# B5 — API clínica y calidad central

Pablo, `feature/pablo`; base integrada B4 `ead042cf3e9042b7c7e969236ba368dd60ebb79a`
(PR #15). Fecha de ejecución: 2026-10-21, Guatemala. Los respaldos usan UTC.

**Estado: API central implementada; cierre integral B5 pendiente.** PostgreSQL
y MySQL ofrecen persistencia clínica y flujo HTTP probado. MongoAdapter y
FirestoreAdapter solo implementan salud en main y en la rama publicada de Jennifer
inspeccionada (`7bacf22`). No se modificaron sus archivos ni frontend. B5 no puede
certificarse como integración clínica de cuatro motores ni flujo real React
hasta contar con A3/A4. La publicación de este avance debe permanecer en borrador
y sin merge mientras ese criterio obligatorio esté pendiente.

## Rutas y composición

Se conserva CONTRACT-API-01@1.0.0 / CONTRACT-REPO-01@1.0.0, sin renombrar campos,
IDs ni rutas. No hay selectores HTTP de motor o institución. La sesión B2 aporta
contexto verificado → presentación valida/permisos → HistorialService → factory
→ proveedor nativo. Django ORM sigue limitado a identidad/sesiones.

| Operación | Ruta | Éxito |
|---|---|---|
| AUTH-CSRF | GET `/api/auth/csrf/` | 200 token/cookie |
| API-01 | POST `/api/auth/login/` | 200 usuario y sesión rotada |
| API-02 | GET `/api/auth/me/` | 200 usuario institucional |
| API-03/04 | GET / POST `/api/pacientes/` | 200 página / 201 paciente |
| API-05 | GET `/api/pacientes/{id}/historial/` | 200 árbol completo |
| API-06 | POST `/api/pacientes/{id}/consultas/` | 201 consulta |
| API-07 | POST `/api/consultas/{id}/diagnosticos/` | 201 ocurrencia |
| API-08 | POST `/api/diagnosticos/{id}/tratamientos/` | 201 tratamiento |
| API-09 | POST `/api/tratamientos/{id}/recetas/` | 201 renglón |
| API-10 | PATCH `/api/pacientes/{id}/estado/` | 200 paciente archivado |
| CAT-01 | GET `/api/medicamentos/` | 200 página de catálogo |
| AUTH-LOGOUT | POST `/api/auth/logout/` | 204 sin cuerpo |

Los ocho handlers clínicos están en `presentation/clinical.py`; composición sin
SQL ni lógica clínica en vistas. Se reutiliza B2 para login, cookies, sesión
absoluta de ocho horas, CSRF y logout. El índice `/api/` anuncia las rutas.
Puertos hospitalización/PED-01 permanecen disponibles en repositorios; no se
inventaron rutas HTTP de especialización fuera del contrato publicado.

Altas reciben los DTOs de maestro §5.1; PATCH exige exactamente
`{"estado":"archivado","motivo":"..."}`. IDs opacos string se conservan; no se
convierten a enteros en presentación. Se rechaza ID vacío/solo espacios antes de
instanciar el proveedor. Padres ajenos/ausentes devuelven el mismo 404 del motor.

JSON es el único formato clínico. Se rechazan campos desconocidos, tipos erróneos,
fechas inválidas/futuras, null no permitido, JSON malformado, claves duplicadas y
NaN/Infinity. Los errores de parseo no revelan el body. q/limit/offset solo se
admiten en GET de pacientes/catálogo; no se aceptan parámetros repetidos ni
selectores como `motor`/`institucion`. Búsqueda NFC/trim/lower por prefijo literal,
count antes de paginar y orden uniforme quedan a cargo de contratos/proveedor.

Autenticación y autorización suceden antes de buscar IDs, leer DTOs clínicos o
instanciar repositorios. Se aplica íntegra la matriz de maestro §5.3, incluyendo
profesional habilitado en escrituras. HEAD hereda los permisos de GET. Cambiar
perfil/profesional se revalida por petición; superusuario técnico no obtiene
privilegios clínicos implícitos. Toda respuesta clínica lleva `no-store`.

Sin sesión: 401 con WWW-Authenticate; CSRF/rol: 403. Duplicado/archivo: 409;
JSON/DTO/query: 400; formato: 415; método: 405; inesperado: 500; persistencia:
503. Siempre `{error:{code,message,fields}}`, fields objeto. Se normalizan además
Http404/NotFound. Las rutas desconocidas bajo `/api/` entregan 404 JSON seguro
incluso con DEBUG. No se publican SQL, trazas, contraseñas ni cuerpos clínicos;
los errores inesperados se registran solo por clase.

## Dependencia concreta para A3/A4

```powershell
docker compose exec -T backend python manage.py audit_clinical_providers
docker compose exec -T backend python manage.py audit_clinical_providers --require-all
```

El primer comando muestra declaraciones de puertos sin consultar datos. El
segundo devuelve **código 1** mientras falte alguno. En esta ejecución:

| Institución | Puerto + catálogo | Integración clínica |
|---|---|---|
| hospital | PostgreSQLAdapter: disponible | cadena HTTP/SQL y suite reales aprobadas |
| pediatrico | MySQLAdapter: disponible | cadena HTTP/SQL y suite reales aprobadas |
| laboratorio | MongoAdapter: faltan los nueve métodos | pendiente A3; HTTP válido → 503 |
| odontologica | FirestoreAdapter: faltan los nueve métodos | pendiente A3; HTTP válido → 503 |

En ambos adaptadores A faltan `registrar_paciente`, `listar_pacientes`,
`obtener_historial`, `registrar_consulta`, `registrar_diagnostico`,
`registrar_tratamiento`, `registrar_receta`, `archivar_paciente` y
`listar_medicamentos`. Deben implementar HistorialRepository/MedicamentoCatalogo,
aceptar `contexto=`, devolver DTOs JSON y traducir fallos al error de dominio.
La auditoría verifica firmas declaradas, no semántica/transacciones ni conectividad.

Ejemplo reproducible pendiente: usuario admin válido de laboratorio u odontología,
POST `/api/pacientes/` con
`{"identificacion":"DEMO-0001","nombres":"Paciente","apellidos":"Álvarez","fecha_nacimiento":"2000-01-01"}`.
Resultado actual: 503 SERVICE_UNAVAILABLE. Resultado requerido tras A3: 201
Paciente y lectura posterior persistida en la misma institución. No se usa un
doble de memoria ni un motor alternativo para dar 201 en producción.

Mongo ya dispone de transacciones, pero su futuro adaptador debe modificar una
versión del documento raíz dentro de la transacción para competir con archivo;
solo leer activo en un snapshot no elimina la carrera. Firestore debe leer la raíz
en su transacción y archivo debe modificarla. Ambos necesitan la suite compartida
con su propio arnés real y pruebas de ambos órdenes/rollback. El frontend actual
de main es el panel de salud/mocks; la rama publicada A incorpora trabajo UI aún
no integrado. No se mezcló una rama revertida ni se modificaron sus fuentes.

Para cerrar B5: incorporar los proveedores publicados por A, ejecutar contratos
reales y HTTP/aislamiento en cuatro destinos, probar flujo React autenticado y
actualizar el comparativo con evidencia A5. Solo entonces pasar el PR de borrador
a listo y aplicar el merge ordinario si las reglas GitHub lo permiten.

## Mongo rs0: procedimiento central conservador

Scripts propios en `ops/mongo/`, fuera de las fuentes A. `mongo` arranca con
`--replSet rs0` sobre el mismo volumen. `mongo-init` es un servicio de una ejecución
que espera conectividad, inicia únicamente si falta configuración y no altera
una topología existente incompatible. Repetirlo conserva rs0. El miembro se
anuncia como `mongo:27017` dentro de Compose; backend usa
`mongodb://mongo:27017/laboratorio?replicaSet=rs0`. Health exige PRIMARY; backend
espera además la finalización correcta de mongo-init. No representa HA.

**Para un volumen standalone existente, antes de aplicar la nueva configuración:**

```powershell
# Detener también cualquier escritor SQL/Mongo externo antes del respaldo.
docker compose stop backend
docker compose run --rm --no-deps mongo-backup
docker compose up -d --no-deps mongo
docker compose run --rm --no-deps mongo-init
docker compose up -d backend
```

Backup primero, cambio de topología después. `mongo-backup` tiene acceso por red
y al directorio privado de respaldos; no monta el volumen activo de MongoDB.
Usa mongodump con archivo gzip y SHA-256. Restaura en un mongod independiente,
loopback:27028, en `/tmp` del contenedor desechable. Compara las bases de usuario:
hash BSON por colección, cantidad, opciones/validadores e índices (incluido orden
de campos de claves compuestas). Compara también el manifiesto del origen antes
y después; sigue siendo obligatoria una ventana sin escritores para consistencia.
Si falla, abortar la transición y revisar escritores. No usa `--drop`
contra el servicio ni elimina volúmenes. admin/config/local son datos internos y
se excluyen del manifiesto de comparación; el dump conserva lo que mongodump
soporta, sin prometer clonar la metadata interna de replicación.

Respaldo local comprobado:
`.local/mongo-backups/20261022T053406Z-50de33d75f1a26e2/mongo.archive.gz`.
Laboratorio antes/después: seis colecciones, cero documentos; hashes/índices/
validadores conservados. Se repite restauración de la copia anterior contra el
estado rs0, sin sobrescribir el archivo original:

```powershell
docker compose run --rm --no-deps mongo-backup bash /ops/backup.sh verify 20261022T053406Z-50de33d75f1a26e2
```

En un arranque nuevo `docker compose up -d` ejecuta mongo-init automáticamente.
Para clientes del host, el hostname `mongo` no se anuncia como localhost: usar
operaciones de mantenimiento dentro de Compose; `directConnection=true` al
host local sirve para inspección, sin cambiar la configuración de replicación.

Reversión: detener escritores, preservar también el estado más reciente y
verificar el dump en otra instancia vacía de la misma versión antes de cambiar
la aplicación. Revertir el flag de arranque no es un procedimiento de recuperación
ni concilia escrituras nuevas. No borrar `mongodata`, `local` ni usar force
reconfig/`down -v`. Referencias oficiales:
[conversión standalone](https://www.mongodb.com/docs/manual/tutorial/convert-standalone-to-replica-set/),
[backup/restore](https://www.mongodb.com/docs/v8.0/tutorial/backup-and-restore-tools/).

## Validación y límites

```powershell
docker compose run --rm integration-tests
node --test frontend/tests/contract-fixtures.test.js
docker compose run --rm --no-deps frontend npm run build -- --outDir /tmp/rim-b5-dist
docker compose exec -T backend python manage.py check --database default
docker compose config -q
```

integration-tests hereda los destinos aislados B2/B3/B4 y añade prueba de
transacción multidocumento commit/abort en base `test_b5_<uuid>` de Mongo rs0.
Solo limpia ese nombre generado y verificado. Las pruebas HTTP usan clientes
Django con middleware/cookies/CSRF reales; las SQL dejan factory y proveedor
reales, cambiando únicamente su destino a bases/esquemas privados y roles limitados.
Se comprueba cadena clínica, lectura desde conexión nueva, archivo, duplicados,
aislamiento cruzado, rollback después de INSERT y fallos de conexión seguros.
Otros tests usan dobles explícitos para las cuatro instituciones y para ausencia
de proveedor; esos tests no certifican persistencia NoSQL.

Resultado final: **172 aprobadas, 0 fallos, 0 omitidas**, ocho pruebas cliente
aprobadas, build Vite/check/Compose correctos y cuatro conexiones saludables.
Restauración del dump anterior y verificación posterior a rs0 aprobadas, incluidos
los índices compuestos. El inicio idempotente se ejecutó tanto desde el estado
NotYetInitialized como sobre rs0 existente; se corrigieron en el script la espera
de conexión inicial y el manejo de la excepción 94 de mongosh antes de completar
la conversión. SHA completo y estado del PR se registran al publicar.

Auditoría `--require-all` pendiente/fallida por proveedores ausentes se informa
aparte de las pruebas aprobadas. No se oculta como skip ni se afirma cierre del
requisito de equivalencia en cuatro motores. No se crearon pacientes, cuentas ni
recetas en bases activas para la demostración. Comparativo y clasificación de
datos en [COMPARATIVO_MOTORES.md](COMPARATIVO_MOTORES.md).
