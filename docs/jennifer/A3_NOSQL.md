# A3 — repositorios clínicos MongoDB y Firestore

Entrega de Jennifer, 22 de octubre de 2026, America/Guatemala.
CONTRACT-REPO-01@1.0.0 y CAT-01; ocho métodos y catálogo. Código de esta entrega:
`git log -1 -- backend/apps/historiales/infrastructure/adapters/mongo_adapter.py`.
Base sincronizada: `d656044`, que incorpora main `ead042c` conservando íntegramente
A1, A2 y React de `7bacf22`. Solo se publica en `feature/jennifer`, sin PR ni merge
hacia main. El SQLite local original se conserva fuera del índice, con los mismos
bytes del archivo anterior a la sincronización.

## Comportamiento entregado

- Alta/listado de pacientes, historial anidado, consulta, diagnóstico por ocurrencia,
  tratamiento, receta y archivo; catálogo real con IDs devueltos por el motor.
- DTOs JSON, fechas civiles, opcionales null y ramas vacías; no se devuelven BSON,
  referencias SDK, institución interna, profesional, versiones ni datos de usuarios.
- Validación B1 compartida y autorización antes de acceder al motor. Constructor
  sin contexto permite salud; operaciones clínicas requieren ContextoClinico válido.
  Mongo solo admite laboratorio y Firestore odontologica. Profesional del principal
  verificado por B2, nunca de un campo arbitrario del formulario. No se consultan
  usuarios históricos Mongo ni se introduce otro sistema de autenticación.
- Prefijo literal trim/NFC/lower por OR, count previo a paginar, orden contractual,
  acentos y símbolos preservados. La evaluación/orden final se hace en Python sobre
  documentos institucionales versionados, sin truncamiento silencioso. Esto asegura
  equivalencia para el alcance académico; **no es una búsqueda indexada de gran escala**.
- Cada cliente se cierra; fallo de conexión/transacción produce 503 seguro.
  Identificación duplicada produce 409; padres/catálogo ajenos o ausentes 404.
  IDs incompatibles con documentos, incluidos slash, reservados y Unicode inválido,
  se rechazan sin producir rutas SDK ni filtrar mensajes del driver.

La base privada `_ClinicalNoSQL` está dentro del archivo propio mongo_adapter.py
para compartir reglas/proyección sin editar dominio, aplicación o puertos de Pablo.
Firestore aporta su unidad transaccional nativa y Mongo la suya. Ambos implementan
HistorialRepository y MedicamentoCatalogo del núcleo B1 ya incorporado a esta rama.

## Consistencia

Mongo usa sesión/transacción snapshot con write concern majority. Toda escritura
hija incrementa la versión del paciente raíz, y el archivo modifica ese mismo
paciente. Un conflicto aborta/reintenta la transacción mediante el SDK y vuelve a
comprobar activo; una lectura snapshot sola no se presenta como exclusión.
Presupuesto de operaciones Mongo: 15 segundos; commit hasta 10 segundos dentro del
presupuesto. No hay mutex de proceso ni reintento HTTP de un POST incierto.

Firestore lee padres, paciente y referencias **antes** de encolar escrituras.
Cada escritura hija y archivo modifica la versión del paciente leído. El SDK puede
reintentar el callback, que vuelve a verificar estado/referencias. Lecturas completas
del historial ocurren en una única transacción read-only. La consulta opcional
consume su cita en la misma transacción y comprueba paciente/profesional/estado.

La reserva de identificación y alta son atómicas; el índice único Mongo refuerza
la restricción. Archivo con el mismo motivo conserva fecha e historia; otro motivo
es 409. Ninguna operación clínica puede confirmarse después del archivo. No se
eliminan historiales ni se reconstruyen fechas históricas mediante inferencias.

## Modelos y preparación del entorno

**Firestore:** reutiliza los documentos A1 `schema_version=2` de las colecciones
pacientes/consultas/diagnosticos/tratamientos/recetas/medicamentos/citas y las reservas
identificaciones. Se probó leer los dos historiales A1 sin alterar su proyección y
ampliar el activo aunque todavía no tuviera `version`. Conserva legacy/seed_version.
El repositorio sigue usando el emulador configurado; no activa Firebase productivo.
El exportador A1 certifica datasets DEMO exactos: no se anuncia como backup de una
base clínica modificada por A3. Recuperación clínica general pertenece a A5.

**Mongo:** las ocho colecciones `clinico_*` contienen el modelo contractual v2,
con IDs string opacos, fechas civiles string, institución/schema_version y versión
raíz. Se separan del modelo A2 BSON/arrays legacy para no reinterpretar ni endurecer
sus documentos. El script propio `db/mongo/clinical_schema.py` crea validadores e
índices de forma explícita e idempotente; rechaza validadores existentes distintos,
sin collMod, borrado ni sustitución de datos. El repositorio devuelve 503 cuando
faltan colecciones clínicas y no las crea implícitamente.

Preparación, con respaldo/inventario previo cuando corresponda y URI configurada
por el responsable del entorno (no guardar claves en Git):

```bash
# MONGO_CLINICAL_SETUP_URI identifica la base que se decidió preparar.
python db/mongo/clinical_schema.py --apply
```

El proceso requiere permisos de mantenimiento sobre las nuevas colecciones/índices.
El runtime necesita lectura/listCollections y escrituras clínicas, no DDL automático.
MONGO_URI debe incluir base de datos y topología transaccional configurada por B5.
**Standalone no acredita A3.** Esta entrega no modifica Compose, replica set,
credenciales, volúmenes ni bases de un compañero. El catálogo se carga mediante
mantenimiento explícito; no hay medicamentos DEMO ni cuentas creados al atender HTTP.

Los fixtures legacy A1/A2 quedan preservados, pero no se convierten automáticamente
en historias clínicas v2. Si existen pacientes reales o documentos históricos fuera
de este esquema, se requiere inventario, correspondencias verificadas y una
migración respaldada antes de habilitarlos. Esta entrega no certifica esa migración.
Tampoco agrega todavía operaciones de resultados de laboratorio/procedimientos.

## Verificación ejecutada

Entorno: Python 3.12.14, PyMongo 4.19.0, MongoDB 7.0.45 en replica set local dedicado
`a3`, Firestore Emulator 1.22.0 y SDK 2.34.1; Node 22 en contenedor para fixtures.
Sin datos reales, bases/volúmenes compartidos ni servicios Compose del proyecto.
Dependencias ya declaradas por backend; instalación de herramientas solo en work/.

| Comprobación final | Resultado |
|---|---|
| Suite común B1 y casos A3 contra los dos motores reales | **49 OK, 0 omitidas** |
| Django: núcleo/contrato en memoria, salud, fixtures y conexión Mongo | **48 OK, 0 omitidas** |
| Django check con config.test_settings | Sin incidencias |
| Cuatro archivos de pruebas React con Node 22 aislado | **33 OK, 0 omitidas** |
| Sintaxis Python, git diff --check, propiedad y preservación A1/React | Correctos |

Cada caso de integración genera una base `a3_test_<uuid>` y un proyecto emulado
`demo-a3-<uuid>`; no acepta URI remota ni una base activa. Cada peer usa cliente y
sesión independientes. La limpieza solo elimina los destinos generados del caso.
Se certificaron árbol/ocurrencias, búsquedas NFC/literales, duplicados institucionales
y simultáneos, ausencia de padres, permisos/profesional, cita/rollback/consumo,
archivo idempotente, nacimiento/fecha Guatemala, fallos después de mutaciones,
namespace no preparado y compatibilidad real con el modelo A1.

Para imponer los dos órdenes de confirmación de la suite compartida, el harness
Firestore intercepta **solo en pruebas** el commit del peer: si compite antes de la
primera confirmación, ejecuta rollback nativo para liberar sus locks y hace que el
SDK reintente tras el primer commit. Esperar manteniendo esos locks causaba un
deadlock de la propia barrera. Hay además carreras nativas sin imponer orden,
sin ese hook, y carreras contra diagnóstico/tratamiento/receta. No se atribuye al
servidor una regla de «el primero en comenzar siempre gana».

Las ejecuciones iniciales detectaron la indeterminación del ganador y después un
deadlock de la barrera de pruebas Firestore. Se corrigió el harness; la ejecución
final de 49 pruebas aprobó completa. No se suman como aprobadas las ejecuciones
fallidas ni las repeticiones. Las primeras pruebas se hicieron contra una copia
B1 aislada; la certificación final se ejecutó directamente desde feature/jennifer
con el núcleo ya sincronizado. No se reejecutó build/browser React ni se certificó
PostgreSQL/MySQL real en este módulo: sus fuentes no recibieron cambios propios.

### Reproducir desde el checkout completo

Preparar dos servicios dedicados: Mongo local con replica set `a3` y Firestore
local vacío. Los puertos siguientes son exclusivos del ejemplo de pruebas:

```bash
A3_NOSQL_TESTS=1 \
A3_MONGO_TEST_URI='mongodb://127.0.0.1:27039/?replicaSet=a3' \
A3_MONGO_SCHEMA="$PWD/db/mongo/clinical_schema.py" \
FIRESTORE_EMULATOR_HOST=127.0.0.1:8093 \
PYTHONPATH=backend \
python -m unittest apps.historiales.test_clinical_nosql -v

(cd backend && python manage.py test \
  apps.historiales.tests apps.historiales.test_database_health \
  apps.historiales.test_contract_sql apps.historiales.test_clinical_core \
  apps.historiales.test_repository_contract apps.historiales.test_mongo_nosql \
  --settings=config.test_settings)

npm --prefix frontend test
```

Sin A3_NOSQL_TESTS=1, las clases de integración se omiten explícitamente; esa
omisión nunca equivale a certificación de los motores.

## Continuación

A3 entrega persistencia contractual v2 probada. Integración HTTP real de cuatro
motores sigue siendo B5; este módulo no incorpora el PR #16 a Jennifer ni modifica
rutas centrales. Preparación de Mongo/catálogo y cualquier migración histórica
requieren el procedimiento del entorno correspondiente antes del flujo final.

Siguiente incremento A4: registro de diagnósticos, tratamientos, CAT-01/recetas,
archivo y especializaciones. Después, A5 debe demostrar React → API → cuatro motores,
permisos reales, recuperación clínica y evidencia académica. Los mocks y estas
pruebas de repositorio no sustituyen ese E2E.
