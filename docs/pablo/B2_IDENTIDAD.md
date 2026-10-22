# B2 — Identidad y acceso institucional

Responsable: Pablo. Rama permanente: `feature/pablo`. Fecha local: 2026-10-21.
Base: B1 integrado mediante PR #12 (`ee2a24c`). Contratos API/REPO: **1.0.0**.

## Alcance implementado

Django User estándar conserva hashing, permisos técnicos y admin. La app
`apps.identidad` agrega `PerfilInstitucional` y `Profesional`: institución/rol/estado
del perfil y referencia institucional del profesional habilitado. No hay modelos ORM
clínicos, credenciales paralelas ni Firebase Auth. FK, unicidad y checks SQL limitan
instituciones/roles y restringen laboratorista a laboratorio. La validación de modelo
y del principal rechaza profesionales de otra institución.

| Ruta | Conducta |
|---|---|
| GET `/api/auth/csrf/` | Anónima; devuelve csrfToken y cookie csrftoken; sin caché |
| POST `/api/auth/login/` | JSON username/password, CSRF incluso anónimo; 200 usuario y sesión rotada |
| GET `/api/auth/me/` | 200 usuario del principal vigente; 401 sin sesión/expirada |
| POST `/api/auth/logout/` | Sesión + CSRF; 204 sin cuerpo y sesión invalidada |

Login recorta username y preserva password exactamente. Datos malformados/desconocidos
son 400; credenciales inválidas, cuenta inactiva o perfil inválido dan el mismo 401.
Al acceder con sesión, perfil revocado/institución inválida es 403. No hay bypass
clínico de superusuario técnico. Se rechazan parámetros de query en estas rutas.
El traductor común de errores conserva envelopes de contrato y evita exponer errores
SQL, contraseñas o trazas; los fallos de base durante la vista se traducen a 503.

`InstitutionalSessionAuthentication` comprueba cada petición contra el perfil actual,
construye `request.contexto_clinico` y exige sesión clínica con marca temporal válida.
Una sesión del admin técnico por sí sola no habilita el flujo clínico. B5 debe heredar
`IdentityView` o declarar explícitamente esta autenticación e IsAuthenticated en sus
vistas, y usar ese contexto al llamar a la factory B1. Los endpoints públicos de
salud conservan su conducta. El profesional deshabilitado/no vinculado impide
escrituras profesionales de B1; no se inventa uno al autenticar.

Cada login válido reemplaza la sesión anterior y rota CSRF, incluso para el mismo
usuario. `sessionid` es HttpOnly, SameSite=Lax y expira al cerrar navegador. La marca
de login se verifica en el servidor con límite absoluto de ocho horas sin extensión
por actividad; logout elimina la sesión en base, y cambiar password la invalida.
En HTTPS configurar `DJANGO_COOKIE_SECURE=true`; ambas cookies llevan Secure.
Cerrar navegador depende de su política de restauración; el límite del servidor
siempre se aplica. No se guarda token en localStorage.

CORS con credenciales y CSRF confiable solo admiten `http://localhost:5173` además
del mismo origen permitido por Django. Usar localhost en ambos lados, no mezclar
127.0.0.1. React debe enviar `credentials: include`, pedir csrf antes y después de
login, y mandar X-CSRFToken en escrituras. No se modificó frontend ni fuentes NoSQL A.

## PostgreSQL técnico y privilegios

Servicio Compose `identidad`, base `identidad`, volumen nuevo `identitydata`, sin
puerto expuesto al host. Usa PostgreSQL 16 como motor técnico de cuentas, separado
de hospital; no es una quinta institución ni otro motor institucional.

| Rol técnico | Uso y permisos |
|---|---|
| identidad_owner | Bootstrap del contenedor; no se entrega su contraseña al backend |
| identidad_migrator | Mantenimiento/DDL en identidad; sin superuser, createdb ni createrole |
| identidad_app | Runtime: conexión, uso de schema y DML de tablas/secuencias; sin DDL/createdb/createrole |

`db/identity/01-roles.sh` solo corre sobre un volumen vacío, con ON_ERROR_STOP y
contraseñas tomadas del entorno. Las concesiones por defecto del migrator cubren
tablas y secuencias creadas por sus migraciones. El proceso backend solo recibe la
clave de identidad_app; el servicio con perfil `maintenance` recibe la del migrator.
No se usa el rol hospitalario para identidad.

Se retiró `migrate` del arranque del backend. El servicio `identity-migrate` tiene
comando explícito `migrate --database identity_migration`; no se ejecuta al iniciar
el proyecto normalmente. No mover cuentas automáticamente al levantar Compose.
Conservar las claves configuradas si ya existe identitydata: cambiar .env no cambia
las contraseñas dentro de un volumen existente.

## Configurar una instalación nueva

1. Copiar `.env.example` sin sobrescribir un `.env` existente. Generar tres claves
   diferentes para IDENTITY_OWNER_PASSWORD, IDENTITY_MIGRATOR_PASSWORD e
   IDENTITY_APP_PASSWORD. Se pueden generar localmente con
   `python -c "import secrets; print(secrets.token_urlsafe(36))"`.
2. Para una instalación sin cuentas previas, usar IDENTITY_DB_MODE=postgres.
3. Construir y preparar el esquema antes de servir autenticación:

```powershell
docker compose build backend frontend firestore identity-migrate
docker compose up -d identidad
docker compose run --rm identity-migrate
docker compose up -d
docker compose exec -T backend python manage.py check --database default
```

No publicar `.env`, respaldos ni fixtures de identidades reales. `.local/` y SQLite
están ignorados. El SQLite se retiró del índice con `git rm --cached` conservando
el archivo local de este checkout; respaldar el SQLite propio antes de actualizar
otro checkout que aún lo tenga versionado.

## Traslado desde SQLite existente

Mantener IDENTITY_DB_MODE=legacy durante preparación/ensayo. Detener el backend
para impedir cambios de cuentas durante el corte. `legacy` es alias de lectura sola
del archivo original; `identity_migration` apunta a PostgreSQL con el migrator.
El mantenimiento no requiere arrancar los motores clínicos.

```powershell
docker compose stop backend
docker compose up -d identidad
docker compose run --rm identity-migrate
docker compose run --rm identity-migrate python manage.py transfer_identity --source legacy --target identity_migration --backup-dir /backups/corte-unico
docker compose run --rm identity-migrate python manage.py transfer_identity --source legacy --target identity_migration --backup-dir /backups/corte-unico --verify-only
```

Usar un directorio de corte nuevo. `transfer_identity` crea copia SQLite consistente
y JSON privado con creación exclusiva; no sobrescribe backups ni cuentas de destino.
Lee el snapshot inmutable, reconoce hashes Django y conserva IDs, hashes sin cambios,
grupos y permisos mediante claves naturales. La carga y la conciliación ocurren en
una transacción PostgreSQL con bloqueo de las tablas técnicas. Un fallo o diferencia
revierte las filas importadas. También cancela si detecta cambios del origen.
Los hashes no reconocidos requieren conciliación, nunca se convierten en contraseña.
No importa sesiones ni asigna perfiles/roles clínicos por suposición.
Si el origen ya contiene perfiles B2, cancela y exige un traslado ampliado.

Tras respaldo, ensayo y conciliación, cambiar IDENTITY_DB_MODE=postgres en `.env`
y recrear solo el backend: `docker compose up -d --no-deps backend`. Asignar perfiles
institucionales expresos antes de que usuarios heredados accedan a clínica. Verificar
/me, logout y salud; no abrir escrituras hasta terminar la revisión.

Reversión inmediata antes de nuevas escrituras de identidad: detener backend,
conservar PostgreSQL y los backups, volver al backend anterior B1 y al SQLite
original con modo legacy. La fuente no se modifica en el traslado. El ensayo verifica
integridad y autenticación desde la copia SQLite recuperada. Después de nuevas altas
o cambios de cuentas en PostgreSQL, reconciliar esos cambios en un destino de
reversión separado antes de cambiar la configuración; no descartar cuentas nuevas.
No se ensayó un corte de servicio con usuarios reales: el inventario local es cero.

## Cuentas DEMO y admin técnico

Crear cada cuenta local con contraseña solicitada por getpass, sin eco ni claves en
Git/argumentos. El comando valida contraseña, usa hashing Django y no sobrescribe
una cuenta existente. Elegir referencias profesionales que realmente correspondan
al motor institucional; B3/B4/A3 verificarán su existencia/estado al escribir clínica.

```powershell
docker compose run --rm identity-migrate python manage.py create_demo_identity --username DEMO-hospital --institucion hospital --rol medico --professional-id REFERENCIA_REAL --database identity_migration
```

Repetir para pediatrico, laboratorio y odontologica con nombres y referencias
propios. El comando crea cuentas sin permisos de superusuario/staff. Para administrar
perfiles desde Django Admin, crear una cuenta técnica expresamente con
`docker compose run --rm identity-migrate python manage.py createsuperuser --database identity_migration`.
Una cuenta técnica no obtiene acceso clínico por ser superusuario.

## Pruebas y evidencia

La suite principal usa PostgreSQL y SQLite sintético separados del origen real.
Precrear **solo si no existe** `test_b2_identidad` con propietario identidad_migrator
(el migrator no tiene CREATEDB):

```powershell
docker compose exec -T identidad psql -U identidad_owner -d identidad -c "CREATE DATABASE test_b2_identidad OWNER identidad_migrator"
docker compose run --rm -e TEST_IDENTITY_POSTGRES=1 identity-migrate python manage.py test apps.identidad apps.historiales --settings=config.test_settings --keepdb
```

`--keepdb` conserva únicamente la base de pruebas. Nunca apuntar TEST.NAME a identidad
ni a hospital. `config.test_settings` usa SQLite efímero si no se activa la variable:
en ese caso las pruebas de traslado real se omiten explícitamente. Los tests HTTP
usan Client con enforce_csrf_checks=True. La suite rápida usa un hasher de pruebas;
el hashing productivo y los traslados se verifican con PBKDF2 de Django.

Se probaron login/CSRF/rotación/logout/replay, expiración absoluta, baja/cambio de
perfil, falta de perfil, superusuario sin bypass, CORS, cookies Secure, rechazo de
inyección de institución, cruce de profesional/institución, permisos B1 y mismo 404
para recurso ausente/ajeno. El ensayo de traslado comprueba hashes/IDs, grupos,
permisos/secuencias, fuente intacta, backup autenticable, contraseñas inutilizables,
hash desconocido, fallo tras importar, destino ocupado y perfiles B2 incompatibles.

Verificación local aplicada: fuente SQLite **0 usuarios**, backup y conciliación
correctos en `.local/identity-backups/corte-b2-20261021`, PostgreSQL activado después
del ensayo. Se comprobó identidad_app sin CREATE en base/schema y con DML necesario;
el backend no recibe contraseña de migrator. Un smoke HTTP real recorrió las cuatro
instituciones con cuentas sintéticas temporales y confirmó CSRF/login/me/logout;
esas cuentas y sesiones se retiraron al terminar. Comandos/resultados y SHA finales
se registran en el PR. Los datos/volúmenes clínicos se conservaron.

Resultados finales de esta ejecución (código del commit indicado en el PR):

| Comprobación | Resultado |
|---|---|
| Suite PostgreSQL indicada arriba, con SQLite sintético para traslado | 85 aprobadas, 0 omitidas, salida 0 |
| `node --test frontend/tests/contract-fixtures.test.js` | 8 aprobadas, salida 0 |
| `compose exec -T backend python manage.py check --database default` | Sin incidencias, salida 0 |
| `manage.py makemigrations --check --dry-run --settings=config.test_settings` | No changes detected, salida 0 |
| `docker compose config -q` | Salida 0 |
| `compose run --rm --no-deps frontend npm run build -- --outDir /tmp/rim-b2-dist` | Vite correcto, salida 0; sin archivos nuevos en frontend |
| Salud backend y cuatro motores | HTTP 200 y cuatro connected=true |
| `transfer_identity ... --verify-only` | Conciliación correcta, salida 0 |
| SQLite conservado tras retirarlo del índice | Hash Git idéntico al archivo de B1 |
| Usuarios/perfiles persistentes tras smoke HTTP | 0 / 0; fixtures retiradas |

La suite PostgreSQL usa Python 3.13/Django 5.2.18 dentro de Docker. También se
ejecutaron inicialmente 74 pruebas de núcleo/auth con SQLite efímero en Python 3.12.7
local; el resultado definitivo de traslado es el de PostgreSQL, sin omisiones.

B2 no implementa API-03..10 ni catálogo clínico: son B5; tampoco certifica los
repositorios reales B3/B4/A3 ni configura replica set Mongo. Jennifer puede consumir
las cuatro rutas de autenticación sin editar sus componentes desde esta célula.

Referencias técnicas consultadas: [sesiones Django 5.2](https://docs.djangoproject.com/en/5.2/topics/http/sessions/),
[CSRF Django](https://docs.djangoproject.com/en/5.2/ref/csrf/),
[SessionAuthentication DRF](https://www.django-rest-framework.org/api-guide/authentication/#sessionauthentication).
