from abc import ABC, abstractmethod


class DatabaseAdapter(ABC):
    @abstractmethod
    def health_check(self):
        raise NotImplementedError


class HistorialRepository(ABC):
    @abstractmethod
    def registrar_paciente(self, paciente):
        raise NotImplementedError

    @abstractmethod
    def obtener_historial(self, paciente_id):
        raise NotImplementedError

    @abstractmethod
    def registrar_consulta(self, paciente_id, consulta):
        raise NotImplementedError

    @abstractmethod
    def desactivar_paciente(self, paciente_id, motivo):
        raise NotImplementedError
