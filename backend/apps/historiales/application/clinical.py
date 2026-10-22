"""Institutional use cases. Only the repository owns relations/atomicity/state checks."""
from apps.historiales.application.validation import (
    identificador, texto, validar_dto, validar_paginacion,
)
from apps.historiales.domain.context import autorizar, ContextoClinico
from apps.historiales.domain.errors import NoAutenticado, PersistenciaNoDisponible


class HistorialService:
    def __init__(self, contexto, repository, catalogo=None, *, today=None):
        if not isinstance(contexto, ContextoClinico):
            raise NoAutenticado()
        self.contexto = contexto
        self.repository = repository
        self.catalogo = catalogo
        self.today = today

    def registrar_paciente(self, paciente):
        autorizar(self.contexto, "registrar_paciente")
        return self.repository.registrar_paciente(validar_dto("paciente", paciente, today=self.today))

    def listar_pacientes(self, *, q="", limit=20, offset=0):
        autorizar(self.contexto, "listar_pacientes")
        return self.repository.listar_pacientes(**validar_paginacion(q=q, limit=limit, offset=offset))

    def obtener_historial(self, paciente_id):
        autorizar(self.contexto, "obtener_historial")
        return self.repository.obtener_historial(identificador(paciente_id))

    def _registrar(self, operacion, parent_id, kind, body):
        autorizar(self.contexto, operacion)
        parent_id = identificador(parent_id)
        data = validar_dto(kind, body, today=self.today)
        return getattr(self.repository, operacion)(parent_id, data)

    def registrar_consulta(self, paciente_id, consulta):
        return self._registrar("registrar_consulta", paciente_id, "consulta", consulta)

    def registrar_diagnostico(self, consulta_id, diagnostico):
        return self._registrar("registrar_diagnostico", consulta_id, "diagnostico", diagnostico)

    def registrar_tratamiento(self, diagnostico_id, tratamiento):
        return self._registrar("registrar_tratamiento", diagnostico_id, "tratamiento", tratamiento)

    def registrar_receta(self, tratamiento_id, receta):
        return self._registrar("registrar_receta", tratamiento_id, "receta", receta)

    def archivar_paciente(self, paciente_id, motivo):
        autorizar(self.contexto, "archivar_paciente")
        return self.repository.archivar_paciente(identificador(paciente_id), texto(motivo, "motivo", 200))

    def listar_medicamentos(self, *, q="", limit=20, offset=0):
        autorizar(self.contexto, "listar_medicamentos")
        if self.catalogo is None:
            raise PersistenciaNoDisponible()
        return self.catalogo.listar_medicamentos(**validar_paginacion(q=q, limit=limit, offset=offset))
