# Investigación SQL C0 antes de implementar C2

Base: main `f671245a29a5a8f34167665efb74ce17c9907e8b`, tras integrar PR #5
aprobado por Jennifer. Responsabilidad B / Pablo. F0 sigue abierto: la aprobación
registrada cubre la corrección de salud, no ratifica aún el PR #6 completo.

Se prepararon dos experimentos reproducibles del diseño propuesto en
[RESOLUCIONES.md](RESOLUCIONES.md), que permanece en la rama/PR #6. Este PR de
pruebas parte directamente de main y no modifica ese documento ni depende de
su integración. Los scripts verifican posibilidades del esquema, no implementan
CONTRACT-REPO-01 ni constituyen migraciones listas para datos existentes.

## Resultados ejecutados

Fecha local: 2026-10-20. Motores reales: PostgreSQL **16.15** y MySQL **8.4.11**.
Se cargó una copia completa del init.sql de cada motor en una instancia nueva,
sin red, puertos publicados ni volúmenes del proyecto. Los cambios experimentales
solo se ejecutaron en esas instancias temporales. No se usaron hospital/pediatrico.

| Motor | Caso | Resultado |
|---|---|---|
| PostgreSQL | NOT NULL con fecha histórica desconocida | Rechazado, sin rellenar fechas ficticias |
| PostgreSQL | Fecha clínica distinta de cita | Valor explícito conservado |
| PostgreSQL | Consulta sin fecha tras consolidación | Rechazada por NOT NULL |
| PostgreSQL | Identificación duplicada | Rechazada por UNIQUE |
| PostgreSQL | Consulta con paciente inexistente | Rechazada por FK |
| PostgreSQL | Falla de diagnóstico tras insertar consulta | Escritura parcial revertida en subtransacción |
| MySQL | Dos consultas con cita NULL | Aceptadas |
| MySQL | Dos consultas con la misma cita | Segunda rechazada por UNIQUE |
| MySQL | Cita inexistente | Rechazada por FK |
| MySQL | Tratamiento con diagnóstico de otra consulta | Rechazado por FK compuesta |
| MySQL | Receta con tratamiento de otra consulta | Rechazada por FK compuesta |
| MySQL | Error en detalle de receta | ROLLBACK explícito a savepoint elimina cabecera parcial |
| MySQL | Mismo código diagnóstico en dos consultas | Ocurrencias distintas; tratamiento no puede usar la ocurrencia de la otra consulta |

Ambos scripts finalizaron con código 0: seis resultados OK PostgreSQL y siete
MySQL, trece casos en total. La repetición MySQL incorporó la precisión solicitada
por Jennifer en #7: id externo diagnóstico = consulta_diagnostico.id, no el id
reutilizable del catálogo. Se usa consulta_diagnostico_id en el vínculo experimental
de tratamiento. Un fallo
de sintaxis o una aserción incumplida termina el cliente con error: no usar --force
en mysql ni quitar ON_ERROR_STOP en psql. En el primer intento, PowerShell pasó
mal un argumento de host a mysql; se corrigió la invocación antes de cargar el
esquema y ejecutar los seis casos satisfactoriamente.

Baseline del proyecto después de estos experimentos: Compose config válido,
Django check sin incidencias, **12 pruebas Django OK**, cuatro motores conectados.
`git diff --check` sin errores. No se repitió build React porque solo se agregan
scripts SQL experimentales y este documento; no se modifican fuentes compartidas
ni frontend. Los resultados del build anterior siguen como evidencia histórica.

## Reproducción en PowerShell

Ejecutar desde la raíz. Si Docker está en PATH, usar `docker`; esta máquina usó
el ejecutable siguiente. Se requieren las imágenes locales postgres:16 y mysql:8.4.
No reutilizar contenedores del proyecto ni ejecutar los scripts contra sus bases.
Cada comando debe terminar con salida 0 antes de continuar; si docker run falla
por nombre existente, detenerse y revisar el contenedor, sin borrarlo a ciegas.

```powershell
$dockerPrueba = "$env:LOCALAPPDATA\Programs\DockerDesktop\resources\bin\docker.exe"
& $dockerPrueba run --pull never --rm -d --network none --name demo-pablo-pg-c0 --label tarea=pablo-diseno-sql -e POSTGRES_HOST_AUTH_METHOD=trust -e POSTGRES_DB=demo_diseno postgres:16
& $dockerPrueba run --pull never --rm -d --network none --name demo-pablo-mysql-c0 --label tarea=pablo-diseno-sql -e MYSQL_ALLOW_EMPTY_PASSWORD=yes -e MYSQL_DATABASE=demo_diseno mysql:8.4

& $dockerPrueba cp db/postgres/init.sql demo-pablo-pg-c0:/tmp/init.sql
& $dockerPrueba cp db/postgres/verificar_diseno.sql demo-pablo-pg-c0:/tmp/verificar.sql
& $dockerPrueba cp db/mysql/init.sql demo-pablo-mysql-c0:/tmp/init.sql
& $dockerPrueba cp db/mysql/verificar_diseno.sql demo-pablo-mysql-c0:/tmp/verificar.sql

# Esperar a que estos comandos de disponibilidad terminen con salida 0.
& $dockerPrueba exec demo-pablo-pg-c0 pg_isready -U postgres -d demo_diseno
& $dockerPrueba exec demo-pablo-mysql-c0 mysql --protocol=TCP '--host=127.0.0.1' --user=root --database=demo_diseno --execute 'SELECT 1'

& $dockerPrueba exec demo-pablo-pg-c0 psql -v ON_ERROR_STOP=1 -U postgres -d demo_diseno -f /tmp/init.sql
& $dockerPrueba exec demo-pablo-pg-c0 psql -v ON_ERROR_STOP=1 -U postgres -d demo_diseno -f /tmp/verificar.sql
& $dockerPrueba exec demo-pablo-mysql-c0 sh -c 'exec mysql -uroot demo_diseno < /tmp/init.sql'
& $dockerPrueba exec demo-pablo-mysql-c0 sh -c 'exec mysql -uroot demo_diseno < /tmp/verificar.sql'
```

El acceso sin contraseña solo existe en estos motores temporales con `--network
none`, sin puertos publicados. No es configuración propuesta para la aplicación.
Las imágenes pueden cambiar de parche: registrar versiones en cada repetición.
MySQL aplica el DDL experimental con commits implícitos; para repetir desde cero
se requiere una instancia nueva. La transacción PostgreSQL finaliza con ROLLBACK.

Limpieza solo de los dos contenedores creados en esta ejecución. Verificar nombre,
etiqueta y ausencia de red/puertos antes de retirar cada uno:

```powershell
& $dockerPrueba inspect demo-pablo-pg-c0 demo-pablo-mysql-c0 --format '{{.Name}} | {{.Config.Labels.tarea}} | {{.HostConfig.NetworkMode}} | {{json .HostConfig.PortBindings}}'
# Esperado: nombres demo-pablo-*, etiqueta pablo-diseno-sql, network none, sin puertos.
& $dockerPrueba rm -f demo-pablo-pg-c0 demo-pablo-mysql-c0
```

No usar down -v, volume prune ni borrar volúmenes del proyecto.

## Límites y siguiente paso

No se probaron concurrencia con archivo, adaptadores, endpoints, autorización,
conciliación de datos históricos MySQL ni restauración de backups. Un SQL de
savepoint no prueba que el futuro adaptador gestione correctamente sus errores.
Antes de C2: ratificar contratos y decisiones pendientes de F0. Después preparar
migraciones incrementales con precondiciones, conciliación trazable, backup y
reversión ensayada; actualizar init.sql en ese PR de implementación revisado.
