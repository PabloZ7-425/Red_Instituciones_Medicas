# AUC-09: continuidad de tareas y navegación de cuentas

Implementada en `implementacion`. Completa el bloque solicitado AUC-05 a AUC-09.

## Comportamiento

Continuar abre el formulario de la siguiente tarea con el padre recién guardado.
Las referencias se transfieren por el recurso al que apuntan, conservando los
identificadores públicos: factura → concepto → pago mantiene la misma factura;
examen → resultado conserva el examen. También se conservan referencias previas
necesarias en las cadenas de catálogos, hospitalización y farmacia. No se copian
importes calculados ni columnas por coincidencia de nombre. Solo se ofrece una
continuación cuando el manifiesto permite crear la tarea siguiente.

Los formularios operativos conservan su borrador al cancelar o pulsar Escape.
Reabrir el registro permite retomarlo; Descartar cambios lo elimina explícitamente.
Si Continuar reemplazaría un borrador de la tarea siguiente, se pide elegir entre
conservarlo o descartarlo. Un borrador de edición conserva la versión original,
para que reabrirlo no evite la protección contra escrituras concurrentes.

El espacio de operaciones conserva tarea, búsqueda y página al ir al expediente.
El paciente sigue seleccionado. Las tareas clínicas abren la consulta o el editor
institucional correspondiente; cuando necesitan una consulta, diagnóstico o
tratamiento, se indica qué padre debe escoger el usuario. Si todavía no hay
paciente, la tarea espera su selección. Una sesión nueva comienza en operaciones.

Usuarios y permisos utiliza un único editor modal para alta o vínculo. Se conserva
el borrador al cancelar y ante un rechazo del servidor; la contraseña se elimina
al cancelar, con aviso explícito. Los profesionales se buscan y paginan, en lugar
de descargar todo el catálogo antes de abrir el formulario.

## API de cuentas

`GET /api/operaciones/cuentas/?q=demo&limit=20&offset=200` devuelve `count`, `limit`,
`offset`, `results` y `roles`. La búsqueda es por inicio del nombre de usuario,
sin interpretar comodines. Se cuenta antes de paginar y se ordena por usuario e
identificador. Se elimina el corte fijo de 200. La interfaz reinicia la página al
buscar y corrige una página que quede fuera del total después de una actualización.

Se mantienen autorización administrativa, aislamiento institucional y validación
de sesión. Parámetros desconocidos, repetidos o fuera de rango se rechazan; las
escrituras siguen rechazando parámetros de consulta. No hay migraciones de datos.

## Validación reproducible

```powershell
$env:VITE_API_URL='/api'
npm.cmd --prefix frontend run build
node --test frontend/tests/*.test.js
python docs/implementacion/verify_finance.py --guided --docker "$env:LOCALAPPDATA/Programs/DockerDesktop/resources/bin/docker.exe"
```

`--guided` incluye las regresiones AUC-06/07/08 y añade AUC-09. Reutiliza el
ejecutor aislado y sus nombres temporales `auc08-*`: PostgreSQL, MySQL, MongoDB,
Firestore e identidad SQLite nuevos, sin puertos publicados ni volúmenes del
entorno compartido. La semilla crea 225 cuentas ficticias adicionales para
comprobar navegación real más allá de 200. Las mutaciones verificadas se realizan
desde la interfaz. Los controles del navegador deben estar visibles y habilitados.

`test_guided.py` comprueba paginación completa de 225 cuentas, orden, búsqueda,
conteo, límites, aislamiento y rechazos de acceso/parámetros. `workflow.test.js`
comprueba referencias entre pasos, rutas clínicas y transporte de paginación.
`browser-guided.mjs` añade circuitos con padres nuevos, cancelación/recuperación,
selección de paciente y padre clínico, editores institucionales, conflicto de
cuenta y navegación de usuarios a los recorridos anteriores.

## Resultado final

- **64 pruebas backend aprobadas**, sin omisiones, con motores reales temporales.
- **65 pruebas cliente aprobadas** y compilación Vite de producción correcta.
- **86 escenarios de navegador aprobados**: 72 regresiones de AUC-08 y 14 casos
  dirigidos a AUC-09. Se registraron 219 escrituras HTTP: 210 aceptadas y nueve
  rechazos esperados. Cero errores JavaScript y 17 capturas PNG.

La ejecución completa terminó con código cero y retiró sus contenedores y red.
Evidencia local: `.local/validation/auc08-5c178922fc7f/`, con `tests.log`,
`browser.log`, `report.json`, `browser-report.json` y `screenshots/`.
El [resumen versionado](CIERRE_AUC_09_VERIFICACION.json) conserva los conteos y rutas.
Los intentos anteriores no se suman como nuevas pruebas. Se inspeccionó visualmente
la captura final de cuentas para comprobar búsqueda, resultado y paginación
visibles. Esa revisión permitió corregir la vista inicial al cambiar de sesión.

## Alcance y límites

Los borradores se conservan en memoria de la sesión de interfaz, sin almacenarse
en el navegador. Recargar la aplicación o cerrar sesión los elimina. La retención
implementada corresponde a formularios operativos y de cuentas; no sustituye
los contratos ni añade autoguardado a los editores clínicos previos.

La tabla física de cobertura permanece en 76 B, 2 P y 17 T; la fila adicional de
usuarios Django pasa a base verificada. No es una certificación de aceptación de
usuarios ni despliegue. AUC-10, AUC-11 y AUC-12 pertenecen a otro bloque y siguen
abiertas: coherencia de desactivación profesional, medición de eficiencia y
habilitación sobre copia poblada/entorno compartido.
