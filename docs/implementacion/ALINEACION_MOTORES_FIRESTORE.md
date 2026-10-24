# Alineación de motores y Firebase

La entrega usa una sola instancia de cada motor clínico: PostgreSQL (Hospital),
MySQL (Pediatría), MongoDB (Laboratorio) y Firestore (Odontología). La identidad
central reside en `hospital.identidad`, en el mismo PostgreSQL del Hospital; las
tablas clínicas permanecen en `hospital.public`. Un esquema no es otro motor ni
otra base. No se añade SQLite como almacén operativo en este despliegue.

`docker-compose.yml` ya no declara un segundo servidor PostgreSQL. La definición
anterior se conserva exclusivamente en `compose.identity-legacy.yml` para trasladar
y recuperar instalaciones existentes. No forma parte del arranque de entrega.

## Permisos y conservación de cuentas

- `identidad_migrator` posee exclusivamente el esquema `identidad`.
- `identidad_app` tiene DML y uso de secuencias de identidad, sin DDL ni privilegios
  de superusuario. No recibe permisos sobre las tablas clínicas de `public`.
- `hospital_runtime` conserva su acceso clínico, sin acceso al esquema privado.
- El traslado conserva usuarios y hashes de contraseña, grupos y permisos,
  profesionales, vínculos institucionales, sesiones y registros administrativos.
- El origen no se borra ni modifica. Una diferencia en un destino poblado cancela
  el traslado; una repetición idéntica se limita a verificarlo.

## Instalación existente: no recrear el backend antes del traslado

Actualizar Git no migra automáticamente las cuentas. El backend antiguo puede
seguir funcionando con su entorno anterior mientras se prepara el destino.

1. Conservar `.local/auc12/accesos.json` fuera del contenedor. Detener escrituras
   del backend; generar respaldos nuevos de Hospital e identidad y verificar su
   restauración en copias con `ops/auc12/verify_sql_backups.ps1 -LegacyIdentity`
   (además de `-BackupDir`). Las copias antiguas
   de identidad preceden a las cuentas iniciales y no bastan para este traslado.
2. Ejecutar `db/identity/consolidated-roles.sh` en el PostgreSQL hospitalario como
   propietario, usando las claves actuales app/migrator. Puede ejecutarse por el
   socket del contenedor si la clave propietaria del `.env` difiere de la del volumen.
   No cambiar la contraseña propietaria ni borrar volúmenes.
3. `docker compose --profile maintenance run --rm --no-deps identity-migrate`
   prepara el esquema nuevo, sin copiar ni crear cuentas.
4. Manteniendo disponible el PostgreSQL de identidad anterior, ejecutar
   `docker compose --profile maintenance run --rm --no-deps identity-consolidate`.
   El origen predeterminado es `identidad:5432/identidad`, esquema `public`.
   Si se necesita declarar/arrancar el servicio antiguo, añadir el archivo
   `-f compose.identity-legacy.yml` junto al Compose principal.
5. Comprobar el mensaje de conciliación. El directorio `.local/identity-backups`
   contiene un checkpoint privado con hashes y sesiones: no compartirlo ni subirlo.
6. Recrear únicamente el backend con la nueva configuración; comprobar inventario,
   los cuatro accesos, permisos y consultas clínicas. Conservar el origen antiguo
   detenido hasta terminar la aceptación. No usar `down -v` ni `--remove-orphans`.

La prueba local automatizada restauró 17 objetos de identidad (cuatro usuarios,
grupos, profesionales y perfiles, más una sesión), verificó contraseñas y relaciones,
repetición, rechazo de diferencias, rechazo de DDL y aislamiento clínico. Esto no
certifica que el traslado ya se ejecutó en Docker Desktop del usuario.

## Firestore: recomendación para la entrega

Usar **cloud en la demostración final** y el **emulador en desarrollo/pruebas**.
El PDF menciona Firebase y no exige expresamente cloud; cloud permite demostrar el
servicio real y su autenticación IAM. Requiere Internet y un proyecto configurado;
pueden aplicar cuotas o costes según el proyecto. Las pruebas del emulador no
certifican IAM, índices ni ejecución del servicio cloud.

El servidor admite dos modos explícitos:

- `FIRESTORE_MODE=emulator`: exige `FIRESTORE_EMULATOR_HOST`; usa credenciales
  anónimas exclusivamente contra ese host.
- `FIRESTORE_MODE=cloud`: exige un `FIREBASE_PROJECT_ID` real, prohíbe un host de
  emulador y usa Application Default Credentials privadas del servidor.

Para cloud:

1. Crear/seleccionar un proyecto Firebase y habilitar Firestore en modo nativo.
2. Configurar una identidad de servidor con acceso de datos Firestore
   (`roles/datastore.user` como punto de partida). El SDK servidor usa IAM;
   las reglas del cliente Firebase no sustituyen los permisos IAM ni los permisos
   institucionales que aplica Django.
3. Guardar la credencial ADC únicamente en `.local/firebase/credentials.json`,
   fuera de Git, y asignar `FIREBASE_PROJECT_ID` en `.env`. Nunca enviar el archivo
   por chat ni incorporarlo al frontend o a una imagen Docker.
4. Usar `docker compose -f docker-compose.yml -f compose.firestore-cloud.yml up -d backend frontend`.
   Este modo no inicia el emulador; un emulador previamente encendido se debe detener
   por separado, conservando antes sus datos.
5. Provisionar catálogos/profesionales de Odontología en el nuevo destino y validar
   registro, consulta, diagnóstico, tratamiento, receta y archivo con datos ficticios.
   Los documentos del emulador NO se copian automáticamente a cloud. Los vínculos
   profesionales existentes necesitan conservar sus referencias o conciliarlas.
6. Publicar los índices necesarios y verificar cualquier error `FAILED_PRECONDITION`
   con el índice solicitado por Firestore. No declarar cloud aceptado sin este ensayo.

## Persistencia del emulador

El Compose agrega el volumen `firestoredata`, importación y exportación al detenerse
normalmente (`--export-on-exit`) y 60 segundos de gracia. Una terminación forzada o
un fallo del host puede perder cambios posteriores al último checkpoint; no es una
sustitución de los respaldos ni la durabilidad del servicio cloud.

**Antes de recrear el emulador antiguo**, exportar sus documentos y copiar el
resultado al host; de otro modo sus datos en memoria se pierden. Dentro del servicio
antiguo, `firebase emulators:export /tmp/auc12-firestore --project demo-historiales`
genera el checkpoint. Copiarlo desde `hc_firestore` a un directorio nuevo privado del
host y verificar que contiene `firebase-export-metadata.json`. Después del cambio,
con el nuevo emulador detenido, colocar el contenido en `/data/export` del volumen
`firestoredata`; al iniciar se importa automáticamente. No recrear primero y exportar
después. Mantener los respaldos SQL/Mongo y el checkpoint Firestore separados.

## Estado de cierre

La configuración queda alineada; el cambio de la instalación del usuario y la
conexión cloud requieren sus correspondientes pruebas reales. AUC-12 permanece
abierto hasta completar la aceptación. `main` y la rama de Pablo no se modifican.
