# Prueba local de React y Django con Docker

La rama `implementacion` sirve el frontend compilado en [localhost:5173](http://localhost:5173/) y la API Django en [localhost:8000/api/](http://localhost:8000/api/). Los formularios llaman a Django y guardan datos en PostgreSQL (Hospital), MySQL (Pediatría), MongoDB (Laboratorio) y el emulador persistente de Firestore (Odontología). Los datos y las cuentas de ejemplo de esta guía son ficticios.

## 1. Elegir la ruta de arranque

Abre Docker Desktop. En PowerShell, desde la raíz del repositorio, revisa el estado de Git y Docker:

```powershell
git status --short --branch
git fetch origin implementacion
docker compose version
docker compose ps -a
```

En una copia limpia, cambia a `implementacion` y actualízala con `git merge --ff-only origin/implementacion`. Si hay ediciones locales o commits propios, consérvalos y resuelve la actualización antes de ejecutar Compose. Los nombres `hc_*` y los puertos del Compose raíz son fijos. Usa un solo checkout activo por equipo y cierra el Vite local si ocupa el puerto 5173.

- **Instalación existente con datos o cuentas.** Sigue el [traspaso para Pablo](../../PARA_EL_AGENTE_DE_PABLO.md) y conserva el nombre del proyecto Compose. Antes de recrear servicios, haz respaldos restaurables, exporta Firestore y comprueba si la identidad ya vive en `hospital.identidad`. Después del traslado y la conciliación, continúa en la sección 3 con tus cuentas. Si Docker lista un servidor `identidad` antiguo, consérvalo como recuperación hasta validar los accesos en el nuevo esquema.
- **Instalación nueva con volúmenes vacíos.** Sigue la sección 2. Una carpeta recién clonada también puede apuntar a volúmenes existentes si conserva el mismo nombre de proyecto. Si tienes dudas, usa la ruta de instalación existente.

## 2. Preparar una instalación nueva

Copia `.env.example` a `.env` si aún no existe. Configura claves privadas y distintas para `PG_PASSWORD`, `MYSQL_PASSWORD`, `MYSQL_ROOT_PASSWORD`, `HOSPITAL_APP_PASSWORD`, `PEDIATRIA_APP_PASSWORD`, `IDENTITY_APP_PASSWORD` e `IDENTITY_MIGRATOR_PASSWORD`. Agrega una `DJANGO_SECRET_KEY` local. El Compose normal usa el emulador. `IDENTITY_OWNER_PASSWORD` se reserva para recuperar instalaciones con el servicio antiguo. Mantén `.env`, los accesos y los respaldos fuera de Git.

Define este ayudante en la misma ventana de PowerShell. Así, cada bloque se detiene al fallar un comando nativo.

```powershell
function Invoke-RimCompose {
    & docker compose @args
    if ($LASTEXITCODE -ne 0) { throw "Docker Compose terminó con código $LASTEXITCODE" }
}
$rimRepo = (Get-Location).Path
$rimRun = @('run', '--rm', '--no-deps', '-T')
$rimMaintenance = @('--profile', 'maintenance') + $rimRun

Invoke-RimCompose config --quiet
Invoke-RimCompose build backend frontend firestore identity-migrate
Invoke-RimCompose up -d --wait --wait-timeout 240 postgres mysql mongo mongo-init firestore
```

Aplica los esquemas y permisos SQL. Los scripts de migración guardan sus respaldos bajo `.local/`. El backend se conecta con los roles limitados configurados en este paso.

```powershell
Invoke-RimCompose @rimMaintenance hospital-migrate bash /schema/migrate.sh all
Invoke-RimCompose @rimMaintenance pediatria-migrate bash /schema/migrate.sh all
Invoke-RimCompose @rimMaintenance hospital-migrate psql -X -v ON_ERROR_STOP=1 -f /schema/operations_upgrade.sql -f /schema/operations_runtime.sql
Invoke-RimCompose @rimMaintenance pediatria-migrate sh -ec 'export MYSQL_PWD=$MYSQL_ROOT_PASSWORD; mysql -h mysql -u root pediatrico < /schema/operations_upgrade.sql; mysql -h mysql -u root pediatrico < /schema/operations_runtime.sql'
Invoke-RimCompose @rimMaintenance identity-schema
Invoke-RimCompose @rimMaintenance identity-migrate
```

Cuando MongoDB esté en estado PRIMARY, prepara las colecciones clínicas y arranca la aplicación. El inicializador legado `db/mongo/init.js` queda como referencia para instalaciones antiguas.

```powershell
Invoke-RimCompose @rimRun -e 'MONGO_CLINICAL_SETUP_URI=mongodb://mongo:27017/laboratorio?replicaSet=rs0' -v "${rimRepo}/db/mongo:/schema:ro" backend sh -ec 'python -B /schema/clinical_schema.py --apply; python -B /schema/specialty_schema.py --apply; python -B /schema/operations_schema.py --apply'
Invoke-RimCompose up -d --wait --wait-timeout 240 backend frontend
Invoke-RimCompose ps -a
```

En esta instalación nueva, crea los cuatro administradores clínicos ficticios con sus vínculos profesionales y carga los catálogos de prueba. Guarda `.local/auc12/accesos.json` de forma privada. Si ya tienes cuentas, usa sus accesos actuales y revisa los catálogos antes de preparar datos adicionales.

```powershell
New-Item -ItemType Directory -Force .local/auc12 | Out-Null
Invoke-RimCompose @rimRun -e AUC12_SETUP=create-initial-accounts -e AUC12_ACCESS_FILE=/private/accesos.json -e PYTHONPATH=/app -v "${rimRepo}/ops:/ops:ro" -v "${rimRepo}/.local/auc12:/private" backend python -B /ops/auc12/setup_initial_accounts.py
Invoke-RimCompose @rimRun -e AUC12_SETUP=seed-demo-catalogs -e PYTHONPATH=/app -v "${rimRepo}/ops:/ops:ro" backend python -B /ops/auc12/seed_demo_catalogs.py
```

El catálogo de prueba usa nombres `PRUEBA`. El cargador conserva las filas existentes. Estas cuentas sirven para entrar en Django y operar sobre Docker.

## 3. Probar el backend

Comprueba que los cuatro motores respondan a través de Django. El estado HTTP de la ruta puede ser 200 aunque alguna conexión falle, por lo que hay que revisar el campo `connected` de cada institución.

```powershell
$rimHealth = Invoke-RestMethod 'http://localhost:8000/api/health/databases/'
$rimHealth.databases.PSObject.Properties | ForEach-Object {
    '{0}: {1}' -f $_.Name, $_.Value.connected
}
```

Para comprobar login, institución, lectura de pacientes y medicamentos, logout y rechazo después del logout, usa el archivo privado con las cuatro cuentas y un catálogo de medicamentos con al menos una entrada por institución. Si los accesos están en otro archivo, ajusta la ruta. El script usa la API a través de la red de Compose y muestra solo el resultado de cada institución.

```powershell
$rimRepo = (Get-Location).Path
docker compose run --rm --no-deps -T -v "${rimRepo}/ops:/ops:ro" -v "${rimRepo}/.local/auc12/accesos.json:/private/access.json:ro" backend python -B /ops/check_local.py
```

Las rutas principales son `/api/auth/csrf/`, `/api/auth/login/`, `/api/auth/me/`, `/api/pacientes/`, `/api/pacientes/{id}/historial/` y `/api/operaciones/`. El login requiere cookies y el token CSRF. Usa los contratos de [B5](../pablo/B5_API_INTEGRACION.md) y [operaciones](README.md#api-y-reglas) para peticiones de escritura.

## 4. Probar el frontend y confirmar persistencia

1. Abre [localhost:5173](http://localhost:5173/) con ese nombre de host. Inicia sesión con una cuenta de cada institución. Comprueba el nombre de la institución y su menú de operaciones.
2. En cada institución, da de alta un paciente ficticio con un identificador único. Guarda una consulta, agrega diagnóstico y tratamiento, y registra una receta con un medicamento de prueba. Recarga el navegador y vuelve a abrir el expediente.
3. Comprueba una operación propia de cada institución.

   | Institución | Recorrido |
   | --- | --- |
   | Hospital | Ingresar al paciente en una cama, trasladarlo y darle de alta. |
   | Pediatría | Registrar vacuna y control de crecimiento. |
   | Laboratorio | Registrar un resultado numérico o de texto desde un tipo de examen. |
   | Odontología | Registrar un procedimiento en una pieza dental y volver a abrir el seguimiento. |

4. Conserva el identificador del expediente y prueba desde otra institución que no se puede abrir el historial ajeno. Con una cuenta administradora, archiva al paciente ficticio cuando termines y comprueba que no admite una nueva consulta.
5. Para comprobar que Firestore guarda el cambio en el volumen local, haz un reinicio controlado sin usuarios escribiendo. Espera a que vuelva a estar sano y comprueba el mismo expediente de Odontología.

   ```powershell
   docker compose restart --timeout 60 firestore
   docker compose up -d --no-recreate --no-build --no-deps --wait --wait-timeout 240 firestore
   ```

La prueba de Firebase Cloud es independiente y requiere un proyecto, credenciales privadas e índices. Sigue la [guía de Firestore](ALINEACION_MOTORES_FIRESTORE.md#firestore-recomendación-para-la-entrega) si la entrega usa ese servicio.

## 5. Entender los contenedores

| Servicios | Función |
| --- | --- |
| `frontend`, `backend` | Sirven React y la API Django. |
| `postgres`, `mysql`, `mongo`, `firestore` | Guardan los datos de las cuatro instituciones. La identidad también está en `postgres`, en el esquema `hospital.identidad`. |
| `adminer` | Interfaz opcional de inspección SQL en [localhost:8081](http://localhost:8081/). |
| `mongo-init` | Inicializa o comprueba el replica set. El estado esperado después del arranque es `Exited (0)`. |

`docker compose ps -a` incluye servicios detenidos y tareas terminadas. Para investigar un fallo revisa `docker compose logs --tail 100 <servicio>` y la salud de los motores. Detén los servicios con `docker compose stop` si quieres conservar contenedores y volúmenes. Reserva `down -v` para proyectos desechables con volúmenes de prueba.
