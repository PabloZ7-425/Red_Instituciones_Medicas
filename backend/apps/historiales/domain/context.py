from dataclasses import dataclass

from apps.historiales.domain.errors import AccesoDenegado, NoAutenticado
from apps.historiales.domain.institutions import Institution

ROLES = frozenset({"admin", "medico", "secretaria", "enfermero", "laboratorista"})


@dataclass(frozen=True)
class ContextoClinico:
    """B2 builds this from a verified active principal/profile/professional, never a body."""
    institucion: str
    usuario_id: str
    rol: str
    profesional_id: str | None = None

    def __post_init__(self):
        if not isinstance(self.usuario_id, str) or not self.usuario_id.strip():
            raise NoAutenticado()
        if not isinstance(self.institucion, str) or self.institucion not in {
            i.value.slug for i in Institution
        }:
            raise AccesoDenegado()
        if not isinstance(self.rol, str) or self.rol not in ROLES:
            raise AccesoDenegado()
        if self.rol == "laboratorista" and self.institucion != "laboratorio":
            raise AccesoDenegado()
        if self.profesional_id is not None and (
            not isinstance(self.profesional_id, str) or not self.profesional_id.strip()
        ):
            raise AccesoDenegado()


PERMISOS = {
    "listar_pacientes": ROLES,
    "registrar_paciente": {"admin", "medico", "secretaria", "laboratorista"},
    "obtener_historial": {"admin", "medico", "enfermero", "laboratorista"},
    "registrar_consulta": {"admin", "medico", "laboratorista"},
    "registrar_diagnostico": {"admin", "medico"},
    "registrar_tratamiento": {"admin", "medico"},
    "registrar_receta": {"admin", "medico"},
    "archivar_paciente": {"admin"},
    "listar_medicamentos": {"admin", "medico"},
}
ESCRITURAS_PROFESIONALES = frozenset({
    "registrar_consulta", "registrar_diagnostico", "registrar_tratamiento", "registrar_receta"
})


def autorizar(contexto, operacion):
    if not isinstance(contexto, ContextoClinico):
        raise NoAutenticado()
    if contexto.rol not in PERMISOS[operacion]:
        raise AccesoDenegado()
    if operacion in ESCRITURAS_PROFESIONALES and contexto.profesional_id is None:
        raise AccesoDenegado()
