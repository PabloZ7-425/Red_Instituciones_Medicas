"""Native InnoDB repository: one patient lock and transaction per mutation."""
import re
from contextlib import contextmanager

import mysql.connector

from apps.historiales.application.validation import (
    hoy_guatemala, identificador, normalizar_busqueda, texto, validar_dto, validar_paginacion,
)
from apps.historiales.domain.context import ContextoClinico, autorizar
from apps.historiales.domain.errors import (
    AccesoDenegado, Conflicto, DatosInvalidos, NoAutenticado,
    PersistenciaNoDisponible, RecursoNoEncontrado,
)
from apps.historiales.domain.ports import HistorialRepository, MedicamentoCatalogo
from .mysql_pediatria import MySQLPediatria


def external(kind, number):
    return f"PED-{kind}-{number}"


def internal(value, kind):
    identificador(value)
    match = re.fullmatch(rf"PED-{kind}-([1-9][0-9]{{0,9}})", value)
    if not match or int(match[1]) > 2147483647:
        raise RecursoNoEncontrado()
    return int(match[1])


class MySQLClinical(MySQLPediatria, HistorialRepository, MedicamentoCatalogo):
    def __init__(self, *, contexto=None):
        if contexto is not None and not isinstance(contexto, ContextoClinico):
            raise NoAutenticado()
        if contexto is not None and contexto.institucion != "pediatrico":
            raise AccesoDenegado()
        self.contexto = contexto

    def _authorize(self, operation):
        autorizar(self.contexto, operation)

    @contextmanager
    def _session(self, *, read=False):
        connection = None
        try:
            connection = self._connect()
            with connection.cursor() as settings:
                settings.execute("SET SESSION innodb_lock_wait_timeout=5")
                settings.execute("SET SESSION time_zone='+00:00'")
            # Writes use READ COMMITTED: parent revalidation after the root lock
            # observes the latest commit. History reads use one coherent snapshot.
            connection.start_transaction(isolation_level="REPEATABLE READ" if read else "READ COMMITTED",
                                         readonly=read, consistent_snapshot=read)
            with connection.cursor(dictionary=True, buffered=True) as cursor:
                cursor.execute("SELECT version FROM pediatria_schema_version WHERE version=1")
                if cursor.fetchone() is None:
                    raise PersistenciaNoDisponible()
                yield cursor
            connection.commit()
        except BaseException as error:
            if connection is not None:
                try:
                    connection.rollback()
                except mysql.connector.Error:
                    pass
            if isinstance(error, mysql.connector.Error):
                if error.errno == 1062:
                    raise Conflicto() from None
                if error.errno in (1451, 1452):
                    raise RecursoNoEncontrado() from None
                if error.errno in (1048, 1264, 1265, 1292, 1366, 1406, 3819):
                    raise DatosInvalidos(fields={"body": ["Datos incompatibles con el modelo clínico"]}) from None
                raise PersistenciaNoDisponible() from None
            raise
        finally:
            if connection is not None:
                connection.close()

    def _after_write(self, cursor):
        """Instrumentation seam for test subclasses, never an HTTP fault switch."""

    def _after_header(self, cursor):
        """Test seam for proving header/detail atomicity."""

    def _lock_patient(self, cursor, number, *, active=True):
        cursor.execute("SELECT * FROM paciente WHERE id=%s FOR UPDATE", (number,))
        row = cursor.fetchone()
        if row is None:
            raise RecursoNoEncontrado()
        if active and row["estado"] != "activo":
            raise Conflicto()
        return row

    def _professional(self, cursor):
        value = self.contexto.profesional_id
        if not value or not re.fullmatch(r"[1-9][0-9]{0,9}", value) or int(value) > 2147483647:
            raise AccesoDenegado()
        cursor.execute("SELECT id FROM medico WHERE id=%s AND BINARY estado='activo'", (int(value),))
        if cursor.fetchone() is None:
            raise AccesoDenegado()
        return int(value)

    def _patient_dto(self, r):
        return {"id": external("P", r["id"]), "identificacion": r["identificacion"],
                "nombres": r["nombre"], "apellidos": r["apellidos"],
                "fecha_nacimiento": r["fecha_nacimiento"].isoformat(), "estado": r["estado"],
                "motivo_archivo": r["motivo_baja"],
                "fecha_archivo": r["fecha_baja"].isoformat() if r["fecha_baja"] else None}

    def _consultation_dto(self, r):
        return {"id": external("C", r["id"]), "paciente_id": external("P", r["paciente_id"]),
                "fecha": r["fecha"].isoformat(), "notas_evolucion": r["observaciones"],
                "cita_id": external("CITA", r["cita_id"]) if r["cita_id"] is not None else None}

    def _diagnosis_dto(self, r):
        return {"id": external("D", r["id"]), "consulta_id": external("C", r["consulta_id"]),
                "codigo_cie10": r["codigo"], "descripcion": r["descripcion"]}

    def _treatment_dto(self, r):
        if r["consulta_diagnostico_id"] is None:
            raise PersistenciaNoDisponible()
        return {"id": external("T", r["id"]), "diagnostico_id": external("D", r["consulta_diagnostico_id"]),
                "indicaciones_generales": r["indicaciones"]}

    def _prescription_dto(self, r):
        if r["tratamiento_id"] is None:
            raise PersistenciaNoDisponible()
        return {"id": external("R", r["id"]), "tratamiento_id": external("T", r["tratamiento_id"]),
                "medicamento_id": external("M", r["medicamento_id"]), "dosis": r["dosis"],
                "frecuencia": r["frecuencia"], "via_administracion": r["via_administracion"]}

    def registrar_paciente(self, paciente):
        self._authorize("registrar_paciente")
        d = validar_dto("paciente", paciente)
        with self._session() as c:
            c.execute("""INSERT INTO paciente(identificacion,nombre,apellidos,fecha_nacimiento)
                         VALUES(%s,%s,%s,%s)""", tuple(d[k] for k in (
                             "identificacion", "nombres", "apellidos", "fecha_nacimiento")))
            c.execute("SELECT * FROM paciente WHERE id=%s", (c.lastrowid,))
            result = self._patient_dto(c.fetchone())
            self._after_write(c)
            return result

    def listar_pacientes(self, *, q="", limit=20, offset=0):
        self._authorize("listar_pacientes")
        page = validar_paginacion(q=q, limit=limit, offset=offset)
        with self._session(read=True) as c:
            c.execute("SELECT * FROM paciente")
            rows = [self._patient_dto(r) for r in c.fetchall() if any(
                normalizar_busqueda(r[f]).startswith(page["q"]) for f in ("identificacion", "nombre", "apellidos"))]
            rows.sort(key=lambda r: (r["identificacion"], r["id"]))
            return {"count": len(rows), "limit": limit, "offset": offset, "results": rows[offset:offset+limit]}

    def obtener_historial(self, paciente_id):
        self._authorize("obtener_historial")
        patient = internal(paciente_id, "P")
        with self._session(read=True) as c:
            c.execute("SELECT * FROM paciente WHERE id=%s", (patient,))
            row = c.fetchone()
            if row is None:
                raise RecursoNoEncontrado()
            result = {"paciente": self._patient_dto(row), "consultas": []}
            c.execute("SELECT * FROM consulta WHERE paciente_id=%s", (patient,))
            consultations = [self._consultation_dto(r) | {"diagnosticos": []} for r in c.fetchall()]
            result["consultas"] = sorted(consultations, key=lambda r: (r["fecha"], r["id"]))
            by_c = {r["id"]: r for r in consultations}
            c.execute("""SELECT cd.id,cd.consulta_id,d.codigo,d.descripcion FROM consulta_diagnostico cd
                         JOIN diagnostico d ON d.id=cd.diagnostico_id
                         JOIN consulta c ON c.id=cd.consulta_id WHERE c.paciente_id=%s""", (patient,))
            diagnoses = [self._diagnosis_dto(r) | {"tratamientos": []} for r in c.fetchall()]
            by_d = {r["id"]: r for r in diagnoses}
            for r in sorted(diagnoses, key=lambda r: r["id"]):
                by_c[r["consulta_id"]]["diagnosticos"].append(r)
            c.execute("""SELECT t.* FROM tratamiento t JOIN consulta c ON c.id=t.consulta_id
                         WHERE c.paciente_id=%s""", (patient,))
            treatments = [self._treatment_dto(r) | {"recetas": []} for r in c.fetchall()]
            by_t = {r["id"]: r for r in treatments}
            for r in sorted(treatments, key=lambda r: r["id"]):
                by_d[r["diagnostico_id"]]["tratamientos"].append(r)
            c.execute("""SELECT dr.*,r.tratamiento_id FROM detalle_receta dr JOIN receta r ON r.id=dr.receta_id
                         JOIN consulta c ON c.id=r.consulta_id WHERE c.paciente_id=%s""", (patient,))
            for r in sorted((self._prescription_dto(r) for r in c.fetchall()), key=lambda r: r["id"]):
                by_t[r["tratamiento_id"]]["recetas"].append(r)
            return result

    def registrar_consulta(self, paciente_id, consulta):
        self._authorize("registrar_consulta")
        d = validar_dto("consulta", consulta)
        patient = internal(paciente_id, "P")
        with self._session() as c:
            self._lock_patient(c, patient)
            professional = self._professional(c)
            appointment = None
            if "cita_id" in d:
                appointment = internal(d["cita_id"], "CITA")
                c.execute("SELECT * FROM cita WHERE id=%s FOR UPDATE", (appointment,))
                row = c.fetchone()
                if row is None:
                    raise RecursoNoEncontrado()
                if (row["paciente_id"], row["medico_id"], row["estado"]) != (patient, professional, "programada"):
                    raise Conflicto()
                c.execute("UPDATE cita SET estado='atendida' WHERE id=%s", (appointment,))
            c.execute("""INSERT INTO consulta(paciente_id,medico_id,cita_id,fecha,observaciones)
                         VALUES(%s,%s,%s,%s,%s)""", (patient, professional, appointment, d["fecha"], d["notas_evolucion"]))
            c.execute("SELECT * FROM consulta WHERE id=%s", (c.lastrowid,))
            result = self._consultation_dto(c.fetchone())
            self._after_write(c)
            return result

    def _parent(self, c, number, kind):
        queries = {
            "C": "SELECT paciente_id, id AS consulta_id FROM consulta WHERE id=%s",
            "D": "SELECT c.paciente_id,c.id AS consulta_id FROM consulta_diagnostico d JOIN consulta c ON c.id=d.consulta_id WHERE d.id=%s",
            "T": "SELECT c.paciente_id,c.id AS consulta_id FROM tratamiento t JOIN consulta c ON c.id=t.consulta_id WHERE t.id=%s",
        }
        c.execute(queries[kind], (number,))
        parent = c.fetchone()
        if parent is None:
            raise RecursoNoEncontrado()
        self._lock_patient(c, parent["paciente_id"])
        c.execute(queries[kind], (number,))
        if c.fetchone() != parent:
            raise RecursoNoEncontrado()
        self._professional(c)
        return parent["consulta_id"]

    def registrar_diagnostico(self, consulta_id, diagnostico):
        self._authorize("registrar_diagnostico")
        d = validar_dto("diagnostico", diagnostico)
        parent = internal(consulta_id, "C")
        with self._session() as c:
            self._parent(c, parent, "C")
            # A catalog row is immutable. Reuse only an exact code+description;
            # a differently worded diagnosis never rewrites another history.
            c.execute("SELECT id FROM diagnostico WHERE BINARY codigo=%s AND BINARY descripcion=%s ORDER BY id LIMIT 1",
                      (d["codigo_cie10"], d["descripcion"]))
            row = c.fetchone()
            if row:
                catalog = row["id"]
            else:
                c.execute("INSERT INTO diagnostico(codigo,descripcion) VALUES(%s,%s)", (d["codigo_cie10"], d["descripcion"]))
                catalog = c.lastrowid
            c.execute("INSERT INTO consulta_diagnostico(consulta_id,diagnostico_id) VALUES(%s,%s)", (parent, catalog))
            result = self._diagnosis_dto(d | {"id": c.lastrowid, "consulta_id": parent,
                                             "codigo": d["codigo_cie10"]})
            self._after_write(c)
            return result

    def registrar_tratamiento(self, diagnostico_id, tratamiento):
        self._authorize("registrar_tratamiento")
        d = validar_dto("tratamiento", tratamiento)
        parent = internal(diagnostico_id, "D")
        with self._session() as c:
            consultation = self._parent(c, parent, "D")
            c.execute("INSERT INTO tratamiento(consulta_id,consulta_diagnostico_id,indicaciones) VALUES(%s,%s,%s)",
                      (consultation, parent, d["indicaciones_generales"]))
            result = self._treatment_dto({"id": c.lastrowid, "consulta_diagnostico_id": parent,
                                          "indicaciones": d["indicaciones_generales"]})
            self._after_write(c)
            return result

    def registrar_receta(self, tratamiento_id, receta):
        self._authorize("registrar_receta")
        d = validar_dto("receta", receta)
        parent = internal(tratamiento_id, "T")
        with self._session() as c:
            consultation = self._parent(c, parent, "T")
            medicine = internal(d["medicamento_id"], "M")
            c.execute("SELECT id FROM medicamento WHERE id=%s AND BINARY estado='activo'", (medicine,))
            if c.fetchone() is None:
                raise RecursoNoEncontrado()
            c.execute("INSERT INTO receta(consulta_id,tratamiento_id,fecha) VALUES(%s,%s,%s)",
                      (consultation, parent, hoy_guatemala()))
            header = c.lastrowid
            self._after_header(c)
            c.execute("""INSERT INTO detalle_receta(receta_id,medicamento_id,dosis,frecuencia,via_administracion)
                         VALUES(%s,%s,%s,%s,%s)""", (header, medicine, d["dosis"], d["frecuencia"], d.get("via_administracion")))
            result = self._prescription_dto(d | {"id": c.lastrowid, "tratamiento_id": parent,
                                                 "medicamento_id": medicine, "via_administracion": d.get("via_administracion")})
            self._after_write(c)
            return result

    def archivar_paciente(self, paciente_id, motivo):
        self._authorize("archivar_paciente")
        patient, reason = internal(paciente_id, "P"), texto(motivo, "motivo", 200)
        with self._session() as c:
            row = self._lock_patient(c, patient, active=False)
            if row["estado"] == "archivado":
                if row["motivo_baja"] != reason:
                    raise Conflicto()
                return self._patient_dto(row)
            c.execute("UPDATE paciente SET estado='archivado',motivo_baja=%s,fecha_baja=%s WHERE id=%s",
                      (reason, hoy_guatemala(), patient))
            c.execute("SELECT * FROM paciente WHERE id=%s", (patient,))
            result = self._patient_dto(c.fetchone())
            self._after_write(c)
            return result

    def listar_medicamentos(self, *, q="", limit=20, offset=0):
        self._authorize("listar_medicamentos")
        page = validar_paginacion(q=q, limit=limit, offset=offset)
        with self._session(read=True) as c:
            c.execute("SELECT id,nombre,presentacion FROM medicamento WHERE BINARY estado='activo'")
            rows = [{"id": external("M", r["id"]), "nombre": r["nombre"], "presentacion": r["presentacion"]}
                    for r in c.fetchall() if normalizar_busqueda(r["nombre"]).startswith(page["q"])]
            rows.sort(key=lambda r: (normalizar_busqueda(r["nombre"]), r["id"]))
            return {"count": len(rows), "limit": limit, "offset": offset, "results": rows[offset:offset+limit]}
