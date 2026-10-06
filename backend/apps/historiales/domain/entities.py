from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Paciente:
    identificacion: str
    nombres: str
    apellidos: str
    fecha_nacimiento: date
    estado: str = "activo"
