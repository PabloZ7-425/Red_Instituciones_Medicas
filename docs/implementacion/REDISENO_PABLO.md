# Rediseño de Pablo: seguimiento institucional

Entrega sobre `feat/ui-base`, desde la fundación integrada
`e0e6010`. Fecha: 6 de noviembre de 2026.

## Cambios

- Laboratorio: tarjetas por resultado y tabla de campo, valor, unidad y
  referencia. Conserva valores numéricos, texto y booleanos, incluido `false`
  como «No». Las unidades y referencias ausentes se indican con texto. La tabla
  permite desplazamiento horizontal y foco de teclado en espacios pequeños.
- El editor de campos variables vive ahora en
  `frontend/src/features/laboratorio/ResultFields.jsx`. Conserva las claves de
  fila, los tipos de valor, los límites y el estado controlado por el formulario.
  Distribuye los controles en dos columnas y en una columna en móvil.
- Pediatría: secciones de tutores, vacunas y crecimiento con recuentos,
  orientación breve y tarjetas con etiquetas, unidades y números tabulares.
  Conserva las advertencias de parentesco y mediciones históricas sin confirmar.
- Los estilos de ambas instituciones viven en sus propios directorios y usan
  los tokens compartidos.

## Extensiones compartidas

`SpecialtyDemoPanel.jsx` consume dos propiedades opcionales del perfil:

| Propiedad | Contrato |
| --- | --- |
| `SpecialtySection` | Componente con `{kind, action, rows, children}`. Presenta el encabezado y envuelve los hijos compartidos. |
| `ResultFields` | Editor de campos variables con `{value, onChange, disabled, errorId}`. Lo publica Laboratorio, único consumidor del tipo `resultFields`. |

El contenedor conserva la carga, los errores, los vacíos, el listado, las
condiciones de autorización y archivo, la selección del editor y el guardado.
Hospital y Odontología usan la sección predeterminada. La presentación de estas
dos instituciones permanece en sus respectivos perfiles.

## Validación realizada

| Comprobación | Resultado |
| --- | --- |
| `npm.cmd --prefix frontend test` | 65 aprobadas, 0 fallidas |
| `npm.cmd --prefix frontend run build` | Aprobada |
| Chromium DEMO con rol admin | Cadena clínica, especialidades y archivo en las cuatro instituciones |
| Chromium DEMO con rol secretaria | Tutor pediátrico; vacuna y crecimiento restringidos |
| Chromium DEMO con rol laboratorista | Resultado especializado; diagnóstico y receta restringidos |
| Responsive | Sin desbordamiento de página a 360, 768 y 1280 px en ambas instituciones, con vacío y registros |
| Tabla de laboratorio | Encabezados semánticos, valores de tres tipos, referencia ausente y foco comprobados |
| Salud API local | `connected: true` en PostgreSQL, MySQL, MongoDB y Firestore |
| Pediatría, Chromium y API local | Alta, consulta, diagnóstico, tratamiento, receta, tutor, vacuna, crecimiento y archivo aprobados |
| Pediatría, sesión nueva | Relectura de cadena y tres registros especializados; archivo persistido y acciones de escritura ocultas |
| Laboratorio, Chromium y API local | Cadena completa, resultado con tres tipos, archivo y relectura tras recargar aprobados |
| Errores en formularios especializados | 400/403/409/503 inyectados por CDP: conservan valores, anuncian error y bloquean Escape durante guardado |
| Sesión invalidada en servidor | Las lecturas devuelven 401; retorno a login y limpieza del paciente en ambas instituciones |
| Preparación DEMO | Cuatro pruebas de creación, repetición, conservación de versión y rechazo de registros incompatibles |
| Runner aislado `verify_native.py --run --browser` | 117 pruebas aprobadas, 0 fallidas, 0 omitidas; build y once recorridos Chromium aprobados |

El runner DEMO incorpora las aserciones nuevas en
`frontend/tests/browser-smoke.mjs`. Para guardar capturas, define
`UI_EVIDENCE_DIR` antes de ejecutar `npm.cmd --prefix frontend run test:browser`.
Define también `CHROMIUM_PATH`, `BROWSER_URL` y el modo DEMO del servidor según
el entorno. Las doce capturas locales de vacío y registros quedaron en
`frontend/.local/ui-pablo/evidencia/` (fuera de Git).

Las pruebas HTTP locales reutilizaron `browser-real.mjs` mediante una copia
privada en `.local/ui-pablo/`, adaptada a las cuentas de
`.local/bootstrap/access.json`, a los catálogos existentes y a identificaciones
ficticias `UI-PABLO-20261106A` hasta `UI-PABLO-20261106H`. Se usó el frontend actualizado en el puerto
18173 con proxy local hacia la API de Docker en 8000. Las credenciales no se
incorporaron al código ni a la evidencia. La prueba de persistencia abrió un
proceso Chromium y una sesión nuevos.

## Corrección del 403 de la preparación local

La causa confirmada fue la ausencia de `DEMO-PABLO-PRO` en
`clinico_profesionales_operativos`. El espejo de identidad sí existía y estaba
habilitado. `ops/bootstrap_local.py` ahora crea el profesional nativo en MongoDB
y Firestore antes de vincular las cuentas. También prepara el esquema operativo
de MongoDB. Conserva cuentas, contraseñas, versiones y desactivaciones expresas.

`ops/bootstrap_professionals.py` centraliza la creación idempotente y rechaza
registros incompatibles. `ops/repair_demo_professionals.py` permite revisar una
instalación DEMO existente; exige el perfil activo esperado y solo inserta un
registro nativo ausente. No cambia identidad ni reactiva registros existentes.

Desde PowerShell con Docker disponible:

```powershell
docker compose run --rm --no-deps -T -e PYTHONPATH=/app -v "${PWD}/ops:/ops:ro" backend python /ops/repair_demo_professionals.py --institution laboratorio
# Solo si el diagnóstico indica missing:
docker compose run --rm --no-deps -T -e PYTHONPATH=/app -v "${PWD}/ops:/ops:ro" backend python /ops/repair_demo_professionals.py --institution laboratorio --apply
python -m unittest discover -s ops -p test_bootstrap_professionals.py -v
```

La misma comprobación admite `--institution odontologica`, exclusivamente con el
emulador local. Ambas referencias nativas fueron creadas en el entorno de Pablo;
el reparador confirmó después `valid; unchanged` en las dos instituciones.

## Repetir el recorrido HTTP con cuentas locales

El runner `frontend/tests/browser-real.mjs` conserva sus valores predeterminados
para el entorno dedicado. Ahora también admite un archivo privado de cuentas,
instituciones seleccionadas, identificación nueva, capturas y comprobaciones de
errores y recarga. El frontend de prueba debe usar la API real; para los errores
se inyectan respuestas exclusivamente en el navegador mediante CDP.

```powershell
$env:CHROMIUM_PATH='C:/Program Files/Google/Chrome/Application/chrome.exe'
$env:BROWSER_URL='http://localhost:18173/'
$env:OPERATIONS_BROWSER_API='http://localhost:18173/api/'
$env:A5_REAL_HTTP='1'
$env:A5_ACCESS_FILE=(Resolve-Path '.local/bootstrap/access.json').Path
$env:A5_INSTITUTIONS='pediatrico,laboratorio'
$env:A5_PATIENT_IDENTIFICATION='UI-PABLO-NUEVO-01' # Cambiar en cada ejecución; máximo 20 caracteres.
$env:A5_RELOAD_CHECK='1'
$env:A5_ERROR_CHECKS='1'
$env:A5_EVIDENCE_DIR='.local/ui-pablo/evidencia-real'
npm.cmd --prefix frontend run test:browser:real
```

En esta ejecución el frontend de 18173 utilizó un proxy local `/api` a Django en
8000. En el runner dedicado se configura `OPERATIONS_BROWSER_API` con su API
directa. `A5_ACCESS_FILE` no se combina con la prueba de roles A5, que conserva
sus cuentas dedicadas. Los fallos HTTP esperados se cuentan individualmente;
cualquier fallo adicional hace fallar el recorrido.

## Evidencia visual

Capturas con datos ficticios, tomadas antes de archivar los pacientes:

| Institución | API real, escritorio | API real, móvil | Vacío DEMO |
| --- | --- | --- | --- |
| Laboratorio | [1280 px](evidencia-ui-pablo/laboratorio-real-1280.png) | [360 px](evidencia-ui-pablo/laboratorio-real-360.png) | [Sin resultados](evidencia-ui-pablo/laboratorio-vacio-1280.png) |
| Pediatría | [1280 px](evidencia-ui-pablo/pediatrico-real-1280.png) | [360 px](evidencia-ui-pablo/pediatrico-real-360.png) | [Sin seguimiento](evidencia-ui-pablo/pediatrico-vacio-1280.png) |

Las capturas adicionales a 768 px y los logs privados quedan fuera de Git.

## Ensayo con motores desechables

Se ejecutó el runner de la guía desde una copia de trabajo dentro de un
contenedor `pablo-validation-runner:latest`, con el socket Docker y el JAR
oficial existente. `verify_native.py` creó tres motores nuevos y un emulador
Firestore independiente. La copia partió de `e0e6010` con los cambios de esta
entrega aplicados; el reporte declara `working_tree: true`.

Resultado: 117 pruebas de operaciones y contrato NoSQL aprobadas, compilación
aprobada, cuatro recorridos operativos y siete recorridos clínicos/de roles
aprobados. El runner retiró sus propios motores, emulador y servidores al
terminar; no usó los volúmenes del entorno compartido. Los logs y el reporte
completo están en `.local/ui-pablo/isolated/native/`, excluidos de Git.

La identidad del ensayo es SQLite técnica desechable, como establece el runner
sin `--identity-postgres`; no se presenta como una nueva validación del traslado
de identidad PostgreSQL. La validación local adicional sí usó la API de Docker
y sus cuentas existentes para ambas instituciones de Pablo.
