# AUC-12: ensayo de actualización y preparación de entrega

**Estado: preparación implementada y ensayo local; cierre del entorno compartido
pendiente.** No se accedió ni desplegó en una instalación compartida. Las copias
pobladas usadas aquí contienen datos sintéticos de los escenarios nativos.
La identidad ensayada es SQLite desechable; no sustituye la validación del
PostgreSQL de identidad de entrega, sus cuentas y sus permisos reales.

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
python docs/implementacion/verify_native.py --run --upgrade --browser --efficiency \
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
5. Verifica que el runtime SQL lea todos los recursos restaurados y que no tenga
   DELETE ni privilegios de DDL. Restaura la identidad SQLite antes de levantar
   el servidor y compara su contenido.
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
No enviar contraseñas por chat. En esta sesión no hay ese destino o copia.

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
