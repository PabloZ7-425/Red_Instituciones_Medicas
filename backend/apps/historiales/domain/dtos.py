"""JSON DTOs for CONTRACT-API-01/REPO-01@1.0.0; validation lives in application."""
from typing import NotRequired, TypedDict

CONTRACT_VERSION = "1.0.0"


class LoginCreate(TypedDict):
    username: str
    password: str


class UsuarioRead(TypedDict):
    id: str
    username: str
    rol: str
    institucion: str


class SessionRead(TypedDict):
    usuario: UsuarioRead


class ArchivoCreate(TypedDict):
    estado: str
    motivo: str


class PacienteCreate(TypedDict):
    identificacion: str
    nombres: str
    apellidos: str
    fecha_nacimiento: str


class PacienteRead(PacienteCreate):
    id: str
    estado: str
    motivo_archivo: str | None
    fecha_archivo: str | None


class ConsultaCreate(TypedDict):
    fecha: str
    notas_evolucion: str
    cita_id: NotRequired[str]


class DiagnosticoCreate(TypedDict):
    codigo_cie10: str
    descripcion: str


class TratamientoCreate(TypedDict):
    indicaciones_generales: str


class RecetaCreate(TypedDict):
    medicamento_id: str
    dosis: str
    frecuencia: str
    via_administracion: NotRequired[str]


class RecetaRead(TypedDict):
    id: str
    tratamiento_id: str
    medicamento_id: str
    dosis: str
    frecuencia: str
    via_administracion: str | None


class TratamientoRead(TratamientoCreate):
    id: str
    diagnostico_id: str


class TratamientoHistorial(TratamientoRead):
    recetas: list[RecetaRead]


class DiagnosticoRead(DiagnosticoCreate):
    id: str
    consulta_id: str


class DiagnosticoHistorial(DiagnosticoRead):
    tratamientos: list[TratamientoHistorial]


class ConsultaRead(TypedDict):
    id: str
    paciente_id: str
    fecha: str
    notas_evolucion: str
    cita_id: str | None


class ConsultaHistorial(ConsultaRead):
    diagnosticos: list[DiagnosticoHistorial]


class HistorialRead(TypedDict):
    paciente: PacienteRead
    consultas: list[ConsultaHistorial]


class MedicamentoRead(TypedDict):
    id: str
    nombre: str
    presentacion: str | None


class PacientesPage(TypedDict):
    count: int
    limit: int
    offset: int
    results: list[PacienteRead]


class MedicamentosPage(TypedDict):
    count: int
    limit: int
    offset: int
    results: list[MedicamentoRead]
