# Red de Instituciones Médicas

Aplicación de agenda, expedientes y atención clínica para cuatro instituciones. React sirve la interfaz y Django conecta cada institución con su base de datos.

| Institución | Motor en Docker | Recorrido de ejemplo |
| --- | --- | --- |
| Hospital general | PostgreSQL | Consulta, ingreso, traslado, alta, cirugía, farmacia y caja |
| Centro médico pediátrico | MySQL | Tutor, crecimiento, vacunación, examen y seguro |
| Laboratorio clínico | MongoDB | Tipos de examen y resultados en distintos estados |
| Clínica odontológica | Emulador de Firestore | Expediente, procedimientos por pieza y odontograma |

## 1. Descargar

Abre Docker Desktop. Usa PowerShell con Git y Docker Compose disponibles.

```powershell
git clone --branch codex/entrega-limpia --single-branch https://github.com/PabloZ7-425/Red_Instituciones_Medicas.git
Set-Location Red_Instituciones_Medicas
docker compose version
```

En un equipo con una instalación anterior, trabaja desde la copia que ya usa Docker. Conserva su nombre de proyecto, su archivo `.env` y sus volúmenes. Los nombres de contenedor y los puertos del proyecto son fijos, por lo que una segunda copia activa puede chocar con la primera. Para una instalación antigua con identidad separada, consulta la [alineación de motores](docs/implementacion/ALINEACION_MOTORES_FIRESTORE.md) antes de actualizar.

Si ya tienes el repositorio, descarga y selecciona la rama desde esa copia.

```powershell
git fetch origin refs/heads/codex/entrega-limpia:refs/remotes/origin/codex/entrega-limpia
git switch codex/entrega-limpia
git merge --ff-only origin/codex/entrega-limpia
```

## 2. Preparar el entorno local

En una instalación nueva, este bloque crea `.env` a partir de `.env.example` y genera valores locales distintos para las claves. Si ya tienes `.env`, el bloque lo reutiliza. Mantén ese archivo y los accesos de ejemplo fuera de Git.

```powershell
if (-not (Test-Path -LiteralPath '.env')) {
    $claves = @(
        'PG_PASSWORD', 'MYSQL_PASSWORD', 'MYSQL_ROOT_PASSWORD',
        'HOSPITAL_APP_PASSWORD', 'PEDIATRIA_APP_PASSWORD',
        'IDENTITY_MIGRATOR_PASSWORD', 'IDENTITY_APP_PASSWORD'
    )
    $lineas = Get-Content -LiteralPath '.env.example' | ForEach-Object {
        $nombre = ($_ -split '=', 2)[0]
        if ($claves -contains $nombre) {
            "$nombre=$([guid]::NewGuid().ToString('N'))"
        } else {
            $_
        }
    }
    $lineas += "DJANGO_SECRET_KEY=$([guid]::NewGuid().ToString('N'))$([guid]::NewGuid().ToString('N'))"
    Set-Content -LiteralPath '.env' -Value $lineas -Encoding ascii
}

function Invoke-RimCompose {
    & docker compose --env-file .env @args
    if ($LASTEXITCODE -ne 0) { throw "Docker Compose terminó con código $LASTEXITCODE" }
}

$rimRepo = (Get-Location).Path
$rimRun = @('run', '--rm', '--no-deps', '-T')
$rimMaintenance = @('--profile', 'maintenance') + $rimRun
Invoke-RimCompose config --quiet
```

## 3. Iniciar con Docker

### Primera instalación con volúmenes nuevos

Desde la raíz y en la misma ventana, prepara los cuatro motores, los esquemas y los permisos. Después inicia Django y React.

```powershell
Invoke-RimCompose build backend frontend firestore identity-migrate
Invoke-RimCompose up -d --wait --wait-timeout 240 postgres mysql mongo mongo-init firestore

Invoke-RimCompose @rimMaintenance hospital-migrate bash /schema/migrate.sh all
Invoke-RimCompose @rimMaintenance pediatria-migrate bash /schema/migrate.sh all
Invoke-RimCompose @rimMaintenance hospital-migrate psql -X -v ON_ERROR_STOP=1 -f /schema/operations_upgrade.sql -f /schema/operations_runtime.sql
Invoke-RimCompose @rimMaintenance pediatria-migrate sh -ec 'export MYSQL_PWD=$MYSQL_ROOT_PASSWORD; mysql -h mysql -u root pediatrico < /schema/operations_upgrade.sql; mysql -h mysql -u root pediatrico < /schema/operations_runtime.sql'
Invoke-RimCompose @rimMaintenance identity-schema
Invoke-RimCompose @rimMaintenance identity-migrate

Invoke-RimCompose @rimRun -e 'MONGO_CLINICAL_SETUP_URI=mongodb://mongo:27017/laboratorio?replicaSet=rs0' -v "${rimRepo}/db/mongo:/schema:ro" backend sh -ec 'python -B /schema/clinical_schema.py --apply; python -B /schema/specialty_schema.py --apply; python -B /schema/operations_schema.py --apply'
Invoke-RimCompose up -d --wait --wait-timeout 240 backend frontend
Invoke-RimCompose ps
```

### Arranques siguientes con los esquemas preparados

```powershell
Invoke-RimCompose up -d --wait --wait-timeout 240 backend frontend
Invoke-RimCompose ps
```

La interfaz está en [localhost:5173](http://localhost:5173/) y la API en [localhost:8000/api/](http://localhost:8000/api/). En [salud de las bases](http://localhost:8000/api/health/databases/) deben aparecer las cuatro instituciones con **connected: true**. Abre la interfaz usando localhost para que coincida con la configuración de la API.

## 4. Cargar los datos de prueba

La carpeta [datos de prueba](datos%20de%20prueba/) contiene un script por motor y un lanzador común. Los nombres, expedientes, resultados e importes son ficticios. La carga usa los servicios de la aplicación y persiste en los cuatro motores de Docker.

```powershell
& '.\datos de prueba\cargar.ps1'
```

El lanzador prepara cuatro cuentas administradoras institucionales y guarda sus contraseñas generadas en el archivo local `.local/datos-de-prueba/accesos.json`. Dentro de `cuentas` encontrarás el usuario y la contraseña de cada institución. Conserva ese archivo para volver a ejecutar la carga. La fecha inicial de las citas queda registrada allí y los expedientes se reconocen por su identificación.

## 5. Ver el flujo

1. Abre [la aplicación](http://localhost:5173/), inicia sesión con la cuenta de la institución elegida y entra en **Pacientes**. Busca el identificador de la tabla.
2. Abre el expediente y recorre **Resumen**, **Consultas y tratamientos** y **Seguimiento institucional**. En **Agenda**, usa **Hoy** y **Próximos 7 días** para ver la jornada de la primera carga.
3. Para recorrer una escritura completa, agenda una cita para hoy con uno de los pacientes de ejemplo. Selecciona el profesional y confirma. Luego pulsa **Atender** y guarda la consulta con la cita vinculada.

| Cuenta | Expediente inicial | Qué observar |
| --- | --- | --- |
| admin.hospital | RIM-H-001 · Lucía Paredes Soto | Consulta y receta, ingreso con alta, traslado, cirugía, despacho y factura con pago parcial. El expediente RIM-H-002 tiene un ingreso abierto. |
| admin.pediatrico | RIM-P-001 · Sofía Herrera Luna | Tutor, gráfica de crecimiento, vacuna, examen con resultado y registros de seguro. |
| admin.laboratorio | RIM-L-001 · Camila Aguilar Ponce | Hemograma finalizado. Los expedientes RIM-L-002 y RIM-L-003 muestran un resultado en proceso y otro pendiente. |
| admin.odontologica | RIM-O-001 · Paula Reyes Ibarra | Odontograma con piezas tratadas y pendientes, tratamiento y pago asociado. |

## Detener o diagnosticar

```powershell
Invoke-RimCompose logs --tail 80 backend frontend
Invoke-RimCompose stop
```

El comando `stop` conserva los volúmenes. Si una conexión aparece caída, revisa el servicio correspondiente con `Invoke-RimCompose ps -a` y sus logs. En una instalación nueva, comprueba también que todos los comandos de preparación terminaron correctamente.

La [documentación técnica de la implementación](docs/implementacion/README.md) reúne los contratos, la arquitectura y la evidencia de validación.
