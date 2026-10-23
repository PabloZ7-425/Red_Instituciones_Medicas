# AUC-10: revocación clínica del profesional

Rama `implementacion`, sobre AUC-01..09 (`7be3eb1`). La desactivación del
profesional se comprueba en el motor clínico al guardar; no se confía únicamente
en el espejo de identidad ni se necesita cerrar y volver a abrir la sesión.

## Regla de acceso

Se deben cumplir **ambas** condiciones: el vínculo B2 está habilitado y la
referencia nativa existe y está habilitada en la institución correspondiente.
Hospital consulta `medico.habilitado`, pediatría `medico.estado='activo'`, y los dos
motores documentales exigen `profesionales_operativos.activo` y `habilitado`.
Una referencia ausente o desactivada rechaza la escritura con 403.

El usuario conserva su sesión y los permisos de lectura/administración que le
correspondan a su rol. Desactivar un profesional no desactiva automáticamente la
cuenta, no elimina registros y no convierte a otro usuario en su sustituto. Para
suspender también el inicio de sesión o todo acceso se desactiva la cuenta/perfil.
Reactivar el catálogo no sobrepasa una revocación vigente en B2.

## Implementación

- MongoDB y Firestore comprueban la referencia nativa dentro de la transacción de
  consulta, diagnóstico, tratamiento, receta, resultado o procedimiento.
- Se actualiza la versión del profesional después de todas las lecturas y antes
  de guardar: compite con una modificación del mismo catálogo y respeta la regla
  de Firestore de leer antes de escribir.
- Las escrituras operativas de atención, hospitalización y farmacia por
  admin/médico/laboratorista pasan por la misma comprobación nativa. Los permisos
  de enfermería y los administrativos conservan sus contratos de rol.
- Los proveedores SQL conservan su comprobación de profesional nativo; operaciones
  también la utiliza. No se introduce una sincronización distribuida frágil entre
  Django y los cuatro motores.

`test_professional_revocation.py` usa cuatro escenarios nativos, uno por institución:
escritura permitida, desactivación mediante API administrativa, rechazo desde la
misma sesión y desde un nuevo login, rechazo con un contexto ya construido,
reactivación y revocación adicional desde B2. Los motores documentales prueban
los dos indicadores. Las sesiones son HTTP Django reales con identidad aislada;
las consultas y cambios de catálogo se persisten en los motores nativos.

## Habilitación

Inventariar los vínculos existentes antes de desplegar. Una referencia B2 sin
profesional nativo habilitado ahora queda bloqueada deliberadamente; el
administrador debe registrar/vincular el profesional correcto. No se fabrica una
referencia ni se habilita un profesional por inferencia del nombre de usuario.

La evidencia integrada, conteos y fuente se conservan en
[CIERRE_AUC_10_12_VERIFICACION.json](CIERRE_AUC_10_12_VERIFICACION.json).
