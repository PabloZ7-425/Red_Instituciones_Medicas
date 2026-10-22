"""PED-01 specialization. No schedule, percentile or treatment is inferred."""
import re
from collections.abc import Mapping
from decimal import Decimal

from apps.historiales.application.validation import (
    invalid, normalizar_busqueda, texto, validar_dto, validar_paginacion,
)
from apps.historiales.domain.errors import RecursoNoEncontrado
from apps.historiales.domain.pediatria import PediatriaRepository


def fields(body, required, optional=()):
    if not isinstance(body, Mapping) or not set(required) <= body.keys() or set(body) - set(required) - set(optional):
        invalid("body", "Campos requeridos ausentes o campos desconocidos")
    return dict(body)


def civil(value):
    return validar_dto("consulta", {"fecha": value, "notas_evolucion": "Validación de fecha"})["fecha"]


def measurement(value, field):
    # Decimal strings deliberately avoid float rounding and JSON NaN/Infinity.
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{1,4}(?:\.[0-9]{1,2})?", value):
        invalid(field, "Se requiere decimal positivo como string, máximo 9999.99 y dos decimales")
    result = Decimal(value)
    if result <= 0:
        invalid(field, "Se requiere valor positivo")
    return result


class MySQLPediatria(PediatriaRepository):
    def listar_tutores(self, paciente_id):
        from .mysql_clinical import external, internal
        self._authorize('registrar_paciente')
        patient = internal(paciente_id, 'P')
        with self._session(read=True) as c:
            c.execute('SELECT id FROM paciente WHERE id=%s', (patient,))
            if c.fetchone() is None:
                raise RecursoNoEncontrado()
            c.execute('''SELECT pt.id,pt.tutor_id,pt.parentesco,t.nombres,t.apellidos,t.telefono,t.correo,t.dpi,
                         t.parentesco AS parentesco_legacy FROM paciente_tutor pt JOIN tutor t ON t.id=pt.tutor_id
                         WHERE pt.paciente_id=%s''', (patient,))
            rows = [dict(row, id=external('PT', row['id']), tutor_id=external('TUTOR', row['tutor_id']), paciente_id=paciente_id)
                    for row in c.fetchall()]
            rows.sort(key=lambda row: row['id'])
            return {'paciente_id': paciente_id, 'tutores': rows}

    def registrar_tutor(self, paciente_id, tutor):
        from .mysql_clinical import external, internal
        self._authorize("registrar_paciente")
        d = fields(tutor, ("nombres", "apellidos", "parentesco"), ("telefono", "correo", "dpi"))
        d = {k: texto(v, k, 150 if k == "correo" else 100) for k, v in d.items()}
        patient = internal(paciente_id, "P")
        with self._session() as c:
            self._lock_patient(c, patient)
            # Do not merge persons merely because DPI or names happen to match.
            c.execute("INSERT INTO tutor(nombres,apellidos,telefono,correo,dpi) VALUES(%s,%s,%s,%s,%s)",
                      tuple(d.get(k) for k in ("nombres", "apellidos", "telefono", "correo", "dpi")))
            tutor_id = c.lastrowid
            c.execute("INSERT INTO paciente_tutor(paciente_id,tutor_id,parentesco) VALUES(%s,%s,%s)",
                      (patient, tutor_id, d["parentesco"]))
            result = {k: d.get(k) for k in ("nombres", "apellidos", "telefono", "correo", "dpi", "parentesco")}
            result.update(id=external("PT", c.lastrowid), tutor_id=external("TUTOR", tutor_id), paciente_id=paciente_id)
            self._after_write(c)
            return result

    def registrar_vacuna(self, paciente_id, aplicacion):
        from .mysql_clinical import external, internal
        self._authorize("registrar_consulta")
        d = fields(aplicacion, ("vacuna_id", "fecha", "dosis"), ("lote", "observaciones"))
        patient, vaccine = internal(paciente_id, "P"), internal(d["vacuna_id"], "V")
        d["fecha"] = civil(d["fecha"])
        if type(d["dosis"]) is not int or not 1 <= d["dosis"] <= 2147483647:
            invalid("dosis", "Se requiere entero positivo")
        for key in ("lote", "observaciones"):
            if key in d:
                d[key] = texto(d[key], key, 100 if key == "lote" else 5000)
        with self._session() as c:
            self._lock_patient(c, patient)
            professional = self._professional(c)
            c.execute("SELECT id FROM vacuna WHERE id=%s", (vaccine,))
            if c.fetchone() is None:
                raise RecursoNoEncontrado()
            c.execute("""INSERT INTO aplicacion_vacuna(paciente_id,vacuna_id,fecha,dosis,lote,observaciones,medico_id)
                         VALUES(%s,%s,%s,%s,%s,%s,%s)""",
                      (patient, vaccine, d["fecha"], d["dosis"], d.get("lote"), d.get("observaciones"), professional))
            result = {"id": external("AV", c.lastrowid), "paciente_id": paciente_id, "vacuna_id": d["vacuna_id"],
                      "fecha": d["fecha"], "dosis": d["dosis"], "lote": d.get("lote"), "observaciones": d.get("observaciones")}
            self._after_write(c)
            return result

    def registrar_crecimiento(self, paciente_id, control):
        from .mysql_clinical import external, internal
        self._authorize("registrar_consulta")
        d = fields(control, ("fecha", "peso_kg", "talla_cm"), ("observaciones",))
        patient = internal(paciente_id, "P")
        d["fecha"] = civil(d["fecha"])
        weight, height = measurement(d["peso_kg"], "peso_kg"), measurement(d["talla_cm"], "talla_cm")
        if "observaciones" in d:
            d["observaciones"] = texto(d["observaciones"], "observaciones", 5000)
        with self._session() as c:
            self._lock_patient(c, patient)
            professional = self._professional(c)
            # New explicit-unit columns preserve legacy talla/altura without
            # pretending to know the historical units or calculating percentiles.
            c.execute("""INSERT INTO control_de_crecimiento(paciente_id,fecha,peso_kg,talla_cm,observaciones,medico_id)
                         VALUES(%s,%s,%s,%s,%s,%s)""",
                      (patient, d["fecha"], weight, height, d.get("observaciones"), professional))
            result = {"id": external("G", c.lastrowid), "paciente_id": paciente_id, "fecha": d["fecha"],
                      "peso_kg": f"{weight:.2f}", "talla_cm": f"{height:.2f}", "observaciones": d.get("observaciones")}
            self._after_write(c)
            return result

    def obtener_seguimiento(self, paciente_id):
        from .mysql_clinical import external, internal
        self._authorize("obtener_historial")
        patient = internal(paciente_id, "P")
        with self._session(read=True) as c:
            c.execute("SELECT id FROM paciente WHERE id=%s", (patient,))
            if c.fetchone() is None:
                raise RecursoNoEncontrado()
            c.execute("""SELECT pt.id,pt.tutor_id,pt.parentesco,t.nombres,t.apellidos,t.telefono,t.correo,t.dpi,
                         t.parentesco AS parentesco_legacy FROM paciente_tutor pt JOIN tutor t ON t.id=pt.tutor_id
                         WHERE pt.paciente_id=%s""", (patient,))
            tutors = [dict(r, id=external("PT", r["id"]), tutor_id=external("TUTOR", r["tutor_id"]),
                           paciente_id=paciente_id) for r in c.fetchall()]
            c.execute("SELECT * FROM aplicacion_vacuna WHERE paciente_id=%s", (patient,))
            vaccines = [{"id": external("AV", r["id"]), "paciente_id": paciente_id, "vacuna_id": external("V", r["vacuna_id"]),
                         "fecha": r["fecha"].isoformat(), "dosis": r["dosis"], "lote": r["lote"],
                         "observaciones": r["observaciones"]} for r in c.fetchall()]
            c.execute("SELECT * FROM control_de_crecimiento WHERE paciente_id=%s", (patient,))
            growth = [{"id": external("G", r["id"]), "paciente_id": paciente_id, "fecha": r["fecha"].isoformat(),
                       "peso_kg": str(r["peso_kg"]) if r["peso_kg"] is not None else None,
                       "talla_cm": str(r["talla_cm"]) if r["talla_cm"] is not None else None,
                       "observaciones": r["observaciones"],
                       "mediciones_legacy": {k: str(r[k]) if r[k] is not None else None
                                             for k in ("peso", "talla", "altura", "percentil")}}
                      for r in c.fetchall()]
            tutors.sort(key=lambda r: r["id"])
            for rows in (vaccines, growth):
                rows.sort(key=lambda r: (r["fecha"], r["id"]))
            return {"paciente_id": paciente_id, "tutores": tutors, "vacunas": vaccines, "crecimiento": growth}

    def listar_vacunas(self, *, q="", limit=20, offset=0):
        from .mysql_clinical import external
        self._authorize("obtener_historial")
        page = validar_paginacion(q=q, limit=limit, offset=offset)
        with self._session(read=True) as c:
            c.execute("SELECT id,nombre FROM vacuna")
            rows = [{"id": external("V", r["id"]), "nombre": r["nombre"]} for r in c.fetchall()
                    if normalizar_busqueda(r["nombre"]).startswith(page["q"])]
            rows.sort(key=lambda r: (normalizar_busqueda(r["nombre"]), r["id"]))
            return {"count": len(rows), "limit": limit, "offset": offset, "results": rows[offset:offset+limit]}
