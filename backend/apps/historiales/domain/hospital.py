"""CONTRACT-HOSPITAL-01@1.0.0: additive hospital port; core REPO stays 1.0.0."""
from abc import ABC, abstractmethod
from typing import TypedDict

from apps.historiales.domain.ports import JsonMap


class IngresoCreate(TypedDict):
    cama_id: str
    fecha_hora_ingreso: str
    tipo_ingreso: str


class IngresoRead(IngresoCreate):
    id: str
    paciente_id: str
    fecha_hora_alta: str | None


class HospitalizacionRepository(ABC):
    @abstractmethod
    def ingresar_paciente(self, paciente_id: str, ingreso: JsonMap) -> JsonMap: ...

    @abstractmethod
    def listar_ingresos(self, paciente_id: str) -> JsonMap: ...

    @abstractmethod
    def dar_alta(self, ingreso_id: str, fecha_hora_alta: str) -> JsonMap: ...
