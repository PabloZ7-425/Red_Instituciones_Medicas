"""Pure validation shared by use cases; no framework or persistence imports."""
import re
import unicodedata
from collections.abc import Mapping
from datetime import date, datetime, timedelta, timezone

from apps.historiales.domain.errors import DatosInvalidos

# Guatemala has no daylight-saving changes. Injectable civil clock for tests.
def hoy_guatemala():
    return datetime.now(timezone(timedelta(hours=-6))).date()


SCHEMAS = {
    "paciente": ({"identificacion": 20, "nombres": 100, "apellidos": 100,
                  "fecha_nacimiento": None}, {}),
    "consulta": ({"fecha": None, "notas_evolucion": 5000}, {"cita_id": None}),
    "diagnostico": ({"codigo_cie10": 20, "descripcion": 5000}, {}),
    "tratamiento": ({"indicaciones_generales": 5000}, {}),
    "receta": ({"medicamento_id": None, "dosis": 100, "frecuencia": 100},
               {"via_administracion": 100}),
    "archivo": ({"estado": 9, "motivo": 200}, {}),
}


def invalid(field, message):
    raise DatosInvalidos(fields={field: [message]})


def texto(value, field, maximum=None):
    if not isinstance(value, str) or not value.strip():
        invalid(field, "Se requiere un texto no vacío")
    value = value.strip()
    if maximum is not None and len(value) > maximum:
        invalid(field, f"Máximo {maximum} caracteres")
    return value


def identificador(value, field="id"):
    # Opaque IDs are preserved, including significant surrounding characters.
    if not isinstance(value, str) or not value.strip():
        invalid(field, "Se requiere un identificador string no vacío")
    return value


def validar_dto(kind, body, *, today=None):
    if not isinstance(body, Mapping):
        invalid("body", "Se requiere un objeto JSON")
    required, optional = SCHEMAS[kind]
    unknown = set(body) - (required.keys() | optional.keys())
    if unknown:
        invalid("body", "Campos desconocidos o no permitidos")
    result = {}
    for field, maximum in (required | optional).items():
        if field not in body and field in optional:
            continue
        if field.endswith("_id"):
            result[field] = identificador(body.get(field), field)
        else:
            result[field] = texto(body.get(field), field, maximum)
        if field in {"fecha", "fecha_nacimiento"}:
            value = result[field]
            if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
                invalid(field, "Fecha civil inválida; use YYYY-MM-DD")
            try:
                parsed = date.fromisoformat(value)
            except ValueError:
                invalid(field, "Fecha civil inválida")
            if parsed > (today or hoy_guatemala()):
                invalid(field, "La fecha no puede ser futura")
    if kind == "archivo" and result["estado"] != "archivado":
        invalid("estado", "Solo se permite archivado")
    return result


def normalizar_busqueda(value):
    return unicodedata.normalize("NFC", value.strip()).lower()


def validar_paginacion(*, q="", limit=20, offset=0):
    if not isinstance(q, str):
        invalid("q", "Se requiere texto")
    q = normalizar_busqueda(q)
    if len(q) > 100:
        invalid("q", "Máximo 100 caracteres")
    if type(limit) is not int or not 1 <= limit <= 100:
        invalid("limit", "Se requiere un entero entre 1 y 100")
    if type(offset) is not int or offset < 0:
        invalid("offset", "Se requiere un entero mayor o igual a cero")
    return {"q": q, "limit": limit, "offset": offset}


def validar_query(pairs):
    """Parse HTTP query pairs, retaining repetitions so they cannot be silently lost.

    B5 passes request.query_params.lists() flattened into (name, value) pairs.
    """
    values = {}
    for key, value in pairs:
        if key not in {"q", "limit", "offset"} or key in values:
            invalid("query", "Parámetro desconocido o repetido")
        if not isinstance(value, str):
            invalid(key, "Se requiere un parámetro de texto")
        if key in {"limit", "offset"}:
            if not re.fullmatch(r"[0-9]+", value) or len(value) > 10:
                invalid(key, "Se requiere un entero válido")
            value = int(value)
        values[key] = value
    return validar_paginacion(**values)
