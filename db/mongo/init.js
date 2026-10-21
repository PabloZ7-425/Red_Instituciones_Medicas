// Laboratorio clinico - MongoDB 7
// Este script es idempotente: puede ejecutarse varias veces sin borrar datos.
const lab = db.getSiblingDB('laboratorio');

function ensureCollection(name, options = {}) {
  const exists = lab.getCollectionNames().includes(name);

  if (!exists) {
    lab.createCollection(name, options);
    return;
  }

  if (options.validator) {
    const result = lab.runCommand({
      collMod: name,
      validator: options.validator,
      validationLevel: 'strict',
      validationAction: 'error'
    });
    if (result.ok !== 1) throw new Error('No se pudo actualizar el validador: ' + name);
  }
}

ensureCollection('usuarios', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['nombre_usuario', 'contrasena_hash', 'rol', 'activo'],
      properties: {
        nombre_usuario: { bsonType: 'string' },
        contrasena_hash: { bsonType: 'string' },
        rol: { enum: ['laboratorista', 'recepcion', 'admin'] },
        activo: { bsonType: 'bool' }
      }
    }
  }
});
lab.usuarios.createIndex({ nombre_usuario: 1 }, { unique: true });

// Paciente: contacto y tutor van EMBEBIDOS (pequenos y siempre se leen con el paciente)
ensureCollection('pacientes', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['nombres', 'apellidos', 'identificacion', 'fecha_nacimiento', 'estado'],
      properties: {
        nombres: { bsonType: 'string', minLength: 1 },
        apellidos: { bsonType: 'string', minLength: 1 },
        identificacion: { bsonType: 'string', minLength: 1 },
        fecha_nacimiento: { bsonType: 'date' },
        contacto: { bsonType: 'object' },
        tutor: { bsonType: ['object', 'null'] },
        estado: { enum: ['activo', 'inactivo', 'archivado'] },
        motivo_baja: { bsonType: ['string', 'null'] },
        fecha_baja: { bsonType: ['date', 'null'] }
      }
    }
  }
});
lab.pacientes.createIndex({ identificacion: 1 }, { unique: true });
lab.pacientes.createIndex({ apellidos: 1, nombres: 1 });

// Consulta: diagnosticos y recetas EMBEBIDOS (acotados, se escriben juntos y de forma atomica)
// Esquema mínimo de persistencia; los DTOs clínicos esperan ratificación F0.
ensureCollection('consultas', {
  validator: { $jsonSchema: {
    bsonType: 'object', required: ['paciente_id', 'fecha'],
    properties: {
      paciente_id: { bsonType: 'objectId' },
      fecha: { bsonType: 'date' },
      diagnosticos: { bsonType: 'array', items: { bsonType: 'object' } },
      recetas: { bsonType: 'array', items: { bsonType: 'object' } }
    }
  } }
});
lab.consultas.createIndex({ paciente_id: 1, fecha: -1 });

ensureCollection('medicamentos');
lab.medicamentos.createIndex({ nombre: 1 });

// Catalogo de examenes: define los campos esperados de cada tipo
ensureCollection('tipos_examen');
lab.tipos_examen.createIndex({ nombre: 1 }, { unique: true });

// Resultados: coleccion APARTE, referenciada por paciente_id.
// Un paciente acumula cientos de examenes; embeberlos haria crecer el documento sin limite.
// Dentro de cada resultado, 'campos' es un arreglo flexible segun el tipo de examen.
ensureCollection('resultados_examen', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['paciente_id', 'tipo_examen', 'fecha', 'estado', 'campos'],
      properties: {
        paciente_id: { bsonType: 'objectId' },
        fecha: { bsonType: 'date' },
        tipo_examen: { bsonType: 'string', minLength: 1 },
        estado: { enum: ['pendiente', 'en_proceso', 'finalizado', 'anulado'] },
        campos: {
          bsonType: 'array', minItems: 1,
          items: {
            bsonType: 'object', required: ['nombre', 'valor'],
            properties: {
              nombre: { bsonType: 'string', minLength: 1 },
              valor: { bsonType: ['string', 'int', 'long', 'double', 'decimal', 'bool'] },
              unidad: { bsonType: 'string' },
              rango: { bsonType: 'string' }
            }
          }
        }
      }
    }
  }
});
lab.resultados_examen.createIndex({ paciente_id: 1, fecha: -1 });
lab.resultados_examen.createIndex({ tipo_examen: 1 });
