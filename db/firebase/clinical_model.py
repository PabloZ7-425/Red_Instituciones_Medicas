"""Modelo documental A1, alineado con API/REPO 1.0.0; sin operaciones del puerto."""

from datetime import date, datetime
from hashlib import sha256
import json
from pathlib import Path
import re
import unicodedata
from zoneinfo import ZoneInfo

from seed_demo import require

FIXTURE = Path(__file__).with_name("clinical_demo.json")
VERSION = "odontologia-clinical-v2"
FIELDS = {
    "pacientes": {"identificacion", "nombres", "apellidos", "fecha_nacimiento", "estado", "motivo_archivo", "fecha_archivo", "contacto"},
    "citas": {"paciente_id", "profesional_id", "fecha_hora", "motivo", "estado"},
    "consultas": {"paciente_id", "profesional_id", "cita_id", "fecha", "notas_evolucion"},
    "diagnosticos": {"paciente_id", "consulta_id", "codigo_cie10", "descripcion"},
    "tratamientos": {"paciente_id", "diagnostico_id", "indicaciones_generales"},
    "recetas": {"paciente_id", "tratamiento_id", "medicamento_id", "dosis", "frecuencia", "via_administracion"},
    "medicamentos": {"nombre", "presentacion"},
    "procedimientos": {"paciente_id", "consulta_id", "tratamiento_id", "pieza", "descripcion", "estado"},
    "pagos": {"paciente_id", "procedimiento_id", "fecha_hora", "monto_centavos", "moneda", "estado"},
}
DTO_FIELDS = {
    "pacientes": ("identificacion", "nombres", "apellidos", "fecha_nacimiento", "estado", "motivo_archivo", "fecha_archivo"),
    "consultas": ("paciente_id", "fecha", "notas_evolucion", "cita_id"),
    "diagnosticos": ("consulta_id", "codigo_cie10", "descripcion"),
    "tratamientos": ("diagnostico_id", "indicaciones_generales"),
    "recetas": ("tratamiento_id", "medicamento_id", "dosis", "frecuencia", "via_administracion"),
    "medicamentos": ("nombre", "presentacion"),
}


def identifier(value):
    require(isinstance(value, str) and re.fullmatch(r"DEMO-[A-Za-z0-9_-]{1,95}", value) is not None, "ID DEMO inválido")


def text(value, limit):
    require(isinstance(value, str) and 1 <= len(value) <= limit and value == value.strip(), "Texto vacío, sin normalizar o demasiado largo")


def choice(value, values, message):
    require(isinstance(value, str) and value in values, message)


def civil(value, today):
    require(isinstance(value, str), "Fecha civil debe ser string")
    parsed = date.fromisoformat(value)
    require(parsed.isoformat() == value and parsed <= today, "Fecha civil inválida o futura")


def timestamp(value):
    require(isinstance(value, str) and value.endswith("Z"), "Timestamp requiere UTC Z")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    require(parsed.isoformat(timespec="milliseconds").replace("+00:00", "Z") == value, "Timestamp DEMO no canónico")


def validate(data, *, today=None):
    today = today or datetime.now(ZoneInfo("America/Guatemala")).date()
    require(isinstance(data, dict) and set(data) == set(FIELDS), "Colecciones clínicas inesperadas o ausentes")
    for collection, fields in FIELDS.items():
        require(isinstance(data[collection], dict), "Colección debe ser un objeto")
        for key, doc in data[collection].items():
            identifier(key)
            require(isinstance(doc, dict) and set(doc) == fields, "Campos clínicos inesperados o ausentes")
            for name in ("paciente_id", "profesional_id", "consulta_id", "diagnostico_id", "tratamiento_id", "medicamento_id", "procedimiento_id"):
                if name in doc:
                    identifier(doc[name])
            if collection == "pacientes":
                text(doc["identificacion"], 20)
                require(doc["identificacion"].startswith("DEMO-"), "Identificación debe ser sintética")
                text(doc["nombres"], 100)
                text(doc["apellidos"], 100)
                civil(doc["fecha_nacimiento"], today)
                choice(doc["estado"], {"activo", "inactivo", "archivado"}, "Estado de paciente inválido")
                require(isinstance(doc["contacto"], dict) and set(doc["contacto"]) == {"nota"}, "Contacto DEMO inválido")
                text(doc["contacto"]["nota"], 500)
                if doc["estado"] == "archivado" or doc["fecha_archivo"] is not None or doc["motivo_archivo"] is not None:
                    text(doc["motivo_archivo"], 200)
                    civil(doc["fecha_archivo"], today)
                    require(doc["estado"] != "activo" and doc["fecha_archivo"] >= doc["fecha_nacimiento"], "Archivo inconsistente")
            elif collection == "consultas":
                civil(doc["fecha"], today)
                text(doc["notas_evolucion"], 5000)
                if doc["cita_id"] is not None:
                    identifier(doc["cita_id"])
            elif collection == "diagnosticos":
                text(doc["codigo_cie10"], 20)
                text(doc["descripcion"], 5000)
            elif collection == "tratamientos":
                text(doc["indicaciones_generales"], 5000)
            elif collection == "recetas":
                text(doc["dosis"], 100)
                text(doc["frecuencia"], 100)
                if doc["via_administracion"] is not None:
                    text(doc["via_administracion"], 100)
            elif collection == "medicamentos":
                text(doc["nombre"], 150)
                require(doc["nombre"].startswith("DEMO-"), "Medicamento debe ser ficticio")
                if doc["presentacion"] is not None:
                    text(doc["presentacion"], 100)
            elif collection == "citas":
                timestamp(doc["fecha_hora"])
                text(doc["motivo"], 500)
                choice(doc["estado"], {"programada", "atendida", "cancelada"}, "Estado de cita inválido")
            elif collection == "procedimientos":
                text(doc["descripcion"], 5000)
                choice(doc["estado"], {"pendiente", "realizado", "anulado"}, "Estado de procedimiento inválido")
                choice(doc["pieza"], {str(q * 10 + p) for q in range(1, 9) for p in range(1, 9 if q <= 4 else 6)}, "Pieza FDI inválida")
            elif collection == "pagos":
                timestamp(doc["fecha_hora"])
                require(type(doc["monto_centavos"]) is int and doc["monto_centavos"] > 0, "Centavos deben ser enteros positivos")
                require(doc["moneda"] == "GTQ", "Moneda DEMO inválida")
                choice(doc["estado"], {"registrado", "anulado"}, "Pago DEMO inválido")
    identifications = [d["identificacion"] for d in data["pacientes"].values()]
    require(len(identifications) == len(set(identifications)), "Identificación duplicada")
    references = {"paciente_id": "pacientes", "cita_id": "citas", "consulta_id": "consultas", "diagnostico_id": "diagnosticos", "tratamiento_id": "tratamientos", "medicamento_id": "medicamentos", "procedimiento_id": "procedimientos"}
    used_appointments = set()
    for collection, docs in data.items():
        for doc in docs.values():
            for field, target in references.items():
                if field not in doc or doc[field] is None:
                    continue
                require(doc[field] in data[target], "Referencia inexistente: " + field)
                parent = data[target][doc[field]]
                if "paciente_id" in parent:
                    require(parent["paciente_id"] == doc["paciente_id"], "Referencia a otro paciente")
            if collection == "consultas":
                patient = data["pacientes"][doc["paciente_id"]]
                require(doc["fecha"] >= patient["fecha_nacimiento"], "Consulta anterior al nacimiento")
                if patient["fecha_archivo"] is not None:
                    require(doc["fecha"] <= patient["fecha_archivo"], "Consulta posterior al archivo en fixture")
                if doc["cita_id"] is not None:
                    require(doc["cita_id"] not in used_appointments, "Cita consumida por dos consultas")
                    used_appointments.add(doc["cita_id"])
                    require(data["citas"][doc["cita_id"]]["profesional_id"] == doc["profesional_id"], "Cita de otro profesional")
            if collection == "procedimientos":
                treatment = data["tratamientos"][doc["tratamiento_id"]]
                require(data["diagnosticos"][treatment["diagnostico_id"]]["consulta_id"] == doc["consulta_id"], "Procedimiento de otra consulta")
    return data


def load_fixture():
    return validate(json.loads(FIXTURE.read_text(encoding="utf-8")))


def entries(data):
    """Documentos del seed más reservas deterministas de identificación exacta."""
    validate(data)
    result = []
    for collection, docs in data.items():
        for key, doc in docs.items():
            stored = dict(doc, seed_version=VERSION, schema_version=2, institucion="odontologica")
            if collection == "pacientes":
                stored["busqueda"] = {field: unicodedata.normalize("NFC", doc[field].strip()).lower() for field in ("identificacion", "nombres", "apellidos")}
            elif collection == "medicamentos":
                stored["nombre_busqueda"] = unicodedata.normalize("NFC", doc["nombre"].strip()).lower()
            if "fecha_hora" in stored:
                stored["fecha_hora"] = datetime.fromisoformat(stored["fecha_hora"].replace("Z", "+00:00"))
            result.append((collection, key, stored))
    for key, patient in data["pacientes"].items():
        claim = sha256(patient["identificacion"].encode("utf-8")).hexdigest()
        result.append(("identificaciones", claim, {"paciente_id": key, "identificacion": patient["identificacion"], "seed_version": VERSION, "schema_version": 2, "institucion": "odontologica"}))
    return result


def project_document(collection, key, doc):
    """Proyección pura del modelo al DTO; no es un repositorio ni API activa."""
    return {"id": key, **{field: doc[field] for field in DTO_FIELDS[collection]}}


def project_history(data, patient_id):
    validate(data)
    def children(collection, parent_field, parent_id):
        return [(key, doc) for key, doc in sorted(data[collection].items()) if doc[parent_field] == parent_id]
    consultations = []
    for key, doc in sorted(children("consultas", "paciente_id", patient_id), key=lambda item: (item[1]["fecha"], item[0])):
        consultation = project_document("consultas", key, doc)
        consultation["diagnosticos"] = []
        for diagnosis_id, diagnosis in children("diagnosticos", "consulta_id", key):
            projected = project_document("diagnosticos", diagnosis_id, diagnosis)
            projected["tratamientos"] = []
            for treatment_id, treatment in children("tratamientos", "diagnostico_id", diagnosis_id):
                result = project_document("tratamientos", treatment_id, treatment)
                result["recetas"] = [project_document("recetas", i, d) for i, d in children("recetas", "tratamiento_id", treatment_id)]
                projected["tratamientos"].append(result)
            consultation["diagnosticos"].append(projected)
        consultations.append(consultation)
    return {"paciente": project_document("pacientes", patient_id, data["pacientes"][patient_id]), "consultas": consultations}
