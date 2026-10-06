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
    lab.runCommand({
      collMod: name,
      validator: options.validator,
      validationLevel: 'strict',
      validationAction: 'error'
    });
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
ensureCollection('consultas');
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
        estado: { enum: ['pendiente', 'en_proceso', 'finalizado', 'anulado'] },
        campos: { bsonType: 'array' }
      }
    }
  }
});
lab.resultados_examen.createIndex({ paciente_id: 1, fecha: -1 });
lab.resultados_examen.createIndex({ tipo_examen: 1 });
