# AUC-12: ensayo de actualización y preparación de entrega

**Estado: preparación implementada y ensayo local; cierre del entorno compartido
pendiente.** No se accedió ni desplegó en una instalación compartida. Las copias
pobladas usadas aquí contienen datos sintéticos de los escenarios nativos.
El primer ensayo usó identidad SQLite. El seguimiento ya verifica identidad
PostgreSQL 16 con roles reales en una copia sintética; todavía falta la
validación sobre los datos, cuentas y configuración de tu Docker Desktop.

## Herramientas disponibles

`db/operations_inventory.py --institution hospital|pediatrico` hace un preflight
**de solo lectura** usando la cuenta de mantenimiento seleccionada por variables
de entorno. No carga `.env` ni imprime credenciales. Verifica versión B3/B4,
columnas operativas declaradas y compatibilidad de los indicadores existentes;
rechaza una versión, columna clínica o indicador incompatible antes de recomendar
un upgrade aditivo.

`db/mysql/operations_upgrade.sql` ahora consulta `information_schema` y aplica
cada ALTER únicamente si falta la columna. Puede repetirse o reanudarse tras una
interrupción sin elegir manualmente qué líneas ejecutar. No sobrescribe valores
existentes. El DDL de MySQL tiene commits implícitos: la recuperación exige
respaldo restaurable; no se presenta como una transacción de todos los ALTER.
El upgrade PostgreSQL y los grants explícitos siguen siendo repetibles.

Reproducción del ensayo completo con herramientas y dependencias disponibles:

```bash
python docs/implementacion/verify_native.py --run --upgrade --browser --identity-postgres --efficiency \
  --work /ruta/nueva/fuera/del/repositorio --jar /ruta/firestore.jar
```

El ejecutor acepta solo un directorio nuevo fuera del repositorio y puertos
locales libres. Crea sus contenedores sin volúmenes clínicos compartidos y los
elimina al terminar; guarda respaldos privados en ese directorio. Firestore exige
el emulador local propiedad del ejecutor, sin autenticación implícita de producción.

## Qué comprueba el ensayo

1. Genera datos relacionados mediante pruebas nativas. Crea copias SQL pobladas
   anteriores a los flags operativos, obtiene dumps y las restaura con `psql` y
   MySQL. No vuelve a ejecutar `init.sql` sobre datos existentes.
2. Compara huellas de todas las filas clínicas antes/después, verifica las
   versiones y ejecuta upgrades/grants repetidos. Un indicador desactivado
   expresamente permanece desactivado al repetir el upgrade.
3. Respalda/restaura Mongo con tipos BSON, opciones de colecciones e índices;
   repite el aprovisionamiento operativo y compara los documentos.
4. Respalda/restaura Firestore mediante valores protobuf nativos, conservando
   tipos, documentos y referencias. Incluye controles sintéticos de legado v1
   que no se transforman ni pasan a ser registros clínicos v2.
5. Verifica que el runtime clínico SQL lea todos los recursos restaurados y no
   tenga DELETE ni DDL. Con `--identity-postgres`, restaura identidad PostgreSQL
   antes de levantar el servidor, conserva cuentas/perfiles/profesionales y una
   sesión previa, verifica propietarios/grants y rechaza DDL con `identidad_app`.
   Sin esa opción se conserva la compatibilidad con el ensayo SQLite anterior.
6. Ejecuta sesiones HTTP por institución/rol y recorridos Chromium contra las
   **copias restauradas**, incluidos los seis recorridos de eficiencia. No suma
   estos ensayos a una supuesta ejecución sobre el entorno de entrega.

Evidencia resumida: [verificación](CIERRE_AUC_10_12_VERIFICACION.json) y
[restauración](AUC_12_RESTAURACION.json). Los dumps, contraseñas efímeras y archivos
de identidad no se versionan.

## Lo que falta para cerrar AUC-12 en entrega

El responsable del entorno debe proporcionar o habilitar una **copia autorizada
y aislada de su instalación poblada**, junto con su inventario de motores,
versiones y cuenta de mantenimiento por el canal de credenciales del entorno.
Confirmaste que la entrega está en tu computadora con Docker. Ese Docker Desktop
no está conectado con este entorno. El siguiente paso es el [inventario de solo
lectura](../../ops/auc12/README.md), que se ejecuta allí sin actualizar la aplicación
ni enviar credenciales o registros clínicos. Ya se recibió el primer reporte: hospital, pediatría e identidad no pudieron
consultarse; Mongo está en replica set con colecciones legadas y sin registros
clínicos v2, y Firestore está vacío. Las tres huellas de código coinciden con la
versión revisada. El inventario v2 permitirá distinguir causas SQL y conservar
las migraciones pendientes aun cuando falten tablas de identidad. Estos hallazgos
no prueban todavía si faltan cuentas runtime, permisos, credenciales o esquema.

Sobre esa copia se deberá:

1. Pausar escritores e inventariar versión, esquema, permisos, vínculos B2 y
   profesionales nativos; resolver incompatibilidades detectadas por el preflight.
2. Obtener respaldos de los cuatro motores y de la identidad de entrega; demostrar
   su restauración en destinos nuevos antes de aplicar upgrades.
3. Aplicar upgrades y grants con mantenimiento, verificar su repetición y comparar
   datos. Crear/vincular profesionales operativos que falten según AUC-10.
4. Revisar movimientos de cama abiertos de ingresos ya cerrados antes de AUC-02.
   Este ensayo no modifica retrospectivamente esos datos históricos.
5. Verificar cookies/sesión/CSRF, acceso y denegaciones de cada rol y los recorridos
   acordados con la configuración real. Conservar SHA, versiones y evidencia.
6. Acordar la ventana de habilitación y recuperación. Un rollback de código no
   elimina pagos ni registros nuevos: conservar datos y decidir la restauración
   con el responsable antes de habilitar escritores.

Solo después de esa evidencia corresponde marcar AUC-12 como cerrado y valorar
la integración/despliegue. Este documento no cambia `main`, la rama de Pablo ni
sus PR, ni autoriza borrar o reemplazar bases compartidas.

## Seguimiento: identidad PostgreSQL y fallo corregido

Se restauraron **21 usuarios y una sesión existente**. El hash del contenido de
identidad coincidió antes/después; la sesión anterior al respaldo obtuvo HTTP 200
sin volver a iniciar sesión. Se usó el bootstrap de roles de `db/identity/01-roles.sh`:
`identidad_migrator` conserva propiedad/capacidad de migración e `identidad_app`
puede operar sesiones/cuentas, pero rechaza CREATE y ALTER reales y no tiene
atributos de superusuario, creación de roles ni bases. La clave de firma se
conserva en el ensayo; también deberá conservarse en una restauración de entrega.

Este ensayo detectó un defecto que SQLite ocultaba: el PATCH de cuentas aplicaba
FOR UPDATE también al profesional opcional de un LEFT JOIN, y PostgreSQL devolvía
NotSupportedError/503. Se corrigió con bloqueo únicamente del perfil institucional.
Las cuatro instituciones ahora pasan creación, vínculo, desactivación y reactivación
de cuentas por HTTP contra PostgreSQL restaurado, además del vínculo en Chromium.

Resultado: 117 pruebas backend, 17 escenarios HTTP por institución/rol y 11
recorridos Chromium, más las 12 ejecuciones controladas de eficiencia, aprobados.
Las 117 conservan la identidad SQLite de su suite original; los 17 escenarios HTTP
y todos los recorridos Chromium del seguimiento sí usan identidad PostgreSQL.
No se suman estos resultados a ejecuciones anteriores como pruebas distintas.

[Evidencia del seguimiento](AUC_12_IDENTIDAD_POSTGRES_VERIFICACION.json).
El núcleo del inventario Desktop también pasó contra los cuatro motores e
identidad PostgreSQL aislados. Su envoltorio PowerShell aún necesita ejecutarse
en tu equipo; no se declara validado Windows ni cerrada la entrega real.


## Comprobación del diagnóstico ampliado

Se aprobaron seis pruebas aisladas de clasificación/redacción de errores, sin
publicar mensajes sensibles. Un ensayo adicional contra un PostgreSQL 16 vacío
con rol de aplicación limitado confirmó que el inventario conserva la lista de
migraciones pendientes, informa SQLSTATE 42P01 para tablas ausentes y no crea
ninguna tabla. Son pruebas del instrumento de diagnóstico, no una certificación
ni una migración de la computadora de entrega.
