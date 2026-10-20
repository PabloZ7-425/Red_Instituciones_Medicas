# GUIA_JENNIFER_AGENTES.md — Célula A: Jennifer + agentes IA

> **Documento operativo autocontenido** — versión 1.0 (2026-10-20).
> **Responsable humana:** Jennifer. **Célula:** A.
> **Ámbitos exclusivos:** React/Vite y experiencia de usuario, MongoDB para Laboratorio, Firestore para Odontología, adaptadores NoSQL y pruebas documentales.
> **Contraparte:** Pablo + agentes IA = Célula B: Django/DRF, autenticación, dominio/contratos, PostgreSQL, MySQL y API.
> **Lectura obligatoria previa:** [`PLAN_MAESTRO.md`](./PLAN_MAESTRO.md) y [`GUIA_PABLO_AGENTES.md`](./GUIA_PABLO_AGENTES.md) (para límites).
> **Punto auditado:** `main` en `434968295c77b1ba5b3fa96f9f11d367c5a7c835`, 2026-10-20. SHA de trabajo cambiará cuando se fusione PR-00.
> **Estado:** guía de ejecución **propuesta**; no implica que estos PRs, tests o endpoints existan aún.

## 0. Contexto real del proyecto y nuestra responsabilidad

El proyecto final de **Bases de Datos II** es una plataforma de historiales clínicos para cuatro instituciones independientes con cuatro motores distintos y **una sola interfaz**. Las reglas clínicas se implementan mediante puertos/casos de uso comunes en Django, mientras los adaptadores persisten información. El motor se elige automáticamente al autenticar al usuario asociado con su institución. La rúbrica exige pacientes nuevos, consulta y mantenimiento de historias, diagnósticos, tratamientos, medicamentos, archivo, comparación entre motores, seguridad y modelo NoSQL justificado.

| Institución | Motor | Responsable | ¿Qué hacemos? |
|---|---|---|---|
| Hospital general | PostgreSQL | Pablo/B | A solo consume API y verifica UI/contrato. |
| Centro pediátrico | MySQL | Pablo/B | A solo consume API y verifica UI/contrato. |
| Laboratorio clínico | MongoDB 7 | **Jennifer/A** | Modelado documental, operaciones clínicas y de exámenes, adaptador. |
| Clínica odontológica | Firestore Emulator | **Jennifer/A** | Modelo documental completo, citas/procedimientos/recetas/pagos administrativos, adaptador. |
| Interfaz de las 4 | React 19 + Vite 8 | **Jennifer/A** | Login, pacientes, historia y especializaciones sin selector libre del motor. |

**Lo que hay en el repositorio:** `frontend/src/pages/HomePage.jsx` es una pantalla de estado de conexiones; `frontend/src/api/health.js` solo consulta `/api/health/databases/`. `db/mongo/init.js` define seis colecciones (`usuarios`, `pacientes`, `consultas`, `medicamentos`, `tipos_examen`, `resultados_examen`) con validaciones/índices iniciales. `db/firebase/firebase.json` inicia el emulador y su UI, pero **no** define aún colecciones odontológicas ni semillas. Los adaptadores `mongo_adapter.py` y `firestore_adapter.py` únicamente comprueban conexión. El backend solo tiene API de salud en `main` auditado.

**Lo que NO debemos hacer:** sustituir el backend de Pablo, implementar autenticación propia en React o Firebase Auth, modificar las tablas SQL de B, copiar directamente lógica de `ObjectId` al frontend, crear un selector de institución que modifique el repositorio del usuario, usar pacientes reales o trabajar contra Firebase en nube sin autorización. Los usuarios MongoDB iniciales son parte del esquema existente; la fuente de autenticación de la aplicación debe decidirse con B (`D0-01/02`), para no duplicar credenciales.

## 1. Diez reglas no negociables del agente A

1. **Verificar rama, SHA, estado, código actual y contrato antes de editar** (`git status`, lectura de archivos). No sobrescribir cambios de Pablo ni reemplazar el proyecto con scaffolding genérico.
2. **No inventar contrato API ni repositorio.** Las propuestas `CONTRACT-API-01` (10 operaciones) y `CONTRACT-REPO-01` (8 métodos) se ratifican en C0; luego cumplir su versión exacta.
3. **No tocar zona B**: `domain/**`, `application/**`, `presentation/**`, `backend/config/**`, `db/postgres/**`, `db/mysql/**`, `postgres_adapter.py`, `mysql_adapter.py`, `factory.py` salvo autorización explícita por PR asignado.
4. **No modificar `main` directamente.** Trabajar con rama corta `feature/jenni-*`, un PR por tarea y revisión cruzada de Pablo. Jamás `push --force` sobre `main`.
5. **Ejecutar pruebas antes del PR y registrar salidas verdaderas.** No anunciar que `npm run lint` o Vitest pasó cuando aún no existen esos scripts.
6. **Nunca subir `.env`, credenciales ni datos clínicos reales.** Todos los ejemplos deben ser ficticios `DEMO-*`; no mostrar contraseñas ni tokens en screenshots.
7. **No cambiar rutas, IDs, nombres de error o slugs ratificados.** Cualquier cambio incompatible se propone en `contract/*` y requiere Pablo + Jennifer.
8. **No “arreglar” el backend de Pablo sin handoff.** Reportar caso reproducible; usar mock temporal claramente etiquetado para seguir desarrollando UI.
9. **Mantener convenciones simples y consistentes:** Python alineado al proyecto; React con componentes y servicios claros; español técnico natural; no agregar librerías/patrones gratuitos.
10. **Escalar dependencias faltantes.** Si no está el login, fixture o endpoint, documentar `blocked-by-pablo` y continuar subtarea propia que no mienta sobre integración.

## 2. Zonas reservadas y propiedad de escritura

| A SÍ puede editar | B SÍ puede editar / A NO | Compartidos (un dueño por PR, acuerdo previo) |
|---|---|---|
| `frontend/**` | `backend/apps/historiales/domain/**` | `docker-compose.yml`, `.env.example` |
| `db/mongo/**` | `backend/apps/historiales/application/**` | `.gitignore`, `.github/**` |
| `db/firebase/**` | `backend/apps/historiales/presentation/**` | `README.md`, `CONTRIBUTING.md` |
| `backend/apps/historiales/infrastructure/adapters/mongo_adapter.py` | `backend/config/**`, `infrastructure/factory.py` | `PLAN_MAESTRO.md`, guías de agentes |
| `backend/apps/historiales/infrastructure/adapters/firestore_adapter.py` | `db/postgres/**`, `db/mysql/**` | Pruebas de contrato comunes (propietario temporal por PR) |
| Nuevos tests NoSQL (`test_*_nosql.py`) en `backend/apps/historiales/` | `postgres_adapter.py`, `mysql_adapter.py`, pruebas SQL/auth | Scripts de arranque/migración compartidos |

**⚠️ requiere acuerdo A↔B:** habilitar replica set MongoDB modificando Compose; añadir mecanismo de persistencia/exportación a Firestore vía Compose; revisar autenticación alojada en SQLite; proponer nuevos endpoints de especialización; editar el contrato REPO; modificar tests de contrato comunes. Regla: **solicitar cambio** y reservar PR, no editar compartidos simultáneamente.

## 3. Configuración inicial: primer día en la misma base que Pablo

### 3.1 Qué entregamos primero — PR-00 documental

Jennifer prepara `docs/plan-operativo` con **solo** `PLAN_MAESTRO.md`, `GUIA_PABLO_AGENTES.md` y `GUIA_JENNIFER_AGENTES.md` en la raíz del repositorio; Pablo revisa antes del merge. Este es `PR-00` del plan, **no** un número GitHub ya existente.

```powershell
# En un clon limpio en la raíz del repositorio:
git fetch origin
git switch main
git pull --ff-only origin main
git switch -c docs/plan-operativo
# Copiar los 3 archivos .md descargados a la raíz (sin reemplazar otros trabajos).
git add PLAN_MAESTRO.md GUIA_PABLO_AGENTES.md GUIA_JENNIFER_AGENTES.md
git diff --cached --stat
git diff --cached --check
git commit -m "docs: definir plan maestro y guias de agentes"
git push -u origin docs/plan-operativo
# En GitHub crear PR contra main y solicitar revisión a Pablo.
```

No intentar `git add` hasta colocar realmente los tres archivos en la raíz. No agregar `.env` ni `backend/db.sqlite3` por error. Cuando B apruebe PR-00 y se fusione, ambos sincronizan `main` y registran el **mismo SHA posterior**.

### 3.2 Preparar Docker local sin borrar información

```powershell
# Si no has clonado, hacerlo una vez:
git clone https://github.com/PabloZ7-425/Red_Instituciones_Medicas.git
cd Red_Instituciones_Medicas

# Si ya tienes repo local: ejecutar desde la carpeta del repositorio
git fetch origin
git switch main
git pull --ff-only origin main
git rev-parse HEAD
git status --short

# Solo crear .env si no existe:
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
notepad .env
# Reemplazar los valores 'cambiar_*' por claves locales. Nunca subir .env.

# Iniciar Docker Desktop y esperar Engine running:
docker compose config -q
docker compose up --build -d
docker compose ps -a
curl.exe -f http://localhost:8000/api/health/
curl.exe -f http://localhost:8000/api/health/databases/
docker compose exec -T backend python manage.py check
docker compose exec -T backend python manage.py test apps.historiales
docker compose exec -T frontend npm run build
```

**Verificación visual:** React `http://localhost:5173`, datos de BD `/api/health/databases/`, Firebase UI `http://localhost:4000`, Adminer `http://localhost:8081`. Firestore REST del emulador está en `localhost:8082` visto desde el **host**, pero en el contenedor Django se usa `firestore:8080`. MongoDB local `127.0.0.1:27017`; no asumir que acepta transacciones multidocumento.

**Importante:** `docker compose up --build -d` no debe borrar datos de volúmenes existentes. Los scripts `init.sql` no vuelven a ejecutarse en bases con volúmenes poblados. **No usar** `docker compose down -v`, `docker volume prune` ni reconstrucciones destructivas sin acuerdo explícito y respaldo. `README.md` menciona `hc_mongo_init`, pero Compose auditado no lo contiene: no perseguir ese servicio ficticio.

### 3.3 Reporte mínimo que compartes con Pablo

```text
Entorno A — Jennifer
SHA main (después de PR-00): <valor real de git rev-parse HEAD>
Docker config: OK / ERROR (detalle redactado)
Contenedores: 7 servicios principales + Adminer según Compose / error
/api/health/: OK / ERROR
/api/health/databases/: hospital ?, pediatrico ?, laboratorio ?, odontologica ?
Django check + tests: OK / ERROR
Frontend npm run build: OK / ERROR
Bloqueos abiertos: issue(s) o ninguno
Sin secretos adjuntos.
```

La cantidad final de servicios debe tomarse de `docker compose ps -a`; nunca afirmar un conteo fijo solo porque el documento lo sugiere.

## 4. Entregables, contratos y dependencias cruzadas

### 4.1 Qué recibe A de B

| Entregable de Pablo | Dependencia A | Punto de control | Riesgo si falta |
|---|---|---|---|
| `CONTRACT-API-01@1.0`: API-01..10, JSON, errores y status | Todo `frontend/src/api/**` y formularios | Ejemplos válidos e inválidos aprobados | Formularios incompatibles, reescritura. |
| `CONTRACT-REPO-01@1.0`: 8 métodos y errores | `mongo_adapter.py`/`firestore_adapter.py` | Firma revisada y suite común disponible | Adaptadores imposibles de integrar. |
| `D0-01/02/03` auth y roles | Login y estados autenticado/denegado | Flujo login y `/me` verificable | Login visual que no autentica de verdad. |
| Enrutamiento por sesión | Pruebas NoSQL / llamadas UI | Nunca hay motor seleccionable libremente | Datos cruzados. |
| Endpoint clínico + fixtures API | Integración React real | JSON coincide con mocks, pruebas API | Pantallas detenidas. |
| Autorización de especializaciones | Campos UI por institución | Contrato adicional acordado | UI solicita rutas inexistentes. |

### 4.2 Qué entrega A a B

| Entregable de Jennifer | Lo usa Pablo para | Evidencia |
|---|---|---|
| Ejemplos de JSON compatibles con React, ID externo `string`, fechas | Ratificar `D0-05` y DTOs | Capturas JSON/fixtures sintéticos y tests. |
| Modelo MongoDB documentado | Comparativo, lógica de consultas | Colecciones, validaciones, índices y relaciones. |
| Modelo Firestore documentado | Comparativo, consistencia | Colecciones/subcolecciones/referencias y reglas. |
| Adaptadores NoSQL probados contra puerto | Integración API y pruebas de contrato | Resultados de tests con errores negativos. |
| UI con mocks fieles al contrato | Verificar que API responde lo que usa la UI | Lista de pantallas y fixtures sin API falsa encubierta. |
| Incidencias de contrato reproducibles | Corregir DRF/puerto sin adivinar | Método, endpoint, payload DEMO, esperado/actual. |

## 5. Decisiones F0 que te corresponde revisar de verdad

No basta responder “me parece bien”; como célula A debes validar la compatibilidad documental y visual antes de aprobar los contratos.

- `D0-01`: ¿cómo autenticará React? ¿token, cookie/CSRF, expiración y salida? Nada de crear auth paralela.
- `D0-02`: ¿dónde guardará Django el directorio técnico de usuarios? Cualquier cambio de esquema o SQLite lo gestiona B. A exige que no haya selección arbitraria de institución.
- `D0-03`: ¿qué acciones se permiten a personal clínico, recepción y admin? ¿Cómo se expresan roles de laboratorio y odontología?
- `D0-04`: ¿son utilizables los 10 endpoints, errores y paginación desde React? ¿Qué pasa con pacientes archivados?
- `D0-05`: ID siempre string al exterior; `YYYY-MM-DD` para fecha y timestamp UTC ISO-8601 `Z`; establecer si el frontend localiza a horario Guatemala.
- `D0-06` (**lidera A**): pacientes con datos de contacto pequeños embebidos; exámenes crecientes en colección separada; procedimientos y registros con consultas adecuadas. Documentar decisión, no copiar el modelo SQL tal cual.
- `D0-07`: qué caso necesita transacción multidocumento y cuándo es atómica una sola escritura.
- `D0-08` (**lidera A**): Firestore seed y export/import en entorno local; sin asumir persistencia automática a través de cualquier reinicio.
- `D0-09`: `npm run build` existe; no existe `npm run lint` ni `npm test` hoy. Acordar si se agrega Node test runner/ESLint después sin ralentizar F0.
- `D0-10`: requerimientos especializados y diagrama/retroalimentación Entrega I. Si no están en repositorio, pedirlos a coordinadores, sin inventar su contenido.

### 5.1 Gate F0: once verificaciones con Pablo

- [ ] `G0-01` SHA compartido y `main` actualizado después de PR-00.
- [ ] `G0-02` `.env` local en ambos, sin versionar.
- [ ] `G0-03` Compose válido en ambos.
- [ ] `G0-04` Servicios principales iniciados en ambos.
- [ ] `G0-05` 4 BD reportan conexión en ambos.
- [ ] `G0-06` `check` y test Django baseline pasan en ambos.
- [ ] `G0-07` `npm run build` pasa en ambos.
- [ ] `G0-08` D0-01..05 ratificados.
- [ ] `G0-09` D0-06..10 ratificados.
- [ ] `G0-10` CONTRACT-API-01/REPO-01 @1.0 aprobados con fixtures/errores.
- [ ] `G0-11` PR-00 integrado; primera pareja de tareas y archivos reservados.

**Si falta un punto**, F0 queda abierto; A puede hacer investigación, diseño y mocks marcados “provisionales”, pero no afirmar adaptador conforme a contrato v1 ni abrir PR de funcionalidad que dependa de su versión definitiva.

## 6. Tareas A por ciclo — una tarea, una rama, un PR

Cada fila está diseñada para que un agente tome su propio trabajo sin invadir B. Los IDs de PR son **del plan**, los números reales de GitHub se registran al crearlos. Los archivos nuevos se indican explícitamente. Los hitos `F*.T*` se corresponden con el `PLAN_MAESTRO.md`.

| Ciclo / épica | Tarea / PR | Inputs y dependencias | Archivos de A | Output + aceptación verificable |
|---|---|---|---|---|
| `C0 · EPIC-00 · F0.T1` | **`A-C0-T1` — `PR-01`** revisión de contrato + mocks | PR-00; borrador B de API/REPO; D0-04/05 | `frontend/src/mocks/` (nuevo), `frontend/src/api/` **solo fixtures cliente**, docs compartidos solo con reserva | Mock paciente/historial/errores consistente con 10 operaciones; B acepta tipos y A aprueba puerto; build React pasa; **no construir API paralela**. |
| `C1 · EPIC-01 · F1.T1` | **`A-C1-T1` — `PR-03`** modelo odontológico Firestore | D0-06/08, casos odontológicos definidos | `db/firebase/**`, scripts demo A (nuevos) | Esquema de `pacientes`, `citas`, `consultas`, `procedimientos`, `recetas`, `pagos` donde corresponda; seed DEMO reproducible; justificación embebido/referencia; lectura por emulador demostrada. |
| `C2 · EPIC-01 · F1.T2` | **`A-C2-T1` — `PR-05`** completar MongoDB | `db/mongo/init.js` actual, CONTRACT-REPO-01, resultado examen variable | `db/mongo/**`, tests NoSQL A (nuevos) | Validadores/índices/fixtures para pacientes, consultas y exámenes; buscar por paciente/fecha; `campos` heterogéneos válidos; scripts idempotentes para datos DEMO. |
| `C3 · EPIC-02 · F2.T1` | **`A-C3-T1` — `PR-07`** adaptar MongoDB al puerto | C2, puertos aprobados, dataset DEMO | `.../adapters/mongo_adapter.py`, tests `test_*_nosql.py` (nuevo) | 8 métodos comunes funcionan; resultados/exámenes consultables; IDs string externos; manejo de inexistencia/duplicados; suite contrato pasa. |
| `C4 · EPIC-02 · F2.T2` | **`A-C4-T1` — `PR-09`** adaptar Firestore al puerto | C1 modelo, C3 pruebas de contrato, versión REPO v1 | `.../adapters/firestore_adapter.py`, tests NoSQL A (nuevo) | 8 métodos comunes, consultas por paciente, archivo lógico y relaciones odontológicas; datos accesibles tras seed; tests con emulador. |
| `C5 · EPIC-03 · F3.T1` | **`A-C5-T1` — `PR-11`** React con mocks | CONTRACT-API-01, mocks C0, estados UI | `frontend/src/**`, `frontend/package.json` si se justifica, tests UI A (nuevos) | Login visual, pacientes, registro, historial, consulta, diagnóstico, tratamiento, receta, archivo; estados loading/empty/error; build sin errores; etiquetar backend simulado. |
| `C6 · EPIC-03 · F3.T2` | **`A-C6-T1` — `PR-13`** integrar API real + especializaciones | B-C5-T1 endpoints y B-C6-T1 permisos/especializaciones según contrato | `frontend/src/api/**`, `frontend/src/pages/**`, `frontend/src/components/**`, tests UI A | Retirar mocks de flujo real; registro/lectura real 4 motores; vista específica de odontología/laboratorio cuando API lo permite; UI sin selector de motor; build + prueba manual guiada. |
| `C7 · EPIC-04 · F4.T1` | **`A-C7-T1` — `PR-15`** transacciones/auditoría NoSQL | Métodos estables, decisión D0-07 y autorización B | `db/mongo/**`, `db/firebase/**`, adaptadores NoSQL, tests NoSQL A | Atomicidad probada para operaciones compuestas; auditoría justificada sin datos sensibles innecesarios; caso de error intencional no deja inconsistencia. |
| `C8 · EPIC-04 · F4.T2` | **`A-C8-T1` — `PR-17`** recuperación y pruebas frontend | Aplicación integrada, fixtures DEMO | `db/mongo/**`, `db/firebase/**`, `frontend/**`, docs reservados | Recuperación Mongo y Firestore en entorno separado, rutas UI verificadas y errores mostrados sin datos sensibles; evidencia reproducible. |
| `C9 · EPIC-05 · F5.T1` | **`A-C9-T1` — `PR-19`** documentación final A | REQ-01..12, evidencias de fases, documentos B | Docs Mongo/Firestore/frontend reservados y correcciones solo A | Modelos NoSQL, embebidos/referencias, índices, consistencia, UI y evidencias verificadas; comparativo cotejado con B. |

### 6.1 Pasos exactos por tarea

#### `A-C0-T1` (PR-01): mocks y revisión de contrato

- [ ] Leer `PLAN_MAESTRO.md` §5 y el borrador de Pablo de `CONTRACT-API-01` y `CONTRACT-REPO-01`.
- [ ] Verificar `id` string, `identificacion` string, fecha ISO, estados de archivo, paginación y errores.
- [ ] Preparar datos sintéticos de **paciente**, **historial completo**, **login/me**, **lista paginada** y **errores** en `frontend/src/mocks/` **(directorio nuevo)**, separados del servicio HTTP real.
- [ ] Señalar a B un caso concreto de MongoDB y otro de Firestore que exija traducción de tipos/relaciones.
- [ ] No inventar campos solo para el frontend; solicitar cambio al contrato si uno es indispensable.
- [ ] Tras aprobación A↔B y merge del contrato en `PR-02`, terminar `PR-01`: actualizar fixtures al contrato ratificado, documentar qué era experimental y correr `npm run build`.

#### `A-C1-T1` (PR-03): Firestore desde cero, sin copiar MySQL

- [ ] Leer `db/firebase/firebase.json` y comprobar en emulador si existen colecciones. No afirmar que existen porque aparecen en este plan.
- [ ] Diseñar documentos `pacientes`; citas/consultas se referencian por paciente cuando puedan crecer sin límite; almacenar los campos de procedimientos por pieza dental donde se consulten.
- [ ] Definir representación común de receta/diagnóstico según REPO v1. Si odontología necesita campos extra, proponer extensión aislada, no cambiar la respuesta común.
- [ ] Decidir si procedimientos/recetas/pagos serán subcolecciones o colecciones; justificar patrones de consulta, borrado lógico, índices y límites. Evitar estructuras duplicadas innecesarias.
- [ ] Implementar **seed idempotente** de casos ficticios y procedimiento export/import para emulador; registrar comandos reales probados y mecanismo de persistencia acordado.
- [ ] Probar lectura después de reiniciar servicios **sin** destruir volúmenes de las otras bases. Si requiere Compose, levantar `⚠️ requiere acuerdo A↔B` antes del PR.

#### `A-C2-T1` (PR-05): MongoDB modelo del laboratorio

- [ ] Leer `db/mongo/init.js` actual: preservar sus seis colecciones y decisiones ya comentadas salvo evidencia de necesidad.
- [ ] `pacientes`: validar nombres/identificación/fecha/estado y datos de contacto pequeños; `consultas`: diagnósticos/recetas embebidos según el modelo que ya aparece; `resultados_examen`: documentos independientes por paciente.
- [ ] Para resultados variables, crear ejemplos de hematología, examen de orina y otro tipo con campos diferenciados; validar tipos, unidad/rango cuando aplique y estado.
- [ ] Revisar índices `{ identificacion: 1 }` único, búsquedas por paciente+fecha, `{ tipo_examen: 1 }`; justificar índices extra por consultas reales, no por cantidad.
- [ ] Crear tests positivos/negativos con documentos DEMO (fecha válida, estado inválido, duplicado, resultado sin campos).
- [ ] Mantener scripts idempotentes; no vaciar colecciones reales ni modificar URI de Mongo de B.

#### `A-C3-T1` y `A-C4-T1`: adaptadores NoSQL

- [ ] Leer código real del puerto **ratificado**; no implementar un puerto provisional diferente.
- [ ] Implementar alta, listado/paginación, lectura historial, consulta, diagnóstico, tratamiento, receta, archivo en cada adaptador.
- [ ] Traducir `ObjectId` Mongo y IDs Firestore a **strings**, sin devolver objeto Mongo a React. Convertir fechas en adaptador/serializador con criterio único.
- [ ] Usar filtros parametrizados/patrones seguros; validar pertenencia a paciente y estado antes de escribir.
- [ ] Mantener `health_check()` y liberar clientes/conexiones de forma apropiada. Gestionar errores de inexistencia, duplicado y estructura inválida sin exponer detalles internos.
- [ ] Probar 8 métodos con fixtures DEMO repetibles, borrado lógico y consultas en orden esperado. No sustituir SQLite/Django config.
- [ ] Si hace falta modificar `factory.py`, abrir `blocked-by-pablo` y proponer cambio con diff y test esperado, no tocarlo.

#### `A-C5-T1`: frontend profesional y mantenible

- [ ] Preservar `HomePage` de salud como pantalla técnica o mover su función mediante ruta/decisión; no borrar el diagnóstico útil.
- [ ] Implementar componentes de navegación, formularios, listas e historial; un patrón visual consistente entre instituciones.
- [ ] Centralizar solicitudes HTTP en `frontend/src/api/`; no usar fetch distinto y disperso en cada componente.
- [ ] Separar `mocks/` del servicio API real. Visualmente indicar modo demo/mock mientras no exista backend funcional.
- [ ] Validar entradas comunes (`identificacion` se maneja como cadena, no número), estados vacío, error, confirmación de archivo, loading y mensajes comprensibles.
- [ ] No incluir IDs `ObjectId` ni URLs de Firestore ni una elección editable de motor en formularios.
- [ ] Ejecutar build, probar navegación manual y documentar pantallas faltantes de especializaciones como dependencias de API.

#### `A-C6-T1`: integración real React ↔ Django

- [ ] Validar primero login y `/api/auth/me/`; asociar UX visible con la institución devuelta por la API, **no** con un selector arbitrario.
- [ ] Sustituir mocks por llamadas HTTP sin mezclar estructura de presentación con lógica de base de datos.
- [ ] Ejecutar alta, listado, consulta, diagnóstico, tratamiento, receta, lectura final y archivo contra los cuatro motores mediante la **misma UI**.
- [ ] Verificar token/cookie/CSRF según `D0-01`, no guardar credenciales en localStorage por intuición.
- [ ] Simular 400, 401, 403/404, 409 y caída del backend; mostrar errores seguros y recuperación razonable.
- [ ] Si un endpoint contradice contrato, abrir `contract-violation` y no construir workaround de producción que esconda la incompatibilidad.

#### `A-C7-T1`: consistencia, auditoría NoSQL

- [ ] Identificar operación compuesta real antes de usar transacción. En MongoDB las escrituras de documento son atómicas; transacción multidocumento requiere replica set (**Compose compartido**, revisar con B).
- [ ] En Firestore preferir transacción/batch según lectura-escritura y límites de emulador; no declarar consistencia eventual como propiedad universal.
- [ ] Probar fallo deliberado sin datos clínicos parciales, y que una excepción se traduzca a error controlado.
- [ ] Auditoría con usuario/acción/fecha/referencia, sin copiar historial sensible completo; si la lógica común de auditoría pertenece a B, pedir contrato/handoff en lugar de duplicarla.

#### `A-C8-T1`: recuperación + UI tests

- [ ] Realizar `mongodump` y restauración en entorno separado con datos DEMO. No ejecutar sobre una base compartida sin confirmar destino.
- [ ] Guardar/exportar e importar datos de emulador Firestore según la estrategia `D0-08`; verificar lectura posterior en emulador.
- [ ] Construir guion de UI: login, paciente nuevo, consulta, diagnóstico, tratamiento, receta, historial, archivo, acceso denegado.
- [ ] Repetir con laboratorio y odontología (también verificar que el diseño se adapta a hospital y pediatría con API B).
- [ ] Guardar resultados **reales** y registrar casos no comprobados explícitamente.

#### `A-C9-T1`: entrega

- [ ] Documentar qué se embebe y referencia en **MongoDB** y **Firestore** y por qué, con tamaño futuro y frecuencia de consulta.
- [ ] Resumir seguridad, integridad, recuperación, restricciones y decisiones de modelado de NoSQL con evidencia real.
- [ ] Actualizar pantallas y capturas de UI en una guía reproducible, sin datos reales.
- [ ] Revisar comparativo con el trabajo de Pablo, especialmente que los cuatro motores cumplen las mismas reglas clínicas.
- [ ] Marcar `REQ-01..12` conforme a pruebas y documentos; no marcar como listo un requisito sin evidencia.

## 7. Comandos exactos de pruebas para agentes A

### 7.1 Disponibles en el repositorio auditado

```powershell
# Desde raíz:
git status --short
git diff --check
docker compose config -q
docker compose ps -a
curl.exe -f http://localhost:8000/api/health/
curl.exe -f http://localhost:8000/api/health/databases/
docker compose exec -T backend python manage.py check
docker compose exec -T backend python manage.py test apps.historiales
docker compose exec -T frontend npm run build
```

Si se modifica únicamente `frontend/**`, sigue siendo recomendable ejecutar `npm run build` y consulta básica a API; si A modifica adaptadores NoSQL, es obligatorio correr suite de Django y prueba específica de motor añadida al PR. **No afirmar que ya existen** `npm run lint`, `npm test`, `pytest`, `ruff`, `black`, `prettier` o `vitest`. Si A propone agregar lint/test frontend, documentar versión, script, prueba y archivo lock en un PR separado o en el PR que introduce la primera prueba, con aprobación sobre dependencias.

### 7.2 Pruebas que A debe crear por fases

Los archivos siguientes son **nuevos sugeridos**, no rutas auditadas existentes:

- `backend/apps/historiales/test_mongo_nosql.py` — insertar/buscar, duplicados, documentos inválidos, historial/consulta, archivo y atomicidad cuando corresponda.
- `backend/apps/historiales/test_firestore_nosql.py` — emulador, seed, CRUD, estados, atomicidad, relaciones odontológicas.
- `frontend/tests/` (nuevo) — pruebas de transformación de API, validaciones y estados UI; definir runner en `D0-09` antes de exigirlo.
- `frontend/src/mocks/` (nuevo) — fixtures de contrato, **nunca** como fuente de datos productiva silenciosa.

| Tipo de prueba | Qué demostrar | Evidencia mínima |
|---|---|---|
| Mongo positivo | Laboratorio guarda paciente, consulta, examen variable e historial | JSON sintético esperado vs real |
| Mongo negativo | Identificación duplicada/estado inválido, error mapeado | Test fallando antes del arreglo y pasando después |
| Firestore positivo | Odontología guarda paciente, cita/consulta, procedimiento y receta | Documentos en emulador + respuesta del repositorio |
| Firestore negativo | Documento inválido, paciente inexistente, archivo | Validación y respuesta segura |
| React funcional | Login, pacientes, historial, mantenimiento, archivo | Guion manual o tests UI registrados |
| Cross-institution | Usuario laboratorio no consulta paciente de hospital | Rechazo backend, no solo ocultamiento UI |
| Recuperación | Export/import en destino demo | Identificadores y contenido permanecen coherentes |

**Para suites no existentes aún:** un agente debe escribir el archivo real, ejecutar el comando realmente soportado y anotar el resultado; **no inventar nombres de comandos puntuales**. `python manage.py test apps.historiales` puede descubrir nuevos módulos `test_*.py` del paquete. Evitar borrar/rescribir `backend/apps/historiales/tests.py`, cuya propiedad es B.

## 8. Protocolo de bloqueos A↔B: qué hacer exactamente

| Bloqueo | Acción de Jennifer/A | Puede continuar con | Prohibido |
|---|---|---|---|
| `CONTRACT-API-01` no aprobado | En issue `blocked-by-pablo` anotar operación, campo y fecha, pedir ejemplo JSON + status + auth | Diseño UI con **mock provisional marcado** | Fijar endpoint inventado y declararlo final. |
| `CONTRACT-REPO-01` incompleto | En issue `blocked-by-pablo` citar método y tipo faltante, proponer firma | Diseño documental y validador independiente | Modificar `domain/ports.py` por cuenta propia. |
| Falta fixture de auth | Solicitar a B cuenta DEMO por institución o método seguro de seed, sin contraseñas públicas | Formularios React sin envío real | Inventar JWT o poner credenciales hardcoded. |
| Falla un test común escrito por B | Abrir issue `contract-violation` con entrada DEMO, salida esperada/real, SHA, comando, sin PII | Investigar adapter A y reproducir | Cambiar la prueba o contrato para esconder bug. |
| Error en endpoint DRF | Reproducción HTTP, abrir `contract-violation` asignado a B; PR frontend draft | UX del estado error y mocks explícitos | Editar `presentation/views.py` de B. |
| Necesitamos cambio de Compose (replica set/Firestore seed) | Crear issue `blocked-by-pablo`, acordar dueño y ventana de PR compartido | Script dentro `db/mongo` o `db/firebase` | Dos ramas modificando Compose simultáneamente. |
| Firestore sin datos tras reinicio | Documentar estrategia `D0-08` y seed A reproducible; pedir Compose si necesario | Validador/fixtures | `down -v` destructivo sin consentimiento. |
| UI necesita endpoint especializado | Describir operación y ejemplo de UI, abrir propuesta `contract/*` mediante B y A | Componentes visuales con mocks etiquetados | Consumir ruta inexistente y declarar integración completa. |
| A recibe issue `blocked-by-jennifer` de B | Confirmar bloqueo, dar fixture/adapter/test o PR A que lo resuelva y SHA | Otras tareas A no bloqueadas | Obligar a B a editar NoSQL por urgencia. |

### Si otra célula rompe el contrato ratificado

1. **No cambiar el contrato ni código ajeno en secreto.** Congelar el merge del PR dependiente, moverlo a draft si hace falta.
2. Abrir issue con título `contract-violation: API-0N / <método>`; indicar `CONTRACT-API-01@1.0` o `CONTRACT-REPO-01@1.0`, versión y SHA.
3. Incluir input DEMO, pasos, esperado, observado, código de respuesta, test/comando; borrar tokens y datos sensibles.
4. Si el problema es de B, asignar a B; si es del adapter A, arreglar exclusivamente adaptador propio en PR A. No crear un wrapper oculto que convierta 500 en “correcto”.
5. Si la semántica necesita cambiar legítimamente, B propone PR `contract/*`, A revisa, y ambos actualizan pruebas, DTOs y mocks antes del merge.
6. Un `TODO(contract-violation: issue #...)` es admisible **solo** en rama draft/fixture, nunca para aprobar una funcionalidad incompleta.

## 9. Plantilla PR obligatoria — Célula A

**Título sugerido:** `[A-C4-T1] Firestore: implementar historial (CONTRACT-REPO-01)`.

```markdown
## Qué cambia
- ...

## Identificación
- Célula: A / Jennifer
- Ciclo/tarea: A-Cn-T1
- PR del plan: PR-XX (NO número GitHub)
- Épica/requisito: EPIC-0N / REQ-0N
- Dependencias de B: ninguna / enlace al PR/issue / blocked-by-pablo

## Contratos
- CONTRACT-API-01@1.0: sin cambios / propuesta contract/*
- CONTRACT-REPO-01@1.0: sin cambios / propuesta contract/*
- ¿Rompe contrato?: NO / SÍ (bloquear merge hasta acuerdo A↔B)

## Archivos tocados
- ruta → por qué es nuestra zona / acuerdo para compartido

## Cómo probar — comandos y salidas reales
- [ ] git diff --check
- [ ] docker compose config -q
- [ ] docker compose exec -T backend python manage.py check
- [ ] docker compose exec -T backend python manage.py test apps.historiales
- [ ] docker compose exec -T frontend npm run build
- [ ] Prueba concreta NoSQL/frontend: ...

## Evidencia
- DEMO positivo: ...
- DEMO negativo: ...
- SHA base: ...
- Logs/capturas redactadas: ...

## Seguridad y datos
- [ ] No hay credenciales ni datos médicos reales
- [ ] No se selecciona motor desde React
- [ ] No se borran datos/volúmenes ajenos
- [ ] Validaciones y errores documentados

## Revisión y cierre
- [ ] Archivos solo A, o autorización explícita por compartido
- [ ] Fixture y contrato ratificados
- [ ] Pablo revisó si hay integración con backend
- [ ] Tests pasados o bloqueos declarados
- [ ] Sin TODO bloqueante antes del merge
```

No tratar el identificador `PR-13` como si GitHub hubiese asignado el número #13. Guardar enlace real de PR y SHA de merge en el registro de coordinación.

## 10. Ritual de coordinación y entrega desde Jennifer

### 10.1 Cómo revisar contratos y PR de Pablo

- [ ] Confirmar que la institución del usuario se deriva de auth y nunca de un parámetro manipulable.
- [ ] Verificar `id` string, fechas ISO, nombres de propiedades, reglas de pacientes archivados y respuestas de errores.
- [ ] Verificar que los métodos REPO se puedan implementar con Mongo y Firestore sin necesitar joins SQL.
- [ ] Confirmar que el PR B no cambió `mongo_adapter.py`, `firestore_adapter.py` ni `frontend/**` sin permiso.
- [ ] Si cambia puerto/DTO, exigir versión de contrato y pruebas actualizadas; no aprobar “después lo arreglamos”.

### 10.2 Handoff A → B

Enviar una entrega autocontenida, idealmente como comentario en PR/issue:

```text
Handoff A → B
Tarea: A-Cn-T1 / PR del plan: PR-XX
SHA / rama / PR real: ...
Contrato: CONTRACT-REPO-01@1.0 / CONTRACT-API-01@1.0
Qué está listo: ...
Qué NO está listo: ...
Ejemplo DEMO de entrada/salida: ...
Pruebas ejecutadas y resultados: ...
Qué necesita B integrar/probar: ...
Bloqueos o decisiones pendientes: ...
```

### 10.3 Si Pablo reporta `blocked-by-jennifer`

1. Reproducir caso y determinar si la dependencia es fixture, adaptador, modelo documental o interfaz de cliente.
2. No pedir que B cambie su implementación para esconder un error de nuestro motor.
3. Arreglar en rama A, escribir prueba positiva y negativa, enviar PR pequeño.
4. Devolver al issue SHA/PR real + comando/resultado + dato DEMO para desbloquearlo.
5. Solicitar confirmación de B de que la suite compartida pasa antes de cerrar.

### 10.4 Cierre de cada ciclo

- [ ] El trabajo `A-Cn-T1` está fusionado o su bloqueo tiene issue reproducible.
- [ ] B confirma que el `B-Cn-T1` cumple lo acordado.
- [ ] No hay dos PR tocando un compartido.
- [ ] Builds/tests de ambos pasan; cualquier prueba no ejecutada está explicada.
- [ ] El estado `REQ-*` se actualiza con evidencia, no por intuición.
- [ ] Ambos vuelven a la nueva `main` y comparten SHA.

## 11. Convenciones técnicas que evitan retrabajo

### Frontend

- Usar componentes React reutilizables y servicios HTTP concentrados en `frontend/src/api/`. Mantener `frontend/src/pages/` para páginas y `frontend/src/components/` para UI; rutas adicionales solo según contrato/aprobación.
- Estados de carga, errores de red, autorización, formularios inválidos y datos vacíos son obligatorios para no simular éxito.
- `id` es string en UI; `identificacion` conserva ceros y formato. Fechas sin hora en `YYYY-MM-DD`, timestamps UTC ISO `Z` y presentación local Guatemala.
- Mantener una interfaz visual coherente entre 4 instituciones; componentes especializados solo cuando cambian datos/formularios clínicos.
- No introducir React Router, Axios, Tailwind, UI kits, ESLint o Vitest por impulso; proponerlos si reducen complejidad y aprobar dependencias con PR. El stack actual usa `fetch` simple y React+Vite.
- No almacenar contraseñas/tokens según intuición ni mostrar datos sensibles en almacenamiento/console; seguir mecanismo auth aprobado por B.

### MongoDB

- Mantener BSON/`ObjectId` **dentro** del adaptador; al exterior JSON con ID string.
- Consultas por paciente/fecha/tipo de examen justifican índices; evitar índices sin casos de consulta.
- Embebidos: datos pequeños y acotados leídos juntos; referencias: conjuntos de resultados de examen crecientes. Validación del esquema para estados e identificación.
- No suponer consistencia eventual como regla universal. Una escritura documental tiene atomicidad; multidocumento exige topología compatible.

### Firestore

- Solo emulador local durante desarrollo; sin credenciales de producción.
- Diseñar colecciones y referencias según acceso, límites y crecimiento; almacenar datos de odontología sin imitar relaciones SQL una a una.
- Definir seed y export/import; documentar índices requeridos si alguna consulta los necesita.
- La seguridad principal para las rutas clínicas la hace Django/B; el emulador no equivale a un entorno de producción seguro. No exponerlo en red pública.

### Prohibiciones y anti-patrones

- No editar SQL de Pablo porque “es más rápido”.
- No usar `.env.example` para poner contraseñas reales.
- No crear una segunda base/servidor para solucionar un problema de UI.
- No generar carpetas enormes sin caso de uso, ni microservicios en un proyecto hexagonal sencillo.
- No llenar la BD con historiales clínicos reales ni subir dump a Git.
- No borrar volumen para forzar scripts de inicialización; usar migración/seed controlado.
- No cambiar los slugs `hospital`, `pediatrico`, `laboratorio`, `odontologica` sin versión de contrato.
- No aprobar PR que solo pasa build pero carece de los tests clínicos requeridos.
- No fabricar capturas/resultados de pruebas.

## 12. Orden inmediato para Jennifer y este asistente

1. **Preparar PR-00** con los tres Markdown en raíz, sin otros archivos. Enviar a Pablo para revisión y merge (todavía **no** está creado desde esta guía).
2. Confirmar localmente el estado de Git (rama limpia, SHA) y Docker; ejecutar §3.2, anotar resultado real y compartir sin secretos.
3. **C0, A-C0-T1:** antes de programar Firestore, leer contrato que Pablo propone, señalar aspectos de NoSQL y crear mocks `frontend/src/mocks/` consistentes. No iniciar adaptadores clínicos sin `CONTRACT-REPO-01@1.0` ratificado.
4. Revisar los 11 ítems de F0 con Pablo. Registrar qué falta, quién lo resuelve y qué PR lo entrega.
5. C1: abrir `feature/jenni-c1-firestore-model` desde `main` sincronizada; implementar solo `db/firebase/**` salvo acuerdo de Compose.
6. Después C2→C4: Mongo, MongoAdapter, FirestoreAdapter. Mantener tests por motor y PR independientes.
7. En paralelo, crear frontend con mocks y comunicar a B cada campo extra **antes** de depender de un endpoint no aprobado.

**Regla de oro: PR pequeño y respetuoso del contrato > velocidad aparente.**


---

## Anexo operativo — ADR-ORM-01: frontera ORM / NoSQL / Frontend (agregado el 2026-10-20)

**Decisión tecnológica:** el equipo seguirá una persistencia híbrida. **Pablo/B** usará Django ORM únicamente para usuarios, autenticación, grupos, permisos, sesiones y administración interna; para historiales de PostgreSQL/MySQL usará **drivers nativos** (`psycopg` y `mysql-connector-python`). **Jennifer/A** seguirá con **PyMongo** para MongoDB y **SDK oficial de Firestore**; React consumirá la API REST sin detalles de persistencia. Jennifer aceptó la orientación; Pablo la ratifica con `D0-02` y `G0-08` antes de cambiar configuración de auth. Consultar el mismo `ADR-ORM-01` en `PLAN_MAESTRO.md`.

### Consecuencias concretas para los agentes de Jennifer

1. **No crear autenticación paralela** en MongoDB ni en Firestore. `db/mongo/init.js` incluye una colección `usuarios` heredada: **no usarla como fuente de credenciales del nuevo login** sin una decisión conjunta; no borrarla precipitadamente si existen referencias/datos. Tampoco introducir Firebase Auth ni una pantalla que permita escoger motor arbitrariamente.
2. **No tocar ORM ni migraciones Django:** `backend/config/settings.py`, modelos/usuarios Django, `AUTH_USER_MODEL`, `DATABASES`, `manage.py migrate` y el almacén central son responsabilidad de B. Si A necesita un rol o campo extra, pedirlo como cambio a `D0-01/03` o `CONTRACT-API-01` con ejemplo de JSON, sin editar código B.
3. **No introducir un ODM** (`mongoengine`, `djongo` u otros) para acceder a MongoDB ni intentar mapear Firestore con ORM Django. Usar `pymongo` y Firestore SDK tal como establece `PLAN_MAESTRO.md`; preservar los modelos y validaciones documentales que exige el profesor.
4. **React no sabe de motores:** los servicios de `frontend/src/api/**` trabajan con `CONTRACT-API-01@1.0`. `id` externo se mantiene `string`; conversiones internas de `ObjectId` o IDs Firestore se hacen en adaptadores. Los formularios muestran institución/rol autorizados devueltos por `/api/auth/me/`, no exponen ni infieren dónde se almacenan las tablas de identidad.
5. **Mocks primero, autenticación real después:** en `A-C0-T1` / `PR-01`, preparar fixtures sintéticos de login/`me` ajustados al contrato; en `A-C5-T1` / `PR-11`, UI funcional con mocks; en `A-C6-T1` / `PR-13`, integrar con endpoints reales de B. No inventar tokens, cookies, duraciones ni códigos de respuesta: dependen de `D0-01`.
6. **Cuando B no haya migrado identidad:** mantener las pantallas en modo mock identificado, notificar `blocked-by-pablo` si la integración real depende de su endpoint y continuar solo tareas propias que no necesiten auth final. Nunca apuntar React directamente a PostgreSQL, MongoDB o Firestore para saltarse el bloqueo.

### Verificación y revisión cruzada

- Al revisar `PR-02` de B, confirmar que `ADR-ORM-01` y `D0-02` delimitan inequívocamente ORM técnico frente a los cuatro repositorios clínicos, que no hay selector arbitrario de institución y que las respuestas JSON del login/`me` permiten construir la UI.
- Al revisar `PR-04`, exigir evidencia de permisos, persistencia de identidad y aislamiento institucional, sin intentar modificar las migraciones de B.
- Para PRs A (`PR-03/05/07/09/11/13`), mantener pruebas documentales y `npm run build` donde corresponda; no añadir dependencias ORM/ODM ni subir secretos/credenciales.
- Si un cambio de ubicación de auth rompe el contrato, registrar `contract-violation` y un caso reproducible; solicitar corrección a B por su PR, en lugar de cambiar silenciosamente el frontend o los adaptadores.

**Regla:** los adaptadores clínicos siguen independientes del directorio técnico de Django; la decisión sobre ORM no altera propiedad de archivos, ciclos C0–C9, formato de la API ni criterios de cumplimiento de la Entrega II.
