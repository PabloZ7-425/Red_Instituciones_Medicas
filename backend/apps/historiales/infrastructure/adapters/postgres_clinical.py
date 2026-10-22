"""Native hospital repository. Every mutation owns one transaction and a root lock."""
import re
from collections.abc import Mapping
from contextlib import contextmanager
from datetime import datetime, timezone

import psycopg
from psycopg.rows import dict_row

from apps.historiales.application.validation import (
    hoy_guatemala, identificador, invalid, normalizar_busqueda, texto, validar_dto, validar_paginacion,
)
from apps.historiales.domain.context import ContextoClinico, autorizar
from apps.historiales.domain.errors import (
    AccesoDenegado, Conflicto, DatosInvalidos, NoAutenticado,
    PersistenciaNoDisponible, RecursoNoEncontrado,
)
from apps.historiales.domain.hospital import HospitalizacionRepository
from apps.historiales.domain.ports import HistorialRepository, MedicamentoCatalogo


def external(kind, number):
    return f"H-{kind}-{number}"


def internal(value, kind):
    identificador(value)
    match = re.fullmatch(rf"H-{kind}-([1-9][0-9]{{0,9}})", value)
    if not match or int(match[1]) > 2147483647:
        raise RecursoNoEncontrado()
    return int(match[1])


def utc_time(value, field):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?Z", value):
        invalid(field, "Se requiere timestamp UTC ISO-8601 terminado en Z")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        invalid(field, "Timestamp inválido")
    if parsed > datetime.now(timezone.utc):
        invalid(field, "La fecha no puede ser futura")
    return parsed


class PostgreSQLClinical(HistorialRepository, MedicamentoCatalogo, HospitalizacionRepository):
    def __init__(self, *, contexto=None):
        if contexto is not None and not isinstance(contexto, ContextoClinico):
            raise NoAutenticado()
        if contexto is not None and contexto.institucion != "hospital":
            raise AccesoDenegado()
        self.contexto = contexto

    def _authorize(self, operation):
        autorizar(self.contexto, operation)

    @contextmanager
    def _session(self, *, read=False):
        try:
            with self._connect() as connection:
                with connection.transaction():
                    with connection.cursor(row_factory=dict_row) as cursor:
                        if read:
                            cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
                        cursor.execute("SET LOCAL statement_timeout = '15s'")
                        cursor.execute("SET LOCAL lock_timeout = '5s'")
                        yield cursor
        except psycopg.errors.UniqueViolation:
            raise Conflicto() from None
        except psycopg.errors.ForeignKeyViolation:
            raise RecursoNoEncontrado() from None
        except (psycopg.errors.CheckViolation, psycopg.errors.NotNullViolation, psycopg.DataError):
            raise DatosInvalidos(fields={"body": ["Datos incompatibles con el modelo clínico"]}) from None
        except psycopg.Error:
            # Includes timeouts/deadlocks/connection errors; never guess a duplicate or retry POST.
            raise PersistenciaNoDisponible() from None

    def _after_write(self, cursor):
        """Instrumentation seam for test subclasses; no runtime fault configuration."""

    def _lock_patient(self, cursor, number, *, active=True):
        cursor.execute("SELECT * FROM paciente WHERE id_paciente=%s FOR UPDATE", (number,))
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
        cursor.execute("SELECT id_medico FROM medico WHERE id_medico=%s AND habilitado", (int(value),))
        if cursor.fetchone() is None:
            raise AccesoDenegado()
        return int(value)

    def _patient_dto(self, row):
        return {"id": external("P", row["id_paciente"]), "identificacion": row["dpi_cui"],
                "nombres": row["nombres"], "apellidos": row["apellidos"],
                "fecha_nacimiento": row["fecha_nacimiento"].isoformat(), "estado": row["estado"],
                "motivo_archivo": row["motivo_baja"],
                "fecha_archivo": row["fecha_baja"].isoformat() if row["fecha_baja"] else None}

    def _consultation_dto(self, row):
        if row.get("fecha") is None:
            raise PersistenciaNoDisponible()  # unresolved legacy civil date, never fabricated.
        return {"id": external("C", row["id_consulta"]), "paciente_id": external("P", row["id_paciente"]),
                "fecha": row["fecha"].isoformat(), "notas_evolucion": row["notas_evolucion"],
                "cita_id": external("CITA", row["id_cita"]) if row["id_cita"] is not None else None}

    def _diagnosis_dto(self, row):
        return {"id": external("D", row["id_diagnostico"]), "consulta_id": external("C", row["id_consulta"]),
                "codigo_cie10": row["codigo_cie10"], "descripcion": row["descripcion"]}

    def _treatment_dto(self, row):
        return {"id": external("T", row["id_tratamiento"]), "diagnostico_id": external("D", row["id_diagnostico"]),
                "indicaciones_generales": row["indicaciones_generales"]}

    def _prescription_dto(self, row):
        return {"id": external("R", row["id_receta"]), "tratamiento_id": external("T", row["id_tratamiento"]),
                "medicamento_id": external("M", row["id_medicamento"]), "dosis": row["dosis"],
                "frecuencia": row["frecuencia"], "via_administracion": row["via_administracion"]}

    def registrar_paciente(self, paciente):
        self._authorize("registrar_paciente")
        data = validar_dto("paciente", paciente)
        with self._session() as c:
            c.execute("""INSERT INTO paciente(dpi_cui,nombres,apellidos,fecha_nacimiento)
                         VALUES (%s,%s,%s,%s) RETURNING *""", tuple(data[k] for k in (
                             "identificacion", "nombres", "apellidos", "fecha_nacimiento")))
            result = self._patient_dto(c.fetchone())
            self._after_write(c)
            return result

    def listar_pacientes(self, *, q="", limit=20, offset=0):
        self._authorize("listar_pacientes")
        page = validar_paginacion(q=q, limit=limit, offset=offset)
        with self._session(read=True) as c:
            c.execute("SELECT * FROM paciente")
            # Python's exact NFC/lower/Unicode strip semantics avoid locale-dependent SQL
            # lower() and collation differences. No SQL wildcard or regex interpretation.
            rows = [self._patient_dto(r) for r in c.fetchall() if any(
                normalizar_busqueda(r[f]).startswith(page["q"]) for f in ("dpi_cui", "nombres", "apellidos"))]
            rows.sort(key=lambda r: (r["identificacion"], r["id"]))
            return {"count": len(rows), "limit": limit, "offset": offset, "results": rows[offset:offset+limit]}

    def obtener_historial(self, paciente_id):
        self._authorize("obtener_historial")
        number = internal(paciente_id, "P")
        with self._session(read=True) as c:
            c.execute("SELECT * FROM paciente WHERE id_paciente=%s", (number,))
            patient = c.fetchone()
            if patient is None:
                raise RecursoNoEncontrado()
            c.execute("SELECT * FROM consulta WHERE id_paciente=%s", (number,))
            consultations = [self._consultation_dto(r) | {"diagnosticos": []} for r in c.fetchall()]
            consultations.sort(key=lambda r: (r["fecha"], r["id"]))
            by_consultation = {r["id"]: r for r in consultations}
            c.execute("""SELECT d.* FROM diagnostico d JOIN consulta c USING(id_consulta)
                         WHERE c.id_paciente=%s""", (number,))
            diagnoses = [self._diagnosis_dto(r) | {"tratamientos": []} for r in c.fetchall()]
            by_diagnosis = {r["id"]: r for r in diagnoses}
            for row in sorted(diagnoses, key=lambda r: r["id"]):
                by_consultation[row["consulta_id"]]["diagnosticos"].append(row)
            c.execute("""SELECT t.* FROM tratamiento t JOIN diagnostico d USING(id_diagnostico)
                         JOIN consulta c USING(id_consulta) WHERE c.id_paciente=%s""", (number,))
            treatments = [self._treatment_dto(r) | {"recetas": []} for r in c.fetchall()]
            by_treatment = {r["id"]: r for r in treatments}
            for row in sorted(treatments, key=lambda r: r["id"]):
                by_diagnosis[row["diagnostico_id"]]["tratamientos"].append(row)
            c.execute("""SELECT r.* FROM receta_prescripcion r JOIN tratamiento t USING(id_tratamiento)
                         JOIN diagnostico d USING(id_diagnostico) JOIN consulta c USING(id_consulta)
                         WHERE c.id_paciente=%s""", (number,))
            for row in sorted((self._prescription_dto(r) for r in c.fetchall()), key=lambda r: r["id"]):
                by_treatment[row["tratamiento_id"]]["recetas"].append(row)
            return {"paciente": self._patient_dto(patient), "consultas": consultations}

    def registrar_consulta(self, paciente_id, consulta):
        self._authorize("registrar_consulta")
        data = validar_dto("consulta", consulta)
        patient = internal(paciente_id, "P")
        with self._session() as c:
            self._lock_patient(c, patient)
            professional = self._professional(c)
            appointment = None
            if "cita_id" in data:
                appointment = internal(data["cita_id"], "CITA")
                c.execute("SELECT * FROM cita WHERE id_cita=%s FOR UPDATE", (appointment,))
                row = c.fetchone()
                if row is None:
                    raise RecursoNoEncontrado()
                if row["id_paciente"] != patient or row["id_medico"] != professional or row["estado"] != "programada":
                    raise Conflicto()
                c.execute("SELECT 1 FROM consulta WHERE id_cita=%s", (appointment,))
                if c.fetchone():
                    raise Conflicto()
                c.execute("UPDATE cita SET estado='atendida' WHERE id_cita=%s", (appointment,))
            c.execute("""INSERT INTO consulta(id_paciente,id_medico,id_cita,fecha,notas_evolucion)
                         VALUES (%s,%s,%s,%s,%s) RETURNING *""",
                      (patient, professional, appointment, data["fecha"], data["notas_evolucion"]))
            result = self._consultation_dto(c.fetchone())
            self._after_write(c)
            return result

    def _parent(self, c, number, kind):
        # SQL fragments are fixed by the provider, never supplied by the client.
        queries = {
            "C": "SELECT id_paciente FROM consulta WHERE id_consulta=%s",
            "D": "SELECT c.id_paciente FROM diagnostico d JOIN consulta c USING(id_consulta) WHERE d.id_diagnostico=%s",
            "T": "SELECT c.id_paciente FROM tratamiento t JOIN diagnostico d USING(id_diagnostico) JOIN consulta c USING(id_consulta) WHERE t.id_tratamiento=%s",
        }
        c.execute(queries[kind], (number,))
        parent = c.fetchone()
        if parent is None:
            raise RecursoNoEncontrado()
        self._lock_patient(c, parent["id_paciente"])
        # Revalidate the complete relationship after acquiring the root lock.
        c.execute(queries[kind], (number,))
        if c.fetchone() != parent:
            raise RecursoNoEncontrado()
        self._professional(c)

    def registrar_diagnostico(self, consulta_id, diagnostico):
        self._authorize("registrar_diagnostico")
        data = validar_dto("diagnostico", diagnostico)
        parent = internal(consulta_id, "C")
        with self._session() as c:
            self._parent(c, parent, "C")
            c.execute("INSERT INTO diagnostico(id_consulta,codigo_cie10,descripcion) VALUES (%s,%s,%s) RETURNING *",
                      (parent, data["codigo_cie10"], data["descripcion"]))
            result = self._diagnosis_dto(c.fetchone())
            self._after_write(c)
            return result

    def registrar_tratamiento(self, diagnostico_id, tratamiento):
        self._authorize("registrar_tratamiento")
        data = validar_dto("tratamiento", tratamiento)
        parent = internal(diagnostico_id, "D")
        with self._session() as c:
            self._parent(c, parent, "D")
            c.execute("INSERT INTO tratamiento(id_diagnostico,indicaciones_generales) VALUES (%s,%s) RETURNING *",
                      (parent, data["indicaciones_generales"]))
            result = self._treatment_dto(c.fetchone())
            self._after_write(c)
            return result

    def registrar_receta(self, tratamiento_id, receta):
        self._authorize("registrar_receta")
        data = validar_dto("receta", receta)
        parent = internal(tratamiento_id, "T")
        with self._session() as c:
            self._parent(c, parent, "T")
            medicine = internal(data["medicamento_id"], "M")
            c.execute("SELECT 1 FROM medicamento WHERE id_medicamento=%s", (medicine,))
            if c.fetchone() is None:
                raise RecursoNoEncontrado()
            c.execute("""INSERT INTO receta_prescripcion(id_tratamiento,id_medicamento,dosis,frecuencia,via_administracion)
                         VALUES (%s,%s,%s,%s,%s) RETURNING *""",
                      (parent, medicine, data["dosis"], data["frecuencia"], data.get("via_administracion")))
            result = self._prescription_dto(c.fetchone())
            self._after_write(c)
            return result

    def archivar_paciente(self, paciente_id, motivo):
        self._authorize("archivar_paciente")
        number, motivo = internal(paciente_id, "P"), texto(motivo, "motivo", 200)
        with self._session() as c:
            row = self._lock_patient(c, number, active=False)
            if row["estado"] == "archivado":
                if row["motivo_baja"] != motivo:
                    raise Conflicto()
                return self._patient_dto(row)
            c.execute("SELECT 1 FROM ingreso_hospitalario WHERE id_paciente=%s AND fecha_hora_alta IS NULL", (number,))
            if c.fetchone():
                raise Conflicto()  # hospital extension: close the admission before administrative archive.
            c.execute("UPDATE paciente SET estado='archivado',motivo_baja=%s,fecha_baja=%s WHERE id_paciente=%s RETURNING *",
                      (motivo, hoy_guatemala(), number))
            result = self._patient_dto(c.fetchone())
            self._after_write(c)
            return result

    def listar_medicamentos(self, *, q="", limit=20, offset=0):
        self._authorize("listar_medicamentos")
        page = validar_paginacion(q=q, limit=limit, offset=offset)
        with self._session(read=True) as c:
            c.execute("SELECT id_medicamento,nombre_comercial,presentacion FROM medicamento")
            rows = [{"id": external("M", r["id_medicamento"]), "nombre": r["nombre_comercial"], "presentacion": r["presentacion"]}
                    for r in c.fetchall() if normalizar_busqueda(r["nombre_comercial"]).startswith(page["q"])]
            rows.sort(key=lambda r: (normalizar_busqueda(r["nombre"]), r["id"]))
            return {"count": len(rows), "limit": limit, "offset": offset, "results": rows[offset:offset+limit]}

    def _admission_dto(self, row):
        if row.get("ingreso_utc") is None or (row["fecha_hora_alta"] is not None and row.get("alta_utc") is None):
            raise PersistenciaNoDisponible()
        return {"id": external("I", row["id_ingreso"]), "paciente_id": external("P", row["id_paciente"]),
                "cama_id": external("CAMA", row["id_cama"]), "tipo_ingreso": row["tipo_ingreso"],
                "fecha_hora_ingreso": row["ingreso_utc"].astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
                "fecha_hora_alta": row["alta_utc"].astimezone(timezone.utc).isoformat().replace("+00:00", "Z") if row["alta_utc"] else None}

    def ingresar_paciente(self, paciente_id, ingreso):
        self._authorize("registrar_consulta")
        if not isinstance(ingreso, Mapping) or set(ingreso) != {"cama_id", "fecha_hora_ingreso", "tipo_ingreso"}:
            invalid("body", "Se requieren cama_id, fecha_hora_ingreso y tipo_ingreso")
        patient = internal(paciente_id, "P")
        bed = internal(ingreso["cama_id"], "CAMA")
        instant = utc_time(ingreso["fecha_hora_ingreso"], "fecha_hora_ingreso")
        kind = texto(ingreso["tipo_ingreso"], "tipo_ingreso", 50)
        with self._session() as c:
            self._lock_patient(c, patient)
            professional = self._professional(c)
            # The partial unique index serializes allocation across different
            # patients. No UPDATE privilege on the bed catalog is needed.
            c.execute("SELECT 1 FROM cama WHERE id_cama=%s", (bed,))
            if c.fetchone() is None:
                raise RecursoNoEncontrado()
            c.execute("""INSERT INTO ingreso_hospitalario(id_paciente,id_medico_responsable,id_cama,
                         fecha_hora_ingreso,ingreso_utc,tipo_ingreso) VALUES (%s,%s,%s,%s,%s,%s) RETURNING *""",
                      (patient, professional, bed, instant.replace(tzinfo=None), instant, kind))
            result = self._admission_dto(c.fetchone())
            self._after_write(c)
            return result

    def listar_ingresos(self, paciente_id):
        self._authorize("obtener_historial")
        patient = internal(paciente_id, "P")
        with self._session(read=True) as c:
            c.execute("SELECT 1 FROM paciente WHERE id_paciente=%s", (patient,))
            if c.fetchone() is None:
                raise RecursoNoEncontrado()
            c.execute("SELECT * FROM ingreso_hospitalario WHERE id_paciente=%s", (patient,))
            rows = [self._admission_dto(r) for r in c.fetchall()]
            rows.sort(key=lambda r: (datetime.fromisoformat(r["fecha_hora_ingreso"].replace("Z", "+00:00")), r["id"]))
            return {"paciente_id": paciente_id, "ingresos": rows}

    def dar_alta(self, ingreso_id, fecha_hora_alta):
        self._authorize("registrar_consulta")
        number = internal(ingreso_id, "I")
        instant = utc_time(fecha_hora_alta, "fecha_hora_alta")
        with self._session() as c:
            c.execute("SELECT id_paciente FROM ingreso_hospitalario WHERE id_ingreso=%s", (number,))
            row = c.fetchone()
            if row is None:
                raise RecursoNoEncontrado()
            self._lock_patient(c, row["id_paciente"])
            self._professional(c)
            c.execute("SELECT * FROM ingreso_hospitalario WHERE id_ingreso=%s FOR UPDATE", (number,))
            row = c.fetchone()
            if row is None:
                raise RecursoNoEncontrado()
            if row["ingreso_utc"] is None:
                raise PersistenciaNoDisponible()
            if instant < row["ingreso_utc"]:
                invalid("fecha_hora_alta", "El alta no puede preceder al ingreso")
            if row["alta_utc"] is not None:
                if row["alta_utc"] != instant:
                    raise Conflicto()
                return self._admission_dto(row)
            c.execute("UPDATE ingreso_hospitalario SET fecha_hora_alta=%s,alta_utc=%s WHERE id_ingreso=%s RETURNING *",
                      (instant.replace(tzinfo=None), instant, number))
            result = self._admission_dto(c.fetchone())
            self._after_write(c)
            return result
