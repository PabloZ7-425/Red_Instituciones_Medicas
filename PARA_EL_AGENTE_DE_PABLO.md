# Traspaso al agente de Pablo: actualizar `implementacion` sin perder su instalación

Fecha: 2026-10-24. Base de esta guía: `bdabbcf` (incluye `a1597a9` y `9332923`).
Pablo todavía no descargó estos cambios. **No se conoce el commit ni el estado real
actual de su computadora:** obtenerlos antes de decidir qué fases necesita. No
suponer que su Docker está igual que el de Rashell. Esta guía es una tarea de
configuración local y verificación; no autoriza merges a main ni cambios de otras ramas.

## Resultado esperado

Actualizar su copia de `implementacion`, conservar sus datos y accesos, y dejar:

| Institución | Destino |
|---|---|
| Hospital | PostgreSQL, servicio `postgres`, base `hospital`, esquema `public` |
| Identidad central | **El mismo** PostgreSQL y base `hospital`, esquema `identidad` |
| Pediatría | MySQL, servicio `mysql`, base `pediatrico` |
| Laboratorio | MongoDB, servicio `mongo`, base `laboratorio`, replica set `rs0` |
| Odontología | Firestore: emulador para desarrollo; cloud para la entrega cuando esté configurado y probado |

No levantar un segundo PostgreSQL de identidad en el despliegue final. Un esquema
no es otro motor. La definición antigua existe solamente en
`compose.identity-legacy.yml`, para trasladar/recuperar instalaciones anteriores.

## 1. Reconocer el punto de partida antes de actualizar

Ejecutar desde su repositorio y guardar resultados técnicos en `.local/pablo-upgrade/`:

```powershell
git status --short --branch
git rev-parse HEAD
git log -5 --oneline
git remote -v
docker compose version
docker compose ps -a
```

Inspeccionar los montajes y comandos de los contenedores concretos; no imprimir
`.Config.Env`, `.env`, archivos de accesos ni contraseñas. Identificar el nombre del
proyecto Compose existente y conservarlo: cambiarlo puede conectar volúmenes nuevos
vacíos. Los nombres `hc_*` son fijos y también pueden colisionar entre checkouts.

Antes de cambiar código, registrar configuración de identidad efectiva (SQLite,
PostgreSQL separado o ya consolidado), motor real, versiones de esquema y cantidades.
Si el backend funciona, usar el inventario de `ops/auc12/desktop_inventory.py` desde
el nuevo Git por stdin; no ejecutar seeds para conseguir un inventario.

Luego `git fetch origin implementacion` y comparar `HEAD...origin/implementacion`.
Con árbol limpio y rama local sin divergencias, actualizar con `git merge --ff-only
origin/implementacion`. Si tiene commits locales o cambios sin guardar, preservarlos
y revisar la divergencia antes de integrar; no usar reset --hard, force push ni
stash indiscriminado. No cambiarlo a main para hacer esta instalación.

**No ejecutar todavía `docker compose up -d` global:** recrearía el backend antes de
trasladar las cuentas y puede recrear un emulador con datos solamente en memoria.

## 2. Respaldar y verificar los datos reales

Durante el corte, detener escrituras del backend. Respaldar:

- Hospital: `pg_dump -Fc`, incluyendo todos los esquemas existentes.
- Pediatría: `mysqldump --single-transaction --routines --triggers --events
  --no-tablespaces --set-gtid-purged=OFF`.
- Mongo: `mongodump --archive=... --gzip`.
- Identidad: dump si es PostgreSQL; API `sqlite3.Connection.backup()` si es SQLite
  (una simple copia del archivo puede omitir WAL). Incluir perfiles y profesionales,
  grupos, permisos, hashes y sesiones, no solo usuarios.
- Firestore emulado: exportar **antes de recrear el contenedor**, con
  `firebase emulators:export /tmp/pablo-firestore --project demo-historiales` desde
  el emulador antiguo, y copiar al host el directorio completo con su metadata.
- Mantener privados `.env` y cualquier archivo de accesos ya generado.

Copiar los respaldos al host y probar restauración/conteos/huellas en destinos
nuevos; listar un dump no basta como prueba de restauración. No restaurar sobre las
bases originales. `ops/auc12/verify_sql_backups.ps1` verifica los tres respaldos SQL
históricos cuando existen. Para la identidad separada usar `-LegacyIdentity` además
de `-BackupDir`; incluir su Compose temporal y claves antiguas solo localmente.
Si identidad es SQLite o ya está consolidada, adaptar la prueba a ese origen: no
inventar un `identidad.dump` vacío ni iniciar un servidor adicional para simularlo.

## 3. Configuración privada

Conservar el `.env` existente; agregar solo las variables faltantes. Generar claves
fuertes distintas para los roles nuevos, guardarlas únicamente localmente:

| Variable | Uso |
|---|---|
| `PG_USER`, `PG_PASSWORD` | Propietario hospitalario de mantenimiento existente |
| `HOSPITAL_APP_PASSWORD` | `hospital_runtime`, conexión clínica del backend |
| `MYSQL_USER`, `MYSQL_PASSWORD` | Cuenta histórica MySQL; no confundirla con runtime |
| `MYSQL_ROOT_PASSWORD` | Mantenimiento MySQL existente |
| `PEDIATRIA_APP_PASSWORD` | `pediatria_runtime`, conexión clínica del backend |
| `IDENTITY_APP_PASSWORD` | `identidad_app`, lectura/escritura de identidad sin DDL |
| `IDENTITY_MIGRATOR_PASSWORD` | `identidad_migrator`, migraciones del esquema identidad |
| `IDENTITY_OWNER_PASSWORD` | Solo servidor de identidad antiguo, si existe |
| `DJANGO_SECRET_KEY` | Conservar la actual para mantener sesiones válidas |

Cambiar `.env` **no cambia las claves almacenadas en un volumen existente**. Si la
clave propietaria no coincide, usar acceso local por socket dentro del contenedor
con su configuración real; no restablecer root/propietario ni borrar el volumen.
Las claves runtime de `.env` deben coincidir con las configuradas por los scripts
de roles. No enviar secretos por chat ni guardarlos en documentación/Git.

## 4. Preparar esquemas SQL (ensayar antes en copias restauradas)

Comparar inventario y aplicar solamente lo necesario, en este orden:

Hospital:
1. `db/postgres/migrations/001_expand.sql`
2. `db/postgres/migrations/002_finalize.sql`
3. `db/postgres/operations_upgrade.sql`
4. `db/postgres/runtime_role.sql` (variable psql `app_password` = clave runtime)
5. `db/postgres/operations_runtime.sql`

Pediatría:
1. `db/mysql/migrations/001_expand.sql`
2. `db/mysql/migrations/002_reconcile.sql`
3. `db/mysql/migrations/003_finalize.sql`
4. `db/mysql/operations_upgrade.sql`
5. Configurar runtime mediante la fase `roles` de `db/mysql/migrate.sh`.
6. `db/mysql/operations_runtime.sql`

Los wrappers `hospital-migrate` y `pediatria-migrate` permiten inventario/fases de
mantenimiento; revisar sus opciones antes de invocarlos. `all` no reemplaza la
aplicación de los archivos `operations_upgrade.sql`/`operations_runtime.sql`.
Verificar B3 `B3-1.0.0`, B4 versión `1`, flags booleanos y permisos. Ante una
conciliación conflictiva, resolver los datos detectados; no desactivar restricciones.

En PowerShell usar UTF-8 sin BOM para stdin y restaurar `$OutputEncoding` en finally.
Normalizar CRLF de scripts shell con `tr -d '\015' | sh`; evitar heredocs enviados
a Linux sin normalización. Comprobar `$LASTEXITCODE` tras cada comando nativo y no
continuar fases dependientes si falla. Nunca imprimir variables de contraseña.

## 5. Identidad: seleccionar la ruta según su inventario

### A. Ya está en `hospital.identidad`

Verificar roles, 19 migraciones esperadas para la versión actual, cuentas y vínculos.
No ejecutar el traslado otra vez si el origen antiguo ya no existe. No recrear cuentas.

### B. Usa el servidor PostgreSQL separado

Seguir [Alineación de motores](docs/implementacion/ALINEACION_MOTORES_FIRESTORE.md).
Con backend detenido, respaldos nuevos restaurados y origen disponible:

1. Ejecutar `db/identity/consolidated-roles.sh` como propietario en Hospital.
2. `docker compose --profile maintenance run --rm --no-deps identity-migrate`.
3. `docker compose --profile maintenance run --rm --no-deps identity-consolidate`.
4. Revisar conciliación y conservar el origen sin modificaciones. El helper conserva
   usuarios/hashes/grupos/permisos/profesionales/perfiles/sesiones/admin log; usa el
   migrator para restaurar secuencias, sin ampliar permisos runtime.

Agregar `-f docker-compose.yml -f compose.identity-legacy.yml` cuando necesite
reconocer/arrancar el servicio anterior; mantener el mismo proyecto Compose. No usar
`--remove-orphans`: el origen antiguo se conserva hasta completar la aceptación.

### C. Identidad SQLite heredada

No usar `consolidate_identity.py`: **solo admite origen PostgreSQL**.
`transfer_identity` existente permite SQLite **sin perfiles B2 poblados** y copia
usuarios/grupos, no sesiones. Inventariar tablas y contenido primero.

Si ya hay perfiles/profesionales, el agente debe preparar y probar un traslado
ampliado sobre una copia SQLite: exportar el conjunto completo de identidades con
claves naturales para permisos/contenttypes, importar en el destino vacío usando
`identity_migration`, reajustar secuencias y comparar hashes/relaciones/conteos antes
del corte. Reutilizar el patrón transaccional de `consolidate_identity.py`. Conservar
las referencias externas de profesionales. No ejecutar el comando limitado y luego
reconstruir roles adivinándolos. Si faltan asignaciones institucionales antiguas,
conciliarlas con Pablo sin conceder admin a todos. No declarar esta ruta ya probada:
la evidencia actual cubre el traslado PostgreSQL, no este caso ampliado.

### D. Instalación nueva sin cuentas

Preparar roles/esquema y migrar identidad directamente en Hospital. Después de
preparar los cuatro proveedores se puede ejecutar `ops/auc12/setup_initial_accounts.py`
con `AUC12_SETUP=create-initial-accounts`. Copiar `/tmp/auc12-accesos.json` al host y
mantenerlo privado. No sustituir las cuentas previas de Pablo por cuentas DEMO.

## 6. MongoDB y Firestore

Mongo: inspeccionar comando y volumen actual. Si es standalone, verificar respaldo
antes de recrear **solo mongo**, conservando exactamente el volumen montado en
`/data/db`, ahora con `mongod --bind_ip_all --replSet rs0`. Ejecutar `mongo-init` y
comprobar `isWritablePrimary`. No reiniciar un replica set existente ni volver a
sembrar legacy. Preparar, con las herramientas de mantenimiento del repositorio:

1. `db/mongo/clinical_schema.py --apply`
2. `db/mongo/specialty_schema.py --apply`
3. `db/mongo/operations_schema.py --apply`

Leer cada script y configurar su URI de setup explícita (`MONGO_CLINICAL_SETUP_URI`)
al destino correcto. Legacy y colecciones `clinico_*` son distintas; preparar
colecciones no migra automáticamente registros clínicos antiguos a schema_version=2.
Si Pablo tiene registros legacy, conservarlos y ensayar su migración antes de
prometer que todos serán visibles desde el nuevo flujo.

Firestore: para desarrollo conservar emulador. El nuevo volumen `firestoredata`
importa `/data/export` y exporta al detenerse normalmente; copiar allí el checkpoint
antiguo **con el emulador detenido**, antes de iniciarlo. Verificar un documento
ficticio tras un reinicio controlado. No garantiza recuperación de cambios tras una
terminación forzada; conservar checkpoints independientes.

Para la entrega recomendamos cloud, pero **no bloquear la instalación local por no
tenerlo aún**. Ver `compose.firestore-cloud.yml` y la guía de alineación: proyecto
real, Firestore nativo, ADC privado en `.local/firebase/credentials.json`, IAM de
servidor, índices y prueba real. No se han probado credenciales/IAM cloud. Los datos
del emulador no se copian automáticamente: preservar IDs de profesionales o conciliar
sus vínculos B2 al trasladarlos. No activar cloud sin un destino y credenciales válidos.

No ejecutar `ops/bootstrap_local.py` como actualización universal: tiene datos DEMO
y supuestos de infraestructura específicos. Preferir los pasos de mantenimiento
anteriores y el loader idempotente de catálogos cuando se necesiten datos ficticios.

## 7. Corte, arranque y aceptación

Solo después de conciliar identidad y proveedores:

```powershell
docker compose up -d --build --no-deps backend
docker compose up -d --build --no-deps frontend
docker compose ps -a
```

Conservar/detener el servidor antiguo de identidad, sin borrarlo. La app abre en
`http://localhost:5173`; API `http://localhost:8000/api`.

Validar:
- Inventario sin migraciones pendientes, acceso de los cuatro proveedores y roles runtime.
- Accesos previos de Pablo, instituciones y roles conservados; no solo las cuentas DEMO.
- Por institución: paciente ficticio nuevo, consulta, diagnóstico, tratamiento, receta,
  lectura del historial y archivo; impedir nuevas atenciones del paciente archivado.
- Hospital: cama/ingreso/traslado/alta y stock. Pediatría: vacuna, crecimiento,
  examen/resultado, factura/pago y cobertura. Laboratorio: resultados con estructura
  variable. Odontología: procedimiento por pieza y su historial.
- Catálogos: alta/edición/desactivación, referencias históricas y consulta nativa del
  dato guardado. `seed_demo_catalogs.py`, con `AUC12_SETUP=seed-demo-catalogs`, es
  opcional: hasta 24 filas PRUEBA; no crea pacientes ni restablece existencias.
- Permisos: usuario de otra institución/rol no puede leer/escribir datos ajenos;
  profesional deshabilitado pierde acceso clínico.
- Persistencia tras un reinicio controlado, sin borrar volúmenes.

DataGrip: Hospital `localhost:5432/hospital` usuario `hospital_runtime`, contraseña
`HOSPITAL_APP_PASSWORD`; Pediatría `localhost:3307/pediatrico`, usuario
`pediatria_runtime`, contraseña `PEDIATRIA_APP_PASSWORD`. Mongo local actual:
`mongodb://localhost:27017/laboratorio?directConnection=true` (sin auth solo si así
está realmente configurado). Identidad es esquema `identidad`, no una nueva conexión
propietaria para que todos vean contraseñas. Firestore UI local `localhost:4000`.

## 8. Evidencia y recuperación

Entregar un reporte técnico sin secretos: commits antes/después, motores y volúmenes
identificados, respaldos restaurados, migraciones aplicadas, cuentas/perfiles antes y
después, pruebas aprobadas, fallos y pendientes. No cerrar AUC-12 ni anunciar merge
viable basándose solo en servicios healthy o catálogos cargados.

Si falla antes del corte, el origen queda conservado y backend detenido: corregir o
volver al código/configuración de conexión anterior registrado. Si ya hubo escrituras
en el destino nuevo, no revertir simplemente la conexión a la copia antigua: primero
respaldar y conciliar los cambios posteriores para evitar perder cuentas/sesiones.
No restaurar backups encima de bases activas como primera reacción.

Evidencia disponible: 117 pruebas nativas + 4 de configuración Firestore, ensayo de
traslado PostgreSQL con 17 objetos y permisos restringidos. Ver
`docs/implementacion/ALINEACION_MOTORES_VERIFICACION.json`. Esto no certifica la
instalación de Pablo, no cubre un traslado SQLite B2 ampliado y no certifica cloud.
