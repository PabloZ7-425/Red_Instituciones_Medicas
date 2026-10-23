# AUC-06: facturación y pagos

> Seguimiento AUC-08: los recorridos de navegador y permisos ya fueron verificados; ver [cierre AUC-08](CIERRE_AUC_08.md). Los resultados y pendientes de este documento describen su ejecución original.


Implementada en `implementacion`. La evidencia ejecutada incluye pruebas aisladas,
API y PostgreSQL/MySQL reales; el recorrido financiero en navegador sigue pendiente.
Este documento no certifica actualización de datos existentes ni despliegue.

## Ciclo y tareas

En hospital y pediatría la factura nueva empieza en **Borrador** (`borrador` en
MySQL). Solo el borrador permite agregar conceptos. **Emitir factura** exige
conceptos y un total positivo; fija la fecha de emisión y pasa a **Pendiente**.
Desde ese momento los conceptos y totales quedan cerrados, incluso antes de
recibir el primer pago. **Parcial** refleja cobros vigentes inferiores al total;
**Pagada** requiere cubrir toda la factura. No se cambia el estado por PATCH.

En pediatría cada pago indica paciente o aseguradora. Sus saldos se calculan por
separado, sin sumar un pagador contra el límite del otro. Un cobro del seguro
exige reclamaciones aprobadas suficientes. Aprobar una reclamación no registra
dinero recibido. Cobrar solo la parte del paciente no liquida la parte del seguro.
No se puede reducir/cancelar una aprobación por debajo de lo ya cobrado al seguro
sin revertir primero los cobros correspondientes.

**Revertir pago** conserva importe, referencia y relaciones; cambia su estado a
Anulado y recalcula el estado/saldos de la factura en la misma transacción. Solo
se suman pagos Procesados. Una referencia anulada no se reutiliza. Esta operación
registra una reversión en el sistema; no ejecuta devoluciones bancarias.

**Anular factura** exige que no queden pagos sin anular ni reclamaciones activas.
Conserva conceptos y totales históricos, muestra saldo cobrable cero y bloquea
nuevos cobros, conceptos, emisión y reclamaciones. No se elimina información.

Las tareas aparecen en Caja y seguros para admin/secretaría, con un diálogo de
confirmación, control de doble envío y versión optimista. El listado y el detalle
de facturas muestran estado, cobrado y saldo de cada pagador. Los permisos se
comprueban antes de leer el cuerpo o construir el proveedor.

## API y transacciones

El manifiesto pasa a `OPERACIONES-01@2.0.0`: la emisión explícita cambia el ciclo
anterior. Los consumidores deben crear factura, agregar conceptos, emitir y
después registrar pagos/reclamaciones. Las rutas de alta y lectura se conservan.

```text
POST /api/operaciones/factura/{id}/  {"accion":"emitir|anular","version":"..."}
POST /api/operaciones/pago/{id}/     {"accion":"revertir","version":"..."}
```

`accion` contiene una sola acción literal. Una versión obsoleta o una transición
incompatible devuelve 409; requisitos de importe, aprobación o cancelación
devuelven 400. El DTO de factura añade `financial` con cobrado_paciente,
cobrado_seguro, saldo_paciente y saldo_seguro, como decimales string.

Los cobros y acciones se serializan por la factura. Para revertir se obtiene su
identificador en una transacción de lectura separada; la transacción de escritura
bloquea primero factura y después pago, antes de consultar saldos. Esto evita
establecer una instantánea MySQL anterior a la espera por el bloqueo. El fallo
posterior a la escritura revierte tanto pago como estado de factura.

## Preparación de un entorno existente

Antes de usar el backend nuevo con PostgreSQL, detener escritores, respaldar e
inventariar según el procedimiento existente y aplicar como propietario
`db/postgres/operations_upgrade.sql`. El script reemplaza atómicamente el CHECK
de factura para aceptar Borrador; se puede repetir. `init.sql` ya incluye ese
estado para instalaciones nuevas. El rol de aplicación no ejecuta DDL.

MySQL ya almacena estos estados en VARCHAR; no requiere DDL adicional por AUC-06.
Los grants operativos existentes permiten las escrituras nuevas.

Las facturas antiguas Pendiente/Parcial/Pagada se tratan como emitidas y no aceptan
conceptos nuevos. No se reescriben automáticamente estados/saldos históricos;
su conciliación y la prueba de actualización en copia poblada corresponden a
AUC-12. El código anterior no conoce Borrador: detener escritores y conciliar
esos registros antes de una reversión de versión, conservando respaldo.

## Evidencia ejecutada

- Backend en Docker: **39 aprobadas, 0 fallidas, 0 omitidas**, incluyendo finanzas,
  AUC-05, definiciones/permisos y las regresiones AUC-01..04. Ocho escenarios
  ejecutan los proveedores nativos contra PostgreSQL 16/MySQL 8.4 nuevos con roles
  limitados. Incluyen cobros parciales/total, seguro, rollback y reversiones simultáneas.
- La ejecución local previa tuvo 23 aprobadas y 2 omitidas; las dos nativas se
  ejecutaron después en Docker y están incluidas en las 39. No se suman ambas cifras.
- Cliente Node: **60 aprobadas, 0 fallidas**.
- Build Vite de producción aprobado; `git diff --check` sin errores.

La prueba financiera aislada ejecuta SQL real del repositorio en SQLite temporal,
adaptando placeholders y retirando FOR UPDATE. Comprueba importes y rollback,
pero no certifica bloqueos ni concurrencia de PostgreSQL/MySQL. La API usa
identidad SQLite desechable y el repositorio aislado; no datos compartidos.

```powershell
python backend/manage.py test apps.operaciones.test_finance apps.operaciones.test_chronology apps.operaciones.tests.PermissionTests --settings=config.test_settings --verbosity 1
python docs/implementacion/verify_finance.py --docker "$env:LOCALAPPDATA/Programs/DockerDesktop/resources/bin/docker.exe"
node --test frontend/tests/*.test.js
npm.cmd --prefix frontend run build
```

El ejecutor `verify_finance.py` reutiliza únicamente las dependencias de la imagen
backend local y monta el código/esquemas como solo lectura. Crea una red aislada,
dos contenedores y cuatro bases nuevas (hospital/pediatría y sus destinos AUC), sin
puertos publicados ni volúmenes compartidos. Repite dos veces el upgrade PostgreSQL
en esas bases de ensayo. Al terminar verifica las etiquetas y retira exclusivamente
sus contenedores, volúmenes temporales y red. No lee `.env` ni credenciales del proyecto.

Fuente de aplicación verificada: `1356565`; el ejecutor era una adición local aún
sin commit. Informe y logs privados: `.local/validation/auc06-c9a505f9d87a/`.
No se ejecutó el recorrido financiero en navegador. Las seis filas financieras
siguen P por esa verificación pendiente (AUC-08), sin presentar conteos históricos
como evidencia de esta versión. La actualización de copia poblada sigue en AUC-12.

Siguiente tarea solicitada: AUC-07. AUC-08 debe completar la matriz de cobertura
por rol e interfaz; AUC-09 conserva los ajustes de navegación pendientes.
