"""Native laboratory specialization; root version competes with archive."""
from datetime import datetime
from pymongo.errors import PyMongoError

from apps.historiales.application.specialties import validate_specialty
from apps.historiales.application.validation import validar_paginacion, normalizar_busqueda
from apps.historiales.domain.errors import Conflicto, PersistenciaNoDisponible
from apps.historiales.domain.specialties import ResultadosRepository


class MongoSpecialties(ResultadosRepository):
    def _specialty_ready(self):
        try:
            with self._client() as client:
                if not {'clinico_resultados', 'clinico_tipos_examen'} <= set(client.get_default_database().list_collection_names()):
                    raise PersistenciaNoDisponible()
        except PyMongoError:
            raise PersistenciaNoDisponible() from None

    @staticmethod
    def _result_dto(row):
        return {key: row[key] for key in ('id', 'paciente_id', 'tipo_examen', 'fecha', 'estado', 'campos')}

    def registrar_resultado(self, paciente_id, resultado):
        self._authorize('registrar_consulta')
        data = validate_specialty('result', resultado)
        self._specialty_ready()
        identifier = self._id()

        def apply(unit):
            patient = self._get(unit, 'pacientes', paciente_id)
            if patient['estado'] != 'activo':
                raise Conflicto()
            self._get(unit, 'tipos_examen', data['tipo_examen'])
            self._after_root(unit)
            row = self._stored(paciente_id=paciente_id, profesional_id=self.contexto.profesional_id, **data)
            unit.touch(patient)
            unit.create('resultados', identifier, row)
            self._after_write(unit)
            return self._result_dto(dict(row, id=identifier))

        return self._transaction(apply)

    def listar_resultados(self, paciente_id):
        self._authorize('obtener_historial')
        self._specialty_ready()

        def read(unit):
            self._get(unit, 'pacientes', paciente_id)
            rows = [self._result_dto(row) for row in unit.rows('resultados') if row['paciente_id'] == paciente_id]
            rows.sort(key=lambda row: (datetime.fromisoformat(row['fecha'].replace('Z', '+00:00')), row['id']))
            return {'paciente_id': paciente_id, 'resultados': rows}

        return self._transaction(read, read=True)

    def listar_tipos_examen(self, *, q='', limit=20, offset=0):
        self._authorize('obtener_historial')
        page = validar_paginacion(q=q, limit=limit, offset=offset)
        self._specialty_ready()

        def read(unit):
            rows = [{'id': row['id'], 'nombre': row['nombre']} for row in unit.rows('tipos_examen') if normalizar_busqueda(row['nombre']).startswith(page['q'])]
            rows.sort(key=lambda row: (normalizar_busqueda(row['nombre']), row['id']))
            return {'count': len(rows), 'limit': limit, 'offset': offset, 'results': rows[offset:offset+limit]}

        return self._transaction(read, read=True)
