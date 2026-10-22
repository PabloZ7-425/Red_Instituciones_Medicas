"""Additive LAB-01 and ODONTO-01 repository ports; JSON-only boundaries."""
from abc import ABC, abstractmethod


class ResultadosRepository(ABC):
    @abstractmethod
    def registrar_resultado(self, paciente_id, resultado): ...

    @abstractmethod
    def listar_resultados(self, paciente_id): ...

    @abstractmethod
    def listar_tipos_examen(self, *, q='', limit=20, offset=0): ...


class ProcedimientosRepository(ABC):
    @abstractmethod
    def registrar_procedimiento(self, paciente_id, procedimiento): ...

    @abstractmethod
    def listar_procedimientos(self, paciente_id): ...
