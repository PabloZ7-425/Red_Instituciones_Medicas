# A5 — recuperación clínica NoSQL fuera de fixtures exactos

Jennifer, 22 de octubre de 2026. Base 2793e1a. Nuevos helpers propios:
`db/mongo/clinical_recovery.py` y `db/firebase/clinical_recovery.py`.
No se modifican el exportador DEMO A1, los adaptadores, los contratos o Compose.

## Resultado comprobado

**10 pruebas nuevas aprobadas, cero omitidas.** Se crearon dos historias completas
por motor mediante los métodos reales de A3: paciente, consulta, diagnóstico por
ocurrencia, tratamiento y receta. Una historia quedó activa y otra archivada. Se
agregaron documentos heredados tipados fuera del núcleo para verificar que no se
exporta únicamente el fixture conocido.

Se exportó, se **apagó el origen** y se restauró sin seed:

| Motor | Recuperación fría ejecutada | Verificación |
|---|---|---|
| MongoDB | mongodump/mongorestore, gzip archive, otro servidor/replica set y base nueva *_recovery_uuid | 9 colecciones, 14 documentos, BSON/hash exacto, opciones/validadores e índices (incluido compuesto/único) |
| Firestore | Export nativo, origen detenido, otra JVM con import nativo del mismo proyecto emulado | 8 colecciones, 14 documentos; hashes exactos de documentos y tipos |

Una nueva instancia del adaptador leyó los historiales iguales al origen. La
identificación duplicada siguió produciendo 409, archivo con mismo motivo conservó
fecha/historia y una consulta posterior al archivo siguió produciendo 409. El
paciente activo admitió otra consulta: la prueba verifica continuidad además de
lectura. Mongo rechazó un documento inválido después del restore, demostrando que
sus validadores se recuperaron.

Los datos heredados comprobados incluyen ObjectId, fecha BSON y bytes en Mongo;
Timestamp con **nanosegundos**, bytes, GeoPoint, referencia a documento y mapa/array
con números/bool/null en Firestore. UTF-8, fechas civiles, IDs y opcionales del árbol
clínico se conservaron. No se usaron repositorios de memoria ni se reejecutó seed
sobre los destinos restaurados.

MongoDB 7.0.45, MongoDB Database Tools 100.19.1, Firestore Emulator 1.22.0, SDK 2.34.1,
PyMongo 4.19.0, Python 3.12.14 y Java del entorno. Instancias/puertos dedicados en
loopback; datos y artefactos temporales fuera de Git, sin bases/volúmenes de otro
integrante. Los tests retiran sus artefactos al finalizar; no se publican dumps.

## Cómo funcionan los helpers

### Mongo

Respalda una base explícita usando la herramienta nativa, no JSON de DTOs. Captura
un inventario/snapshot de documentos BSON, opciones y definiciones de índices;
compara antes/después del dump. Guarda el hash del archive y un manifiesto. Los
UUID físicos de colecciones no se comparan: el destino es otro servidor/base.
El orden de claves de índices compuestos sí se conserva en la comparación.

La URI se pasa a la herramienta por archivo temporal privado, no por argumentos
con credenciales. El helper no imprime contenido ni stderr de la herramienta.
El directorio nuevo tiene modo 0700 y el manifiesto 0600. El archive permanece
protegido por ese directorio. SHA-256 se calcula en streaming.

Restore verifica el archive **antes** de invocar mongorestore. Solo admite base
local distinta, con sufijo `_recovery_<32 caracteres hex>` y sin ninguna colección.
Mapea namespaces nativamente, no usa --drop ni borra el origen. Si falla una
restauración, el destino puede quedar parcial: no se declara recuperado, no se
sobrescribe en un segundo intento y el operador utiliza otro destino nuevo.
La comparación posterior certifica documentos, índices y validadores, no solo counts.

### Firestore

Solo emulador explícito en loopback y proyecto `demo-*`. Captura los documentos
planos de las colecciones actuales dentro de una transacción read-only y exporta
por la API nativa del emulador, compartiendo filesystem con Java. No requiere que
los valores sean iguales al fixture A1. Compara inventario/documentos antes/después
y genera hashes de todos los archivos nativos exportados.

El backup es del modelo **plano** actual de A1/A3. Subcolecciones o padres ausentes
se rechazan, no se omiten silenciosamente. Los valores no reconocidos también se
rechazan; no se convierte un tipo desconocido a texto. Las referencias/instantes
se verifican con su tipo, incluida precisión de nanosegundos. El helper no modifica
ni borra documentos.

La importación se hace al iniciar una JVM nueva, en otro puerto y con el mismo
project ID. `verify-archive` rechaza archivos alterados/adicionales o rutas fuera
del backup; `verify-restored` compara el proyecto y documentos recuperados. No
existe una operación del helper que borre o restaure sobre un proyecto poblado.
Este procedimiento no certifica Firebase productivo ni sus reglas/credenciales.

## Condición obligatoria: escritores detenidos

Estos son procedimientos de **mantenimiento**, no hot backup. Detener backend,
seeds y cualquier escritor/DDL externo antes de exportar; mantener la pausa hasta
terminar. `--writers-stopped` es la declaración explícita del operador, **no un lock
distribuido ni un mecanismo que detenga procesos**. La comparación antes/después
detecta cambios observados, pero no reemplaza esa condición ni demuestra ausencia
de una escritura transitoria externa. Durante las pruebas no había API ni escritores
concurrentes y todas las operaciones de preparación habían terminado.

## Uso local del procedimiento Mongo

Requisitos: SDK del backend, mongodump/mongorestore oficiales y replica set local.
Configurar MONGO_RECOVERY_URI fuera de Git; el URI debe incluir la base.
No usar un nombre de destino que corresponda a una base activa.

```bash
# Escritores/DDL ya detenidos. Directorio nuevo, fuera del repositorio.
python db/mongo/clinical_recovery.py backup --writers-stopped --directory /ruta/privada/mongo-backup
python db/mongo/clinical_recovery.py verify-archive --directory /ruta/privada/mongo-backup

# Cambiar MONGO_RECOVERY_URI a otro servidor/base nueva:
# laboratorio_recovery_<uuid hex de 32 caracteres>, sin colecciones.
python db/mongo/clinical_recovery.py restore --directory /ruta/privada/mongo-backup
```

La URI local puede contener credenciales de una instancia autorizada. El ejemplo
no crea cuentas, grants, topología ni servicios automáticamente. El backup incluye
las colecciones ordinarias de la base, también las heredadas; no exporta identidad
Django de otra base. Views/time-series quedan fuera del alcance admitido y se
rechazan. Revisar la clasificación más sensible del contenido antes de almacenarlo.

## Uso local del procedimiento Firestore

Configurar FIRESTORE_EMULATOR_HOST al origen local y detener escritores:

```bash
python db/firebase/clinical_recovery.py backup --project demo-historiales \
  --writers-stopped --directory /ruta/privada/firestore-backup
python db/firebase/clinical_recovery.py verify-archive --project demo-historiales \
  --directory /ruta/privada/firestore-backup
```

Apagar origen. Iniciar otro emulador **vacío**, sin seed, con el metadata file
verificado (mismo proyecto, puerto nuevo):

```bash
java -jar /ruta/local/cloud-firestore-emulator-v1.22.0.jar \
  --host=127.0.0.1 --port=8095 --project_id=demo-historiales \
  --import-data=/ruta/privada/firestore-backup/firestore_export/firestore_export.overall_export_metadata

# Otra terminal, FIRESTORE_EMULATOR_HOST del destino:
python db/firebase/clinical_recovery.py verify-restored --project demo-historiales \
  --directory /ruta/privada/firestore-backup
```

No cambiar el proyecto para «hacer coincidir» un respaldo ajeno. No reutilizar el
JVM/proyecto activo para probar importación. La recuperación A1 de fixtures sigue
siendo un procedimiento independiente y conserva sus comprobaciones anteriores.

## Suite reproducible aislada (Linux)

`backend/apps/historiales/test_recovery_nosql.py` requiere destinos nuevos. Prepara
solo datos sintéticos y detiene el origen como parte de la prueba fría. No admite
esta activación como un test sobre servicios compartidos. El runner debe crear:

- `jennifer-recovery-mongo`: Mongo nuevo, etiqueta codex.task=jennifer-recovery,
  puerto 27039 y replica set recovery, miembro 127.0.0.1:27039.
- `jennifer-recovery-target`: otro Mongo nuevo, misma etiqueta, puerto 27049 y
  replica set recoveryTarget, miembro 127.0.0.1:27049.
- JVM nuevo con puerto 8093, proyecto demo-clinical-recovery y filesystem local.
  El PID se registra para que la prueba valide el argumento antes de detenerlo.
- Directorio `/workspace/work/recovery`, binarios nativos oficiales y JAR local.

```bash
RECOVERY_NOSQL_TESTS=1 \
FIRESTORE_RECOVERY_SOURCE_PID=<pid-del-java-dedicado> \
FIRESTORE_RECOVERY_JAR=/ruta/local/cloud-firestore-emulator-v1.22.0.jar \
MONGO_DUMP_BIN=/ruta/local/mongodump MONGO_RESTORE_BIN=/ruta/local/mongorestore \
PYTHONPATH=backend python -m unittest apps.historiales.test_recovery_nosql -v
```

El resto de los casos rechaza archivo corrupto, destino Mongo poblado, mismo destino,
directorio dentro de Git o existente, pausa no declarada, proyecto no DEMO y
subcolección inesperada; comprueba que el dato rechazado no fue borrado. Sin la
variable de activación, la suite se omite explícitamente y no acredita recuperación.
Las diez pruebas de esta entrega se ejecutaron con activación y ninguna omitida.

## Aporte al cierre

Se cierra la recuperación del núcleo clínico NoSQL para estos modelos y versiones.
No se declara recuperación de SQL/identidad por esta suite, backup sin pausa,
migración de históricos ambiguos ni seguridad productiva. Para la integración,
consultar [ESTADO_PARA_MERGE.md](ESTADO_PARA_MERGE.md); para sensibilidad y comparación,
[COMPARATIVO_Y_CLASIFICACION_A.md](COMPARATIVO_Y_CLASIFICACION_A.md).
