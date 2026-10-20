# GUIA_PABLO_AGENTES.md — Célula B: Pablo + agentes IA

> **Documento operativo autocontenido** — versión 1.0 (2026-10-20).
> **Responsable humano:** Pablo. **Célula:** B.
> **Ámbitos exclusivos:** Django/DRF, dominio, casos de uso, autenticación y autorización, PostgreSQL, MySQL, adaptadores SQL y endpoints.
> **Contraparte:** Jennifer + agentes IA = Célula A: React, MongoDB, Firestore y sus adaptadores.
> **Lectura obligatoria previa:** [`PLAN_MAESTRO.md`](./PLAN_MAESTRO.md), [`GUIA_JENNIFER_AGENTES.md`](./GUIA_JENNIFER_AGENTES.md) (para límites).
> **Punto auditado:** `main` en `434968295c77b1ba5b3fa96f9f11d367c5a7c835` al 2026-10-20. Este SHA cambiará después de integrar PR-00.
> **Estado:** especificación operativa; **no significa que los PRs o endpoints ya existan**.

## 0. Contexto que todo agente B debe conocer

Se desarrolla un trabajo de **Bases de Datos II**, no una plataforma clínica comercial. Cuatro instituciones, cuatro motores sin repetición: Hospital→PostgreSQL (**B**); Pediatría→MySQL (**B**); Laboratorio→MongoDB (**A**); Odontología→Firestore (**A**). Los objetivos obligatorios son: cliente-servidor funcional; arquitectura hexagonal como medio; historial con consultas/diagnósticos/tratamientos/recetas; alta y archivo de pacientes; usuario autenticado enrutado a su institución; modelos y seguridad comparados. La UI ha de mantenerse homogénea. No inventar alcance clínico, pagos reales, despliegue ni alta disponibilidad innecesaria.

**Código ya existente, NO rehacer sin motivo:** `backend/config/settings.py`, `backend/apps/historiales/domain/{entities,institutions,ports}.py`, `application/database_health.py`, `infrastructure/factory.py`, cuatro adaptadores de conectividad, `presentation/{urls,views}.py`, `backend/apps/historiales/tests.py`, `db/postgres/init.sql`, `db/mysql/init.sql`, `docker-compose.yml`. Actualmente los adaptadores solo implementan `health_check()` y los endpoints operativos solo son de salud. B es dueño de los contratos, **pero no de las clases adaptadoras NoSQL**.

### Estado actual y advertencias verificadas

- Django 5.2.x/DRF, React 19/Vite 8 en el repositorio; **no** asumir las versiones recordadas de otros proyectos.
- `backend/config/settings.py` utiliza `backend/db.sqlite3` para tablas internas Django; el archivo binario **está versionado**. Proponer una ubicación de autenticación no ambigua respecto a la rúbrica; no trasladar silenciosamente la información de usuario.
- `db/postgres/init.sql` y `db/mysql/init.sql` tienen entidades y restricciones; su existencia **no prueba** que los volúmenes locales recibieron las últimas revisiones.
- MongoDB actual es standalone; B **no** habilita replica set unilateralmente. Si A necesita transacciones multidocumento, coordinar un PR exclusivo para Compose.
- `docker-compose.yml` **no** incluye `hc_mongo_init`, aunque README lo menciona. Los puertos: frontend `5173`, backend `8000`, PostgreSQL `5432`, MySQL host `3307`, Mongo host `27017`, Firestore API host `8082`, Firestore UI `4000`, Adminer `8081`.
- La única prueba Django auditada valida `/api/health/`.

## 1. Diez reglas no negociables del agente B

1. **Inspeccionar antes de editar.** Leer `git status`, rama, diff, archivo completo y dependencias. No reemplazar trabajo reciente por una versión propia antigua.
2. **No inventar contratos.** Implementar exclusivamente `CONTRACT-API-01@1.0` y `CONTRACT-REPO-01@1.0` ratificados en F0. Las rutas y ejemplos del plan son propuestas hasta su aprobación.
3. **No tocar zona A.** Nunca modificar `frontend/**`, `db/mongo/**`, `db/firebase/**`, `mongo_adapter.py` ni `firestore_adapter.py` sin handoff explícito y aprobación de Jennifer.
4. **No tocar `main` directamente.** Una rama por tarea, un PR por tarea; no `push --force` a ramas ajenas y no merges sin revisión cruzada.
5. **Pruebas antes de PR.** Ejecutar como mínimo las disponibles afectadas; si no hay runner para una prueba, registrar “no ejecutada” con causa. No declarar pruebas inexistentes como aprobadas.
6. **No secretos ni expedientes reales.** `.env`, contraseñas, tokens, backups y datos reales no van a Git, screenshots ni logs compartidos.
7. **No renombrar IDs, rutas, slugs, códigos de error ni tipos ya ratificados.** Cambio incompatible requiere `contract/*` y aprobación de ambos coordinadores.
8. **No reparar código de A por cuenta propia.** Reportar fallo reproducible, abrir issue/pedir handoff; workaround local no mergeable solo si está aislado, probado y documentado.
9. **Código y documentación en español técnico coherente.** Nombres de símbolos existentes se conservan; mensajes clínicos claros, sin comentarios de relleno.
10. **Escalar bloqueos, no adivinar.** Si faltan fixtures, detalles de campos, transacciones o decisión académica, activar protocolo de bloqueos y continuar una subtarea independiente.

## 2. Zonas reservadas: límites exactos

| Tipo | Sí puede modificar B | NO puede modificar B | Aprobación requerida |
|---|---|---|---|
| Dominio/API | `backend/apps/historiales/domain/**`, `application/**`, `presentation/**`, `backend/config/**` | Ninguna ruta A | Contratos con revisión explícita de A. |
| SQL | `db/postgres/**`, `db/mysql/**` | `db/mongo/**`, `db/firebase/**` | Si un cambio altera `CONTRACT-REPO-01`, acuerdo A↔B. |
| Adaptadores | `postgres_adapter.py`, `mysql_adapter.py`, `infrastructure/factory.py` | `mongo_adapter.py`, `firestore_adapter.py` | La fábrica debe conservar registro de los cuatro motores. |
| Pruebas | Nuevos `test_*_sql.py`, `test_auth.py`, `test_api.py` bajo `backend/apps/historiales/` | Tests escritos por A (`test_*_nosql.py`) | Si se cambia test común o `tests.py`, avisar A. |
| Infraestructura | Solo por PR coordinado: `docker-compose.yml`, `.env.example`, `.gitignore`, `README.md`, `.github/**`, docs raíz | Edición simultánea de compartidos | Reservar dueño de cada PR compartido. |
| UI | Ninguna | `frontend/**` | Solicitud formal a A en vez de editar. |

**⚠️ requiere acuerdo A↔B:** cambiar `domain/ports.py` impacta ambos adaptadores NoSQL; cambiar `factory.py` puede romper enrutamiento; mover el auth de SQLite a PostgreSQL requiere evaluar los datos existentes y la interpretación de la rúbrica; modificar Compose para Mongo/Firestore impacta ambos entornos. El dueño del archivo no tiene permiso para cambiar arbitrariamente el contrato.

## 3. Protocolo de arranque común: el mismo punto que Jennifer

**Primera dependencia:** integrar `PR-00` (solo tres guías `.md`); no asumir que ya está integrado. A es la dueña de PR-00; B lo revisa. Tras merge, ambos deben confirmar que `main` apunta al **mismo SHA nuevo** y que los documentos son idénticos.

### 3.1 Preparación de entorno (PowerShell, Windows)

```powershell
# Si todavía no está clonado:
git clone https://github.com/PabloZ7-425/Red_Instituciones_Medicas.git
cd Red_Instituciones_Medicas

# Si el repo ya existe, ejecutar desde su carpeta:
git fetch origin
git switch main
git pull --ff-only origin main
git rev-parse HEAD
git status --short

# Configuración local no versionada; no sobrescribir una .env existente:
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
notepad .env
# Configurar contraseñas locales propias en lugar de los valores 'cambiar_*'.

# Con Docker Desktop iniciado:
docker compose config -q
docker compose up --build -d
docker compose ps -a
curl.exe -f http://localhost:8000/api/health/
curl.exe -f http://localhost:8000/api/health/databases/
docker compose exec -T backend python manage.py check
docker compose exec -T backend python manage.py test apps.historiales
docker compose exec -T frontend npm run build
```

**Aceptar C0 solo si:** `/api/health/databases/` muestra `connected: true` en hospital, pediatrico, laboratorio y odontologica; `check`, test y build terminan sin error; Docker muestra servicios principales activos. Si hay un motor caído, **no** afirmar que Docker está listo por el simple `200` de `/api/health/`.

**Diagnóstico sin destruir datos:** `docker compose logs --tail=100 backend`, `docker compose logs --tail=100 postgres`, `docker compose logs --tail=100 mysql`; `docker compose config`; `docker compose ps -a`. No usar `docker compose down -v`, `docker volume prune` ni resetear base por defecto. Si SQL no refleja cambios, recordar que `init.sql` solo corre en volúmenes vacíos: proponer migración incremental/backup, no borrado.

**Registro de salida al finalizar:** SHA, OS/herramientas (Docker y Git), servicios en `ps`, estado de 4 BD, tests, build, errores redactados. Compartir con Jennifer solo resultados, **nunca** `.env`.

### 3.2 Corrección inicial del SQLite versionado (B; PR separado coordinado)

No realizarla mezclada con contratos. Verificar primero: `git ls-files backend/db.sqlite3`. Si está trackeado:

```powershell
# En rama separada y con trabajo limpio (p. ej. chore/pablo-ignore-sqlite)
# Incorporar `backend/db.sqlite3` o `db.sqlite3` a .gitignore si corresponde.
git rm --cached backend/db.sqlite3
# Verificar que el archivo local NO fue borrado y que no aparecen secretos en el diff:
git status --short
git diff --cached --stat
```

`--cached` lo retira de Git sin borrarlo de la máquina. **No ejecutar `git rm` sin `--cached`**. Evitar que un cambio a `.gitignore` compita con otra rama; reservarlo. La reubicación de la base Django para auth es **otra decisión** (`D0-02`), no parte automática de esta limpieza.

## 4. Contratos de B: qué entrega y qué recibe

### 4.1 Entregables hacia A (dueño B, aprobación A)

| Contrato / elemento | Entrega de B | Cliente A | Riesgo si falla |
|---|---|---|---|
| `CONTRACT-API-01` | 10 operaciones API-01..10, DTOs, ejemplos HTTP 200/201/4xx y formato de error, autenticación | React + mocks | UI desacoplada solo en apariencia. |
| `CONTRACT-REPO-01` | Puerto común con 8 métodos, firmas, excepciones de dominio, tipos `string` | Adaptadores Mongo/Firestore | Métodos incompatibles. |
| `D0-01/02/03` | Mecanismo auth, ubicación directorio de usuarios, roles/permisos | Login y pruebas de acceso de A | Cross-institution data leak. |
| Factory | Instancia adaptador según usuario validado, no según request | A prueba adaptadores NoSQL | Selector de motor manipulable. |
| API disponible | URLs de desarrollo, cambios de serialización y fixtures | Integración React | Errores 400/500 difícilmente depurables. |
| Pruebas comunes | Ejecución del contrato con matrices de casos | A corre su adaptador | Falsos positivos entre motores. |

### 4.2 Dependencias que B recibe de A

| Entrada de A | Cuándo | Verificación de B | Si falta |
|---|---|---|---|
| Confirmación de DTOs y manejo de `ObjectId`/ID externos | C0 | Ejemplo `id` string y fecha válido | `blocked-by-jennifer` + mock contractual local solo para tests propios. |
| Decisión embebido/referencia NoSQL | C1/C2 | Documento de modelo y ejemplos de consulta | No cambiar puertos para adaptar SQL al diseño NoSQL. |
| Adapter Mongo/Firestore conforme puerto | C3/C4 | Ejecutar suite común | Issue a A, no escribir su adapter. |
| Necesidades del frontend sobre errores, paginación, auth | C0/C5 | Casos de aceptación documentados | Proponer `contract/*`, nunca romper silenciosamente. |
| Tests y evidencia de UI | C6/C8 | Flujo completo cubre instituciones | Pruebas API B continúan independiente. |

## 5. Gate obligatorio Fase 0 (11 ítems)

Copiar casillas a la descripción del PR de contrato o issue F0; A y B confirman por comentario/revisión.

- [ ] `G0-01` Git `main` sincronizado y SHA compartido tras PR-00.
- [ ] `G0-02` `.env` local y no versionado en ambos equipos.
- [ ] `G0-03` `docker compose config -q` pasa en ambos.
- [ ] `G0-04` Docker levanta los servicios principales en ambos.
- [ ] `G0-05` Cuatro motores conectados según endpoint en ambos.
- [ ] `G0-06` Django `check` + test baseline pasan en ambos.
- [ ] `G0-07` Build React pasa en ambos.
- [ ] `G0-08` Decisiones D0-01..D0-05 ratificadas.
- [ ] `G0-09` Decisiones D0-06..D0-10 ratificadas.
- [ ] `G0-10` Contratos API/REPO v1 aprobados, con ejemplos válidos/errores.
- [ ] `G0-11` PR-00 integrado y primeras tareas/archivos reservados.

**No abrir PRs C1–C4 que implementen contrato hasta cerrar G0-10.** Sí se puede investigar, preparar fixtures y planear tareas propias sin afirmar compatibilidad final.

## 6. Plan de tareas B por ciclo: orden operativo C0–C9

**Convención de IDs:** `B-Cn-T1` = tarea B del ciclo n; `PR-02,04,...20` son identificadores de **plan** y no números reales de GitHub. `F0.T1` a `F5.T*` designan hitos; `EPIC-00` a `EPIC-05` definen fases. **Cada fila define un PR**, no se agrupan varias filas en un PR. Los paths marcados “nuevo” no existen aún.

| Orden/épica | Tarea / PR | Insumos y dependencia | Archivos B permitidos | Salida y aceptación verificable |
|---|---|---|---|---|
| `C0 · EPIC-00 · F0.T1` | **`B-C0-T1` — `PR-02`** contrato y decisiones F0 | PLAN, revisión de A, inventario código, `D0-*`; PR-00 integrado | `domain/{entities,ports,institutions}.py`, docs contrato **reservados**, pruebas contrato B (nuevo) | `CONTRACT-API-01@1.0` 10 operaciones + `CONTRACT-REPO-01@1.0` con firmas/errores/ejemplos, decisiones ratificadas A↔B; Django `check`/test salud siguen pasando. **No implementar CRUD todavía.** |
| `C1 · EPIC-01 · F1.T1` | **`B-C1-T1` — `PR-04`** autenticación/enrutamiento | C0 cerrado, D0-01/02/03, matriz de roles | `backend/config/**`, `application/**`, `presentation/**`, `infrastructure/factory.py`, tests auth B (nuevo) | Login y `/me` según contrato; usuario con institución; solicitud a otra institución denegada; no aceptar parámetro libre `motor` del cliente; tests auth y acceso pasando. |
| `C2 · EPIC-01 · F1.T2` | **`B-C2-T1` — `PR-06`** saneamiento de SQL | Modelo ER Entrega I disponible, observaciones del docente (si existen), contrato v1 | `db/postgres/**`, `db/mysql/**`, docs SQL reservados, tests SQL B (nuevo) | Scripts/migraciones con relaciones válidas; índices fundamentados; restricciones `CHECK`/FK verificadas con inserts demo y fallos esperados; no pérdida de datos existentes. |
| `C3 · EPIC-02 · F2.T1` | **`B-C3-T1` — `PR-08`** adaptador PostgreSQL | C0 contrato, C2 modelo SQL; suite de contrato común | `postgres_adapter.py`, tests PostgreSQL B (nuevo) | 8 métodos del puerto funcionan con una historia demo hospitalaria; rollback verificado donde aplique; IDs/errores normalizados y suite de contrato pasan. |
| `C4 · EPIC-02 · F2.T2` | **`B-C4-T1` — `PR-10`** adaptador MySQL | Puerto v1, C2 modelo pediátrico, pruebas de C3 | `mysql_adapter.py`, tests MySQL B (nuevo) | 8 métodos y operaciones del historial pediátrico; FKs/estado/archivo correctos; suite de contrato y tests de integridad pasan. |
| `C5 · EPIC-03 · F3.T1` | **`B-C5-T1` — `PR-12`** API clínica DRF | Al menos PostgreSQL validado; DTOs y errores acordados; mocks A disponibles | `application/**`, `presentation/**`, `backend/config/urls.py` si corresponde, tests API B | API-03..10 conectados a casos de uso; códigos acordados; paginación; no revelar institución ajena; pruebas `GET/POST/PATCH`, negativas y permiso. |
| `C6 · EPIC-03 · F3.T2` | **`B-C6-T1` — `PR-14`** validación + especializaciones prioritarias | A reporta necesidades UI; `REQ-*` rúbrica, API clínica | `application/**`, `presentation/**`, tests B | Flujo uniforme en 4 motores, validaciones completas y endpoints especializables acordados vía contrato; hospital ingreso/cama/alta, pediatría tutores/vacunas/crecimiento en el alcance priorizado; pruebas de autorización. |
| `C7 · EPIC-04 · F4.T1` | **`B-C7-T1` — `PR-16`** ACID/auditoría SQL | Operaciones SQL ya estables; casos de fallo definidos | `db/postgres/**`, `db/mysql/**`, adaptadores SQL, tests SQL B | Transacciones con rollback comprobable, cambios sensibles auditados con mecanismo justificado, sin datos clínicos completos en logs; tests de falla y permisos pasan. |
| `C8 · EPIC-04 · F4.T2` | **`B-C8-T1` — `PR-18`** pruebas integración + recuperación SQL | Base y API estables, datasets ficticios, plan de backup | Scripts SQL de respaldo/prueba (nuevos, bajo `db/postgres/` y `db/mysql/`), tests B y docs reservadas | `pg_dump`/restauración y dump MySQL/restauración demostrados en entornos de prueba; tests API y aislamiento; procedimiento y evidencias reproducibles, sin backups con PHI. |
| `C9 · EPIC-05 · F5.T1` | **`B-C9-T1` — `PR-20`** cierre backend/SQL | Todos los ciclos, rúbrica y evidencia A | Documentación SQL/backend reservada, correcciones dentro de zona B | Modelos/normalización/seguridad/transacciones documentados, matriz requisitos `REQ-*` cubierta, PR revisado por A, demo y pruebas sin regresiones. |

### 6.1 Pautas de implementación por bloque: ejecutar en ese orden

**B-C0-T1 — Contratos:**

- [ ] Inspeccionar la diferencia entre `HistorialRepository` actual y el boceto de 8 métodos del `PLAN_MAESTRO.md`.
- [ ] Definir DTOs por operación, `id` string externo, fechas, errores, paginación y campos obligatorios. Revisar con Jennifer antes de fijar firma.
- [ ] Ratificar mecanismo de autenticación y almacenamiento interno con `D0-01/02`, teniendo en cuenta que SQLite no puede ser presentado como motor clínico.
- [ ] Versionar ejemplos `request/response` y pruebas de aceptación (error 400, 401, 403/404, 409 cuando aplique) sin exponer datos reales.
- [ ] Obtener revisión explícita A. Si A objeta estructura NoSQL, atender mediante `contract/*` antes de fusionar.

**B-C1-T1 — Auth:**

- [ ] Reusar autenticación segura de Django; nunca guardar contraseña plana ni SHA256 directo sin algoritmo de passwords de Django.
- [ ] Usuario ligado de forma inequívoca a institución y rol. Definir roles reales por operación; usuario sin institución = rechazo.
- [ ] En cada request, derivar repositorio solo del principal autenticado. Probar acceso cruzado con 2 cuentas de instituciones diferentes.
- [ ] No dejar abierta la API clínica con `AllowAny` por comodidad. Resolver autenticación de prueba con fixtures.

**B-C2-T1 — Esquemas:**

- [ ] Registrar evidencia de normalización y FKs existentes sin alterar todas las tablas por estética.
- [ ] Verificar campos necesarios para `consulta`, `diagnostico`, `tratamiento`, `receta`, archivo lógico e institución.
- [ ] Distinguir `init.sql` de scripts incrementales; no pedir a A ni al usuario destruir volúmenes.
- [ ] Preparar datos DEMO reproducibles y constraints negativos.

**B-C3/C4 — Adaptadores SQL:**

- [ ] Implementar todos los métodos del puerto ratificado, no métodos con nombres propios imposibles de consumir desde aplicación.
- [ ] Usar SQL parametrizado; no interpolar IDs, búsquedas o textos clínicos directamente en SQL.
- [ ] Abrir y cerrar conexiones de forma controlada; mapear `IntegrityError` a errores de dominio sin devolver SQL crudo.
- [ ] Mantener integridad cuando una operación modifica varias tablas y probar rollback.
- [ ] Registrar test positivo, negativo y concurrencia razonable en operaciones sensibles.

**B-C5/C6 — API:**

- [ ] Separar serializadores, vistas y casos de uso; no mezclar queries SQL en las vistas.
- [ ] No introducir `motor`/`institucion` como selector libre en endpoint de paciente.
- [ ] Probar contra la interfaz mock de A, especialmente JSON, fechas y errores; documentar desajustes con ejemplo mínimo.
- [ ] Consultar con A cualquier endpoint adicional de especialización; acordar antes de implementarlo.

**B-C7/C8 — Confiabilidad:**

- [ ] Definir operaciones donde es imprescindible atomicidad y simular fallo a mitad de transacción.
- [ ] Si trigger SQL resuelve auditoría concreta, documentar motivo, datos capturados, costo y privacidad. No trasladar todas las reglas de negocio a triggers.
- [ ] Respaldar/restaurar datos DEMO en base separada; no sobreescribir la base activa de la otra célula.
- [ ] Redactar secretos de logs/evidencias.

**B-C9 — Entrega:**

- [ ] Confirmar tabla institucional y argumentos de elección de PostgreSQL/MySQL.
- [ ] Comparar ACID y enfoque documental con A evitando simplificaciones “NoSQL = eventual siempre”.
- [ ] Adjuntar evidencia ejecutada, no capturas simuladas o resultados inventados.
- [ ] Verificar que la memoria de Entrega I corregida esté incorporada si existía fuera de Git.

## 7. Pruebas y comandos exactos antes de cada PR B

### Disponible **hoy**, no depende de agregar paquetes

```powershell
# Desde la raíz
git status --short
git diff --check
docker compose config -q
docker compose ps -a
docker compose exec -T backend python manage.py check
docker compose exec -T backend python manage.py test apps.historiales
docker compose exec -T frontend npm run build
curl.exe -f http://localhost:8000/api/health/
curl.exe -f http://localhost:8000/api/health/databases/
```

**Afirmar:** estos son comandos disponibles en `main` auditado, pero **no se ejecutaron desde el entorno de esta guía**. B debe guardar códigos de salida y resultado real. `npm run lint`, `ruff`, `black`, `pytest`, `vitest` **no están configurados hoy** y no deben figurar como “pasaron”. Añadir herramientas solo mediante decisión `D0-09` y PR con scripts reproducibles.

### Pruebas que B debe **crear** y luego ejecutar

Proponer archivos separados, por ejemplo `backend/apps/historiales/test_auth.py`, `test_api.py`, `test_postgres_sql.py`, `test_mysql_sql.py`, `test_contract_sql.py` (**no existen aún**). El `python manage.py test apps.historiales` debe descubrirlos; si se cambia el layout, actualizar README en PR coordinado. Cada archivo contiene fixtures falsos, limpieza que no afecte otros volúmenes, casos de error y aserciones de persistencia.

| Suite B | Caso positivo | Caso negativo obligatorio |
|---|---|---|
| Auth | Login, `/me`, institución correcta | 401 sin login; denegación entre instituciones |
| PostgreSQL | Alta→consulta→diagnóstico→tratamiento→receta→lectura | Identificación duplicada, rollback y FK inválida |
| MySQL | Igual, además tutor/vacuna/control | Cita/relación inexistente; estado inválido |
| API | 10 operaciones acordadas | JSON incorrecto, permisos, inexistencia, conflicto |
| Integración | UI A con API real y 4 motores | Una BD caída se maneja sin fugas de excepción |
| Recuperación | Restauración a destino aislado | Demostrar que una copia incompleta no se anuncia válida |

Antes de PR: `git diff --check`, tests afectados, `python manage.py check`, `npm run build` si cambio compartido puede afectar frontend, capturas redactadas solo si aportan evidencia. Si no puede correr Docker por recursos del equipo, notificar bloqueo; **no simular salida**.

## 8. Protocolo de bloqueos y violaciones de contrato

| Problema | Acción obligatoria de B | Trabajo independiente permitido | Lo que NO debe hacer |
|---|---|---|---|
| Falta contrato/DTO v1 | Comentar en issue `blocked-by-jennifer` o `blocked-by-pablo` según dueño de decisión; citar método y campo; escalar a coordinadores | Tests de salud, revisión SQL sin alterar puertos | Inventar payload y fusionarlo. |
| Falta fixture NoSQL de A | Solicitar identificador DEMO, estructura, expected; marcar PR como **bloqueado** | Fixtures SQL propios, pruebas de dominio | Crear colecciones de A por su cuenta. |
| Test de contrato falla en adaptador A | Abrir issue con título prefijo **`contract-violation`**; incluir contrato/version, input DEMO, esperado, actual, SHA/log redactado; asignar A | Continuar tests/SQL propios | Modificar Mongo/Firestore para “arreglar”. |
| Bug en `docker-compose.yml`/`.env.example` | Abrir issue especificando líneas/impacto y pedir reserva de archivo; PR pequeño asignado a un solo dueño | Diagnóstico de logs y workaround temporal local (no commit) | Dos PR tocando Compose simultáneamente. |
| API requerida por UI no prevista | Propuesta `contract/*`, ejemplo de uso y compatibilidad; solicitar aprobación A↔B | Endpoint ya acordado, mocks internos B | Cambiar unilateralmente ruta existente. |
| PR ajeno rompe `main` | Reproducir en rama nueva, citar commit y abrir incidencia/PR revertido coordinado | Continuar en rama propia tras sincronizar | `push --force` / rollback destructivo sin avisar. |
| Cambios SQL no aparecen en volúmenes | Inspeccionar `docker compose ps/logs` y conexión; generar migración incremental con respaldo | Pruebas con base fresca aislada | `docker compose down -v` sin aprobación explícita. |

### Protocolo detallado ante `contract-violation`

1. Registrar `CONTRACT-API-01` o `CONTRACT-REPO-01`, versión y operación `API-*`/método.
2. Adjuntar reproducción mínima con datos ficticios, esperado, actual y comandos que fallan. Redactar secretos.
3. Abrir issue con título `contract-violation: <operación> en <adaptador o API>`; si no existe la etiqueta `contract-violation`, usar el prefijo en el título.
4. Marcar PR dependiente como **draft/bloqueado**. No corregir archivo A ni fusionar bypass que esconda un fallo de permisos.
5. Si hay propuesta de modificar contrato, abrir PR `contract/*` (B redacta; A aprueba); luego adaptar tests, A y B por separado.
6. Reanudar cuando ambos indiquen SHA de arreglo y test de contrato pasando. Un TODO/workaround temporal debe estar aislado, ser explícito y **no** aprobarse para el cierre del ciclo.

## 9. Formato obligatorio de PR B

**Ejemplo de título:** `[B-C3-T1] PostgreSQL: persistencia de historial (CONTRACT-REPO-01)`.

```markdown
## Qué cambia
- ...

## Identificación
- Célula: B / Pablo
- Ciclo y tarea: B-Cn-T1
- PR del plan: PR-XX (no es el número de GitHub)
- Épica y requisito: EPIC-0N, REQ-0N
- Dependencia de A: ninguna / enlace al PR-XX de A / blocked-by-jennifer

## Contratos
- CONTRACT-API-01@1.0: sin cambios / cambios propuestos en contract/*
- CONTRACT-REPO-01@1.0: sin cambios / cambios propuestos en contract/*
- ¿Rompe un contrato aprobado?: NO / SÍ (NO fusionar hasta aprobación A↔B)

## Archivos modificados y razón
- ruta: motivo

## Cómo probar (comandos y salida real)
- [ ] git diff --check
- [ ] docker compose config -q
- [ ] docker compose exec -T backend python manage.py check
- [ ] docker compose exec -T backend python manage.py test apps.historiales
- [ ] Otras pruebas concretas nuevas: ...

## Evidencia
- Caso positivo con dato DEMO: ...
- Caso negativo: ...
- SHA base / entorno: ...
- Logs redactados o enlace a ejecución: ...

## Seguridad y persistencia
- [ ] Sin secretos ni PHI
- [ ] No cambia el motor asignado ni permite elegirlo desde UI
- [ ] Maneja fallos sin parcialidad indebida
- [ ] No borra volúmenes ni datos de compañeros

## Checklist antes del merge
- [ ] Solo toca zona B o existe acuerdo explícito sobre archivo compartido
- [ ] Las dependencias están integradas o justificadas
- [ ] Documentación y pruebas actualizadas
- [ ] Jennifer revisó el PR si afecta contrato/integración
- [ ] Ningún TODO bloqueante pendiente
```

**Revisión de PR A:** comprobar que el código A cumple los DTOs con los que B implementa la API; no comentar preferencias de estilo como bloqueantes salvo que generen seguridad, regresiones o incompatibilidad. Una corrección en archivo A corresponde a un PR de A.

## 10. Handoff y coordinación desde Pablo

### 10.1 Antes de entregar un contrato/API a A

- [ ] Versionar el contrato y adjuntar ejemplos de **request + response** sin datos reales.
- [ ] Incluir status HTTP, código de error y condiciones de permisos.
- [ ] Identificar impacto exacto en componente React y adaptadores Mongo/Firestore.
- [ ] Ejecutar tests existentes, indicar nuevas pruebas todavía pendientes.
- [ ] Solicitar confirmación de Jennifer: **“aprobado para implementar”**. No basta un mensaje ambiguo “lo vi”.
- [ ] Registrar SHA y PR; no cambiar sin emitir nueva revisión.

### 10.2 Cuando A informa `blocked-by-pablo`

1. Confirmar recibo, abrir referencia al issue/PR; responder primero con **qué está bloqueado y por qué**.
2. Determinar si B debe entregar DTO, endpoint, fixture API o configuración común.
3. Dar una respuesta concreta de contrato (con ejemplo) o abrir PR de corrección solo en zona B.
4. No pedirle a A que edite `domain/`, `presentation/` o `config/` para sortear el bloqueo.
5. Ejecutar prueba compartida; informar SHA y caso que habilita a A a continuar.

### 10.3 Revisión al final de cada ciclo

- [ ] B completó su `B-Cn-T1` (o dejó issue bloqueante claro con evidencia).
- [ ] A confirmó el contrato que usa y no existen contradicciones.
- [ ] Todas las pruebas basales y específicas del ciclo pasan.
- [ ] Ambos PR están integrados a `main` **o** el gate queda abierto.
- [ ] Se actualiza matriz `REQ-*` y se registra deuda real, no promesas.

## 11. Convenciones mínimas, seguridad y anti-patrones

- Preferir nombres coherentes con el repositorio (`paciente`, `consulta`, `diagnostico`, `tratamiento`, `receta`) y firmas aprobadas. Los cambios de naming requieren revisión si afectan al cliente.
- SQL parametrizado, restricciones de integridad y transacciones donde hay múltiples escrituras; ninguna concatenación de datos clínicos en SQL.
- Contraseñas solo con hashing robusto provisto por Django; no registrarlas ni enviarlas a logs.
- Fechas clínicas sin hora `YYYY-MM-DD`; timestamps UTC `Z`; el frontend se encarga de la presentación local. ID serializado en string para el contrato externo; conversiones internas por adaptador.
- Errores de API estables, no excepciones SQL crudas. No incluir trazas sensibles en `DEBUG=False`; desarrollo con `DEBUG=True` solo local.
- No instalar librerías no necesarias ni migrar el stack por preferencias del agente. Ruff/Black/ESLint son **opciones**, no herramientas presentes ni requisitos impuestos. Decisión en D0-09.
- No cambiar Firebase/MongoDB de forma unilateral ni sustituir Firestore por otro servicio.
- No normalizar todas las entidades documentales como si fueran SQL, ni desnormalizar SQL solo para imitar NoSQL.
- No usar triggers para esconder toda la lógica clínica del servicio; justificar cada uno.
- No inventar “100 % de cumplimiento” con pruebas parciales; reportar verificación que falta.

## 12. Orden inmediato de actuación para Pablo y su IA

1. **No programar en `main`.** Confirmar PR-00 con los tres documentos; revisar y aprobar lo que le corresponde.
2. En ambos equipos (con Jennifer), ejecutar §3.1 y compartir SHA + checklist G0-01..G0-07.
3. Preparar `B-C0-T1`: proponer `D0-01` a `D0-10`, los ejemplos de `CONTRACT-API-01` y el puerto `CONTRACT-REPO-01` desde lo que realmente existe.
4. Solicitar revisión a Jennifer; resolver incompatibilidades sin implementar todavía los adaptadores.
5. Completar decisiones y revisión A↔B, fusionar `PR-02` una vez aprobado el contrato; después A finaliza e integra `PR-01` con mocks compatibles. Cerrar G0-08..G0-11; no iniciar C1 hasta ratificación.
6. Recién entonces crear `feature/pablo-c1-auth-routing` y empezar `B-C1-T1`. Informar a A qué rutas/fixtures auth están disponibles.

**Regla de oro: PR pequeño y respetuoso del contrato > velocidad aparente.**


---

## Anexo operativo — ADR-ORM-01: uso restringido de Django ORM (agregado el 2026-10-20)

**Contexto y autoridad:** esta decisión está incorporada en `PLAN_MAESTRO.md`. Jennifer acepta la solución híbrida; Pablo debe ratificarla en Fase 0 y cerrar `D0-02` **antes de cualquier migración**. El anexo aclara las tareas existentes, **no** crea nuevos ciclos, modifica `CONTRACT-API-01`/`CONTRACT-REPO-01` ni autoriza cambios en zonas de A.

### Qué implementa B con ORM y qué no

- **Sí, Django ORM:** cuentas, `User`/modelo de usuario según decisión técnica, credenciales hasheadas mediante los hashers de Django, roles/grupos/permisos y sesiones/administración interna. Reutilizar `django.contrib.auth` y su protección de contraseñas. No decidir un cambio de `AUTH_USER_MODEL` después de ejecutar migraciones sin evaluar sus consecuencias.
- **No, Django ORM:** tablas clínicas de hospital y pediatría; usar `psycopg` para PostgreSQL y `mysql-connector-python` para MySQL en sus adaptadores, con SQL parametrizado, FKs, restricciones, índices y transacciones explícitas. No copiar modelos SQL clínicos a `backend/apps/historiales/models.py` ni utilizar `managed=False` como atajo general.
- **No, ningún ORM/ODM nuevo:** MongoDB y Firestore son propiedad de A y continúan con PyMongo y SDK de Firestore. B no instala ni configura librerías para reemplazarlos.
- **DRF:** autentica/autorización con identidad central, obtiene de la sesión/token la institución validada y delega casos de uso a los puertos. La API no debe devolver ni confiar en un motor elegido desde React.

### Procedimiento obligatorio por hito ya previsto

| Hito existente | Instrucción precisa para B | Evidencia / bloqueo |
|---|---|---|
| `B-C0-T1` → `PR-02` | Presentar a A un diseño `ADR-ORM-01` que complemente `D0-01/02/03`: mecanismo de auth, ubicación del directorio, roles, conexión Django y separación técnica respecto al hospital. | **Bloquear** desarrollo de migraciones si `D0-02` no está ratificada. Publicar propuesta/revisión, no dar por creadas las tablas. |
| `G0-08` | Jennifer y Pablo registran aprobación/observaciones de `ADR-ORM-01` dentro de `D0-02` (sin nueva casilla). | Prueba: decisión explícita en PR de contrato y revisión de A. |
| `B-C1-T1` → `PR-04` | Configurar autenticación Django ORM **solo después del gate F0**. Mantener aislado el almacén técnico; realizar cambios de configuración con migraciones planificadas y reversión posible. | Tests de usuario/login, permisos, sesión o token según `D0-01`, enrutamiento y prohibición de acceso cruzado. |
| `B-C3-T1` → `PR-08` | Implementar acceso hospitalario con `psycopg`, no ORM. | Tests positivos/negativos/rollback y consultas parametrizadas. |
| `B-C4-T1` → `PR-10` | Implementar acceso pediátrico con `mysql-connector-python`, no ORM. | Tests positivos/negativos/rollback y consultas parametrizadas. |
| `B-C5-T1` → `PR-12` | Las vistas/serializadores llaman casos de uso y puertos, **no** SQL directo ni modelos ORM clínicos. | Tests API + autenticación y error 401/403/404 ratificado. |

### Riesgo específico de autenticación y SQLite

`backend/config/settings.py` configura hoy `django.db.backends.sqlite3` para tablas internas y el binario `backend/db.sqlite3` figura en Git. La recomendación a evaluar y ratificar en `D0-02` es una **base o esquema técnico de autenticación PostgreSQL separado del hospital**; todavía no es una migración realizada. Mantener trazabilidad de usuarios y sesiones antes de mover datos. No apuntar el ORM a la misma base clínica con migraciones automáticas inadvertidas; el backend arranca hoy con `python manage.py migrate`, por lo que cambiar `DATABASES` puede modificar datos al iniciar Docker. No borrar SQLite, usuarios ni volúmenes automáticamente. Coordinar toda modificación de Compose o configuración compartida y respetar las cuatro instituciones/motores del enunciado.

**Si falta algo de A:** para integrar UI, entregar respuesta sintética conforme `CONTRACT-API-01`; para Mongo/Firestore solicitar adaptador y fixture bajo `blocked-by-jennifer`, sin modificarlos. A no necesita conocer cómo se guardan usuarios con ORM, solo los JSON/errores aprobados.

### Pruebas y PR (comandos disponibles frente a comandos posteriores)

```powershell
# Comprobaciones iniciales (antes de migrar), desde raíz del repo
 docker compose config -q
 docker compose exec backend python manage.py check
 docker compose exec backend python manage.py shell -c "from django.conf import settings; print(settings.DATABASES['default']['ENGINE'])"
 docker compose exec backend python manage.py test apps.historiales
 git diff --check
```

Las pruebas actuales de Django **no** validan todavía autenticación clínica ni migración. En `PR-04`, agregar pruebas automáticas para usuario, permisos, aislamiento institucional y persistencia del almacén técnico; ejecutar también esas pruebas nuevas y adjuntar salida real. Tras ratificar `D0-02`, documentar explícitamente comandos de migración con alias y un método de respaldo/reversión antes de ejecutar; **no** asumir que `manage.py migrate` en el arranque sigue siendo seguro. Los PRs `PR-08/10` deberán acreditar transacciones de drivers nativos, no asumir que `django.db.transaction.atomic()` gobierna conexiones directas de `psycopg` o `mysql-connector-python`.

**No permitido:** introducir modelos Django para pacientes, consultas, diagnósticos o recetas de los cuatro motores; reemplazar SQL sin acuerdo; ejecutar migraciones/limpieza destructivas; cambiar rutas/códigos/IDs del contrato; ajustar frontend o adaptadores NoSQL de A para resolver un error propio. **Regla de bloqueo:** informar a A con evidencia y solicitud concreta, conservar rama y PR acotados, esperar ratificación.
