"""PED-01@1.0.0. Additive pediatric port, separate from the eight core methods."""
from abc import ABC, abstractmethod


class PediatriaRepository(ABC):
    @abstractmethod
    def registrar_tutor(self, paciente_id, tutor): ...

    @abstractmethod
    def registrar_vacuna(self, paciente_id, aplicacion): ...

    @abstractmethod
    def registrar_crecimiento(self, paciente_id, control): ...

    @abstractmethod
    def obtener_seguimiento(self, paciente_id): ...

    @abstractmethod
    def listar_vacunas(self, *, q="", limit=20, offset=0): ...
