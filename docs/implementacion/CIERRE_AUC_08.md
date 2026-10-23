# AUC-08: cobertura operativa, permisos y recorridos de navegador

La ampliación incorpora una matriz reproducible de permisos y recorridos con
React, Django y los cuatro motores reales, ejecutados sobre datos DEMO nuevos.
No representa una actualización ni aceptación del entorno compartido.

## Cobertura de permisos

La [matriz versionada](../../backend/apps/operaciones/permission_matrix.csv)
declara lectura, creación, edición y lookup para los 75 recursos operativos.
`test_coverage.py` recorre las 17 combinaciones válidas de institución/rol y
comprueba **1,236 combinaciones recurso/rol/operación**. El CSV se mantiene como
expectativa fija; la prueba falla si las rutas dejan de respetarlo.

Se comprueban aceptación y rechazo antes de construir el proveedor, incluso con
JSON inválido en escrituras prohibidas, además de tareas financieras, falta de
vínculo profesional, logout y administración de cuentas por institución.
Las pruebas de esta matriz usan identidad SQLite y sustituyen el proveedor:
certifican el control HTTP de acceso, sin fingir escrituras reales de cada
combinación. Los escenarios nativos y de navegador verifican la persistencia.

## Recorridos de navegador

`browser-coverage.mjs` realiza las acciones por la interfaz y contrasta sus
resultados con lecturas posteriores de la API real. La preparación solo crea
padres y datos clínicos sintéticos; las operaciones verificadas se guardan desde
los formularios. No se sustituyen servicios HTTP del navegador por mocks.

- Los **24 catálogos**: alta, edición y desactivación, conservando el registro.
- Agenda en las cuatro instituciones: guardar, reprogramar, atender con una
  consulta vinculada y cancelar otra cita. La comprobación incluye Mongo/Firestore.
- Caja hospitalaria y pediátrica: conceptos, emisión, pagos parciales/total,
  separación de paciente/seguro, recuperación del seguro, reversión y anulación.
  Se prueban rechazos de conceptos después de emitir y de anulación con cobros.
- Póliza: alta activa, edición y rechazo de fechas incompatibles.
- Cirugía: requisito de equipo, realización y cancelación. Pediatría: resultados
  y exámenes completados/cancelados; aprobación, rechazo y anulación de decisiones
  de seguro, con sus dependencias.
- Laboratorio y odontología: completar/cancelar el registro existente y bloquear
  edición de registros terminales.
- Cuentas en las cuatro instituciones: alta, vínculo profesional, desactivación
  y reactivación. Menús y tareas visibles de las 17 combinaciones institución/rol.
- Escrituras con sesiones reales de secretaría (agenda y caja), médico (atención),
  enfermería (signos) y laboratorista (resultado), según sus permisos.

Los formularios operativos se envían dos veces consecutivas para comprobar que
una interacción repetida produce una sola escritura HTTP. Las respuestas de los
casos negativos se comprueban como 400/409, sin contarlas como operaciones exitosas.
El ejecutor registra capturas PNG, escenarios, solicitudes y errores JavaScript.

## Correcciones encontradas por estas pruebas

1. MySQL devuelve TIME como `timedelta`. La serialización ahora produce
   `06:00:00`, en lugar de `6:00:00`, para que una cita se pueda editar/cancelar
   sin que el control HTML de hora quede inválido. La regresión incluye medianoche
   y fracciones de segundo; no cambia fechas civiles ni valores almacenados.
2. Un campo con `choices: []` se muestra como entrada libre, coherente con su
   validación, en lugar de un selector sin opciones. Se verifica creando una
   póliza activa por interfaz y utilizándola para autorizar/reclamar.
3. La selección de referencias ignora eventos mientras las opciones están
   recargando. La automatización espera que el selector esté habilitado y que
   exista la opción; así no fuerza cambios en controles deshabilitados.

## Reproducción

Requiere las imágenes locales de backend, Firestore y `pablo-validation-runner`,
PostgreSQL 16/MySQL 8.4/MongoDB 7, y el JAR local del emulador. El CLI Docker puede
indicarse por ruta absoluta si no está en PATH.

```powershell
$env:VITE_API_URL='/api'
npm.cmd --prefix frontend run build
python docs/implementacion/verify_finance.py --browser --docker "$env:LOCALAPPDATA/Programs/DockerDesktop/resources/bin/docker.exe"
node --test frontend/tests/*.test.js
```

`--coverage` ejecuta backend/matriz de permisos con motores temporales;
`--browser` añade navegador. `--browser-only` crea igualmente motores e identidad
nuevos, pero declara explícitamente que no repitió la suite nativa. Ese modo no
se cuenta como una nueva aprobación de pruebas backend.

El ejecutor monta código y esquemas como solo lectura, crea una red sin puertos
publicados y usa bases, roles y SQLite de identidad desechables. El navegador
solo conecta al backend de esa red a través de un proxy local; no lee `.env` ni
usa los volúmenes del proyecto. La retirada verifica etiquetas e identificadores
de los recursos creados por la ejecución.

## Límites y tareas siguientes

La matriz acredita los permisos declarados y las funciones indicadas por cada
fila, sin convertir un alta aislada en CRUD universal ni afirmar que exista DELETE.
Las capturas no son mediciones de productividad ni aceptación de usuarios.

Siguen abiertos los ajustes de flujo/padres/editor único y paginación de usuarios
de **AUC-09**, el efecto de la desactivación profesional sobre identidad de
**AUC-10**, la medición de eficiencia de **AUC-11** y la actualización en copia
poblada/entorno compartido de **AUC-12**. Los roles del navegador usan perfiles
válidos y vínculos habilitados; no se certifica aquí el pendiente AUC-10.

## Verificación final

- Backend: **60 pruebas aprobadas**, sin omisiones, con PostgreSQL, MySQL, Mongo y Firestore temporales. Registro local: `.local/validation/auc08-4a7b1537c5c9/tests.log`.
- Cliente: **62 pruebas aprobadas**; compilación de producción Vite correcta con `/api`.
- Navegador: **72 escenarios aprobados**, 206 escrituras HTTP (198 aceptadas y 8 rechazos esperados), 14 capturas y ningún error JavaScript. Ejecución final y retirada correctas, código cero: `.local/validation/auc08-c1865bf0d9a6/`.

La ejecución final del navegador utilizó `--browser-only`; las 60 pruebas backend se acreditan con el registro nativo anterior, sin contabilizarlas otra vez. Se corrigió también el cierre del ejecutor de navegador para liberar conexiones del proxy después de terminar. Los intentos anteriores no se suman a los resultados.

La matriz queda con **76 B, 2 P y 17 T** sobre 95 filas físicas. Las dos P conservan AUC-10; las restricciones transversales AUC-09/11/12 permanecen descritas. Los artefactos locales son reproducibles y no se versionan; el [resumen de verificación](CIERRE_AUC_08_VERIFICACION.json) conserva sus rutas y conteos.
