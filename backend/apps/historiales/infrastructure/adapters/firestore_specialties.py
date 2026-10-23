"""ODONTO-01 native Firestore transactions; no read after first write."""
from apps.historiales.application.specialties import validate_specialty
from apps.historiales.domain.errors import Conflicto, RecursoNoEncontrado
from apps.historiales.domain.specialties import ProcedimientosRepository


class FirestoreSpecialties(ProcedimientosRepository):
    @staticmethod
    def _procedure_dto(row):
        return {key: row[key] for key in ('id', 'paciente_id', 'consulta_id', 'tratamiento_id', 'pieza', 'descripcion', 'estado')}

    def registrar_procedimiento(self, paciente_id, procedimiento):
        self._authorize('registrar_diagnostico')
        data = validate_specialty('procedure', procedimiento)
        identifier = self._id()

        def apply(unit):
            professional = self._professional(unit)
            patient = self._get(unit, 'pacientes', paciente_id)
            if patient['estado'] != 'activo':
                raise Conflicto()
            treatment = self._get(unit, 'tratamientos', data['tratamiento_id'])
            diagnosis = self._get(unit, 'diagnosticos', treatment['diagnostico_id'])
            consultation = self._get(unit, 'consultas', diagnosis['consulta_id'])
            if any(row['paciente_id'] != paciente_id for row in (treatment, diagnosis, consultation)):
                raise RecursoNoEncontrado()
            self._after_root(unit)
            row = self._stored(paciente_id=paciente_id, consulta_id=consultation['id'], profesional_id=self.contexto.profesional_id, **data)
            unit.update('profesionales_operativos', professional['id'], {'version': professional.get('version', 0) + 1})
            unit.touch(patient)
            unit.create('procedimientos', identifier, row)
            self._after_write(unit)
            return self._procedure_dto(dict(row, id=identifier))

        return self._transaction(apply)

    def listar_procedimientos(self, paciente_id):
        self._authorize('obtener_historial')

        def read(unit):
            self._get(unit, 'pacientes', paciente_id)
            rows = [self._procedure_dto(row) for row in unit.rows('procedimientos') if row['paciente_id'] == paciente_id]
            rows.sort(key=lambda row: row['id'])
            return {'paciente_id': paciente_id, 'procedimientos': rows}

        return self._transaction(read, read=True)
