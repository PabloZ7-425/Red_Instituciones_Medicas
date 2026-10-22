"""CONTRACT-REPO-01@1.0.0. No driver types cross these ports."""
from abc import ABC, abstractmethod
from typing import Any, Mapping

JsonMap = Mapping[str, Any]


class DatabaseAdapter(ABC):
    @abstractmethod
    def health_check(self):
        raise NotImplementedError


class HistorialRepository(ABC):
    @abstractmethod
    def registrar_paciente(self, paciente: JsonMap) -> JsonMap:
        raise NotImplementedError

    @abstractmethod
    def listar_pacientes(self, *, q: str = "", limit: int = 20, offset: int = 0) -> JsonMap:
        raise NotImplementedError

    @abstractmethod
    def obtener_historial(self, paciente_id: str) -> JsonMap:
        raise NotImplementedError

    @abstractmethod
    def registrar_consulta(self, paciente_id: str, consulta: JsonMap) -> JsonMap:
        raise NotImplementedError

    @abstractmethod
    def registrar_diagnostico(self, consulta_id: str, diagnostico: JsonMap) -> JsonMap:
        raise NotImplementedError

    @abstractmethod
    def registrar_tratamiento(self, diagnostico_id: str, tratamiento: JsonMap) -> JsonMap:
        raise NotImplementedError

    @abstractmethod
    def registrar_receta(self, tratamiento_id: str, receta: JsonMap) -> JsonMap:
        raise NotImplementedError

    @abstractmethod
    def archivar_paciente(self, paciente_id: str, motivo: str) -> JsonMap:
        raise NotImplementedError


class MedicamentoCatalogo(ABC):
    @abstractmethod
    def listar_medicamentos(self, *, q: str = "", limit: int = 20, offset: int = 0) -> JsonMap:
        raise NotImplementedError
