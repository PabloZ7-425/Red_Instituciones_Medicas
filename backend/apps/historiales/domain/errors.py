"""Safe domain errors; presentation may expose only these messages/fields."""


class ErrorDominio(Exception):
    status = 500
    code = "INTERNAL_ERROR"
    message = "Error interno"

    def __init__(self, *, fields=None):
        self.fields = fields or {}
        super().__init__(self.message)

    def as_dict(self):
        return {"error": {"code": self.code, "message": self.message, "fields": self.fields}}


class DatosInvalidos(ErrorDominio):
    status, code, message = 400, "VALIDATION_ERROR", "Datos inválidos"


class NoAutenticado(ErrorDominio):
    status, code, message = 401, "UNAUTHORIZED", "Autenticación requerida"


class AccesoDenegado(ErrorDominio):
    status, code, message = 403, "FORBIDDEN", "Acceso denegado"


class RecursoNoEncontrado(ErrorDominio):
    status, code, message = 404, "NOT_FOUND", "Recurso no encontrado"


class Conflicto(ErrorDominio):
    status, code, message = 409, "CONFLICT", "La operación entra en conflicto con el estado actual"


class PersistenciaNoDisponible(ErrorDominio):
    status, code, message = 503, "SERVICE_UNAVAILABLE", "Persistencia no disponible"
