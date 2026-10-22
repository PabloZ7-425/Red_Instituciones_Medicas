"""A3: common NoSQL orchestration and native MongoDB transactions.

Clinical behavior requires the published B1 runtime; health needs no context.
"""
import os
import time
from hashlib import sha256
from types import SimpleNamespace
from uuid import uuid4

from pymongo import MongoClient, timeout
from pymongo.errors import DuplicateKeyError, PyMongoError
from pymongo.read_concern import ReadConcern
from pymongo.write_concern import WriteConcern

from apps.historiales.domain.ports import DatabaseAdapter, HistorialRepository, MedicamentoCatalogo
from apps.historiales.infrastructure.adapters.mongo_specialties import MongoSpecialties

def _runtime():
    from apps.historiales.application import validation
    from apps.historiales.domain import context, errors
    return SimpleNamespace(v=validation, c=context, e=errors)


_FIELDS = {
    'pacientes': ('identificacion', 'nombres', 'apellidos', 'fecha_nacimiento', 'estado', 'motivo_archivo', 'fecha_archivo'),
    'consultas': ('paciente_id', 'fecha', 'notas_evolucion', 'cita_id'),
    'diagnosticos': ('consulta_id', 'codigo_cie10', 'descripcion'),
    'tratamientos': ('diagnostico_id', 'indicaciones_generales'),
    'recetas': ('tratamiento_id', 'medicamento_id', 'dosis', 'frecuencia', 'via_administracion'),
    'medicamentos': ('nombre', 'presentacion'),
}


class _ClinicalNoSQL(HistorialRepository, MedicamentoCatalogo):
    """Private common behavior. Context comes from the authenticated backend."""
    institution = None

    def __init__(self, *, contexto=None):
        if contexto is not None:
            r = _runtime()
            if not isinstance(contexto, r.c.ContextoClinico):
                raise r.e.NoAutenticado()
            if contexto.institucion != self.institution:
                raise r.e.AccesoDenegado()
        self.contexto = contexto

    def _authorize(self, operation):
        r = _runtime()
        r.c.autorizar(self.contexto, operation)
        return r

    def _id(self):
        return f'{time.time_ns():020d}-{uuid4().hex}'

    def _stored(self, **data):
        return dict(data, schema_version=2, institucion=self.institution)

    def _dto(self, collection, row):
        return {'id': row['id'], **{key: row.get(key) for key in _FIELDS[collection]}}

    def _get(self, u, collection, identifier):
        r = _runtime()
        r.v.identificador(identifier)
        try:
            size = len(identifier.encode('utf-8'))
        except UnicodeError:
            raise r.e.RecursoNoEncontrado() from None
        if '/' in identifier or size > 1500 or identifier in {'.', '..'} or (identifier.startswith('__') and identifier.endswith('__')):
            raise r.e.RecursoNoEncontrado()
        row = u.get(collection, identifier)
        if row is None:
            raise r.e.RecursoNoEncontrado()
        return row

    def _after_root(self, unit):
        """Test subclass seam after root lock/read, before commit."""

    def _after_write(self, unit):
        """Test subclass seam after mutation, before commit."""

    def registrar_paciente(self, paciente):
        r = self._authorize('registrar_paciente')
        data = r.v.validar_dto('paciente', paciente)
        identifier = self._id()
        claim = sha256(data['identificacion'].encode('utf-8')).hexdigest()

        def apply(u):
            if u.get('identificaciones', claim) is not None or any(
                p['identificacion'] == data['identificacion'] for p in u.rows('pacientes')
            ):
                raise r.e.Conflicto()
            row = self._stored(**data, estado='activo', motivo_archivo=None, fecha_archivo=None, version=0)
            u.create('identificaciones', claim, self._stored(paciente_id=identifier, identificacion=data['identificacion']))
            u.create('pacientes', identifier, row)
            self._after_write(u)
            return self._dto('pacientes', dict(row, id=identifier))
        return self._transaction(apply)

    def _page(self, collection, operation, q, limit, offset):
        r = self._authorize(operation)
        params = r.v.validar_paginacion(q=q, limit=limit, offset=offset)
        fields = ('identificacion', 'nombres', 'apellidos') if collection == 'pacientes' else ('nombre',)

        def read(u):
            rows = [row for row in u.rows(collection) if any(
                r.v.normalizar_busqueda(row[field]).startswith(params['q']) for field in fields
            )]
            rows.sort(key=lambda row: (row['identificacion'] if collection == 'pacientes' else r.v.normalizar_busqueda(row['nombre']), row['id']))
            return {'count': len(rows), 'limit': limit, 'offset': offset,
                    'results': [self._dto(collection, row) for row in rows[offset:offset + limit]]}
        return self._transaction(read, read=True)

    def listar_pacientes(self, *, q='', limit=20, offset=0):
        return self._page('pacientes', 'listar_pacientes', q, limit, offset)

    def listar_medicamentos(self, *, q='', limit=20, offset=0):
        return self._page('medicamentos', 'listar_medicamentos', q, limit, offset)

    def obtener_historial(self, paciente_id):
        self._authorize('obtener_historial')

        def read(u):
            patient = self._get(u, 'pacientes', paciente_id)
            groups = {c: [d for d in u.rows(c) if d.get('paciente_id') == paciente_id]
                      for c in ('consultas', 'diagnosticos', 'tratamientos', 'recetas')}

            def children(collection, parent_field, parent_id):
                return sorted((row for row in groups[collection] if row[parent_field] == parent_id), key=lambda d: d['id'])

            consultations = []
            for c in sorted(groups['consultas'], key=lambda d: (d['fecha'], d['id'])):
                consultation = self._dto('consultas', c)
                consultation['diagnosticos'] = []
                for d in children('diagnosticos', 'consulta_id', c['id']):
                    diagnosis = self._dto('diagnosticos', d)
                    diagnosis['tratamientos'] = []
                    for t in children('tratamientos', 'diagnostico_id', d['id']):
                        treatment = self._dto('tratamientos', t)
                        treatment['recetas'] = [self._dto('recetas', x) for x in children('recetas', 'tratamiento_id', t['id'])]
                        diagnosis['tratamientos'].append(treatment)
                    consultation['diagnosticos'].append(diagnosis)
                consultations.append(consultation)
            return {'paciente': self._dto('pacientes', patient), 'consultas': consultations}
        return self._transaction(read, read=True)

    def _append(self, collection, parent_collection, parent_id, kind, operation, payload):
        r = self._authorize(operation)
        data = r.v.validar_dto(kind, payload)
        identifier = self._id()
        parent_field = {'pacientes': 'paciente_id', 'consultas': 'consulta_id', 'diagnosticos': 'diagnostico_id', 'tratamientos': 'tratamiento_id'}[parent_collection]

        def apply(u):
            parent = self._get(u, parent_collection, parent_id)
            patient = parent if parent_collection == 'pacientes' else self._get(u, 'pacientes', parent['paciente_id'])
            if patient['estado'] != 'activo':
                raise r.e.Conflicto()
            appointment = None
            if collection == 'consultas':
                if data['fecha'] < patient['fecha_nacimiento']:
                    r.v.invalid('fecha', 'La consulta no puede preceder al nacimiento')
                if data.get('cita_id') is not None:
                    appointment = self._get(u, 'citas', data['cita_id'])
                    if appointment['paciente_id'] != patient['id'] or appointment['profesional_id'] != self.contexto.profesional_id:
                        raise r.e.RecursoNoEncontrado()
                    if appointment.get('estado') != 'programada' or any(c.get('cita_id') == appointment['id'] for c in u.rows('consultas')):
                        raise r.e.Conflicto()
            if collection == 'recetas':
                self._get(u, 'medicamentos', data['medicamento_id'])
            # Firestore requires ALL reads before writes. Mongo touches the root,
            # making child writes compete with archive even under snapshot reads.
            u.touch(patient)
            self._after_root(u)
            extras = {parent_field: parent_id, 'paciente_id': patient['id']}
            if collection == 'consultas':
                extras.update(profesional_id=self.contexto.profesional_id, cita_id=data.get('cita_id'))
                if appointment:
                    u.update('citas', appointment['id'], {'estado': 'atendida'})
            elif collection == 'recetas':
                extras['via_administracion'] = data.get('via_administracion')
            row = self._stored(**(data | extras))
            u.create(collection, identifier, row)
            self._after_write(u)
            return self._dto(collection, dict(row, id=identifier))
        return self._transaction(apply)

    def registrar_consulta(self, paciente_id, consulta):
        return self._append('consultas', 'pacientes', paciente_id, 'consulta', 'registrar_consulta', consulta)

    def registrar_diagnostico(self, consulta_id, diagnostico):
        return self._append('diagnosticos', 'consultas', consulta_id, 'diagnostico', 'registrar_diagnostico', diagnostico)

    def registrar_tratamiento(self, diagnostico_id, tratamiento):
        return self._append('tratamientos', 'diagnosticos', diagnostico_id, 'tratamiento', 'registrar_tratamiento', tratamiento)

    def registrar_receta(self, tratamiento_id, receta):
        return self._append('recetas', 'tratamientos', tratamiento_id, 'receta', 'registrar_receta', receta)

    def archivar_paciente(self, paciente_id, motivo):
        r = self._authorize('archivar_paciente')
        motivo = r.v.texto(motivo, 'motivo', 200)

        def apply(u):
            patient = self._get(u, 'pacientes', paciente_id)
            if patient['estado'] == 'archivado':
                if patient['motivo_archivo'] != motivo:
                    raise r.e.Conflicto()
                return self._dto('pacientes', patient)
            u.touch(patient)
            self._after_root(u)
            changes = {'estado': 'archivado', 'motivo_archivo': motivo, 'fecha_archivo': r.v.hoy_guatemala().isoformat()}
            u.update('pacientes', paciente_id, changes)
            self._after_write(u)
            return self._dto('pacientes', patient | changes)
        return self._transaction(apply)



class _MongoUnit:
    def __init__(self, db, session, institution):
        self.db, self.session = db, session
        self.scope = {'institucion': institution, 'schema_version': 2}

    def collection(self, name):
        return self.db['clinico_' + name]

    def _row(self, raw):
        return None if raw is None else {'id': raw['_id'], **{k: v for k, v in raw.items() if k != '_id'}}

    def get(self, collection, identifier):
        return self._row(self.collection(collection).find_one(self.scope | {'_id': identifier}, session=self.session))

    def rows(self, collection):
        return [self._row(row) for row in self.collection(collection).find(self.scope, session=self.session)]

    def create(self, collection, identifier, row):
        self.collection(collection).insert_one(dict(row, _id=identifier), session=self.session)

    def update(self, collection, identifier, changes):
        result = self.collection(collection).update_one(self.scope | {'_id': identifier}, {'$set': changes}, session=self.session)
        if result.matched_count != 1:
            raise _runtime().e.RecursoNoEncontrado()

    def touch(self, patient):
        result = self.collection('pacientes').update_one(self.scope | {'_id': patient['id']}, {'$inc': {'version': 1}}, session=self.session)
        if result.matched_count != 1:
            raise _runtime().e.RecursoNoEncontrado()


class MongoAdapter(MongoSpecialties, _ClinicalNoSQL, DatabaseAdapter):
    institution = 'laboratorio'

    def _client(self):
        return MongoClient(os.getenv('MONGO_URI', 'mongodb://mongo:27017/laboratorio'), serverSelectionTimeoutMS=3000)

    def health_check(self):
        client = self._client()
        try:
            return client.admin.command('ping')['ok'] == 1
        finally:
            client.close()

    def _transaction(self, callback, *, read=False):
        r = _runtime()
        client = None
        try:
            client = self._client()
            db = client.get_default_database()
            required = {'clinico_' + name for name in (*_FIELDS, 'citas', 'identificaciones')}
            with timeout(15):
                if not required.issubset(db.list_collection_names()):
                    raise r.e.PersistenciaNoDisponible()
            with timeout(15), client.start_session() as session:
                return session.with_transaction(
                    lambda s: callback(_MongoUnit(db, s, self.institution)),
                    read_concern=ReadConcern('snapshot'), write_concern=WriteConcern('majority'),
                    max_commit_time_ms=10000,
                )
        except DuplicateKeyError:
            raise r.e.Conflicto() from None
        except PyMongoError:
            raise r.e.PersistenciaNoDisponible() from None
        finally:
            if client is not None:
                client.close()
