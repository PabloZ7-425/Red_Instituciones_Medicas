# Plan maestro — desarrollo autónomo por módulos

Versión operativa **2.0**, 2026-10-20. Base auditada: main
`f9e9f4c16429d3649c2467ee9e7d9552278e8667`. Responsables: Jennifer / A y Pablo / B.
Este documento es la especificación vigente; las dos guías lo aplican a cada célula.

## 1. Autoridad, auditoría y cambio de método

Prioridad: PDF del profesor → decisiones expresas del equipo → código y conducta
comprobados → planificación → recomendaciones. La nueva instrucción sustituye los
ciclos C0–C9, una rama por tarea y el gate global F0. No se exige aprobación de la
otra célula. Se conservan decisiones técnicas correctas y protecciones reales GitHub.

Fuente académica leída completa: **Proyecto final bases II (1) (1).pdf**, 4 páginas,
archivo local en Downloads. SHA-256:
`BAB63053189B0D776B8BD13488356EAA5E22D0AEC0E6BDA502ABF8424C10B382`.
Las referencias p. 1–4 corresponden a páginas físicas. No se copia el PDF al repo.
No se inventan plazos ni retroalimentación de Entrega I ausente en los materiales.

Se inspeccionaron configuración, fuentes backend/frontend, cuatro adaptadores,
esquemas, fixtures, pruebas, documentos, commits, ramas y PR. Firestore `fff235a`
y MongoDB `1a6c669` existen y son ancestros de main: están publicados/fusionados,
no requieren recuperación ni reimplementación. PR #1–#9 quedaron integrados.
Antes de esta reorganización solo existía main; §9 establece las dos ramas nuevas.

| Área | Implementado y publicado | Límite comprobado |
|---|---|---|
| Infraestructura | Siete servicios Compose y cuatro conexiones verificadas | Mongo standalone; Firestore emulador, sin entorno productivo |
| Backend | Salud, resultado False correcto; 12 pruebas | Solo raíz/salud; sin login ni CRUD clínico |
| Dominio | Paciente, instituciones, fábrica y puerto clínico de 4 métodos | No implementa las 8 firmas de §6 |
| PostgreSQL/MySQL | Esquemas extensos y 6+7 casos experimentales | DDL no aplicado a bases activas; adaptadores solo health_check |
| MongoDB | Seis colecciones, validadores/índices, 9 documentos DEMO y 7 pruebas | Sin repositorio clínico; seed standalone no atómico entre documentos |
| Firestore | 7 documentos DEMO, seed, exportación, 12 pruebas y recuperación | Sin repositorio clínico ni persistencia automática en Compose |
| React | Panel de conexiones y fixtures; 8 pruebas y build | Sin pantallas clínicas ni autenticación |

Las 39 pruebas y 13 casos SQL, build y recuperación registrados en
[ESTADO_INTEGRACION.md](ESTADO_INTEGRACION.md) son evidencia histórica de integración,
no una nueva ejecución integral en esta edición. El PR registra lo repetido ahora.

Contradicciones: SQLite está ignorado pero versionado; Firestore host usa 8082,
no 8080. hc_mongo existe y está healthy; hc_mongo_init no es servicio Compose.
frontend/tests ya existe. MongoAdapter tiene fallback con replicaSet=rs0 mientras
Compose lo sustituye por standalone: A2 alineará su URI cuando B prepare topología.

## 2. Requisitos y trazabilidad académica

El PDF evalúa sobre todo modelado, consistencia y seguridad; arquitectura hexagonal
es el mecanismo habilitador (p. 1). Conservar REQ-01..12; REQ-13 explicita el análisis
de Entrega I. Parcial no significa cumplimiento académico completo.

| ID | Referencia exacta / requisito | Módulos y motores | Estado / archivos | Prueba y evidencia de cierre | Entrega |
|---|---|---|---|---|---|
| REQ-01 | p. 1 contexto; p. 2 restricciones 1–2; p. 3 asignación: cuatro instituciones/motores sin repetir | A1/A2/B3/B4/B5, cuatro motores | Parcial: Compose/slugs | Conexiones y asignación justificada | I/II |
| REQ-02 | p. 1 hexagonal habilitadora; p. 3 aplicación funcional cliente-servidor | B1/B2/B5/A4, cuatro | Parcial: ports.py y HomePage.jsx | Flujo React → API → motor y lógica independiente del driver | II |
| REQ-03 | p. 2 ER, relacional, entidades/atributos, normalización; p. 3 implementación/correcciones | B3/B4, PostgreSQL/MySQL | Parcial: init.sql; diagramas/feedback no encontrados en Git | Diagramas, normalización, constraints y observaciones disponibles incorporadas | I/II |
| REQ-04 | p. 4 modelo documental y justificación de embebidos/referencias | A1/A2/A5, MongoDB/Firestore | Parcial: READMEs/fixtures | Modelos, crecimiento y consultas justifican elecciones; persistencia probada | II |
| REQ-05 | p. 4 consultas equivalentes en los cuatro motores | B1/B5/A3/B3/B4, cuatro | Pendiente: solo health_check | Misma suite contractual contra cuatro repositorios reales | II |
| REQ-06 | p. 4 generar nuevos historiales, paciente nuevo | A3/A4/B3/B4/B5, cuatro | Pendiente: JSON de ejemplo no es alta real | API-04/UI y lectura posterior, duplicados y aislamiento | II |
| REQ-07 | p. 3 reglas comunes; p. 4 consultas, diagnósticos, tratamientos, medicamentos recetados | A3/A4/B3/B4/B5, cuatro | Pendiente: esquemas/semillas preparatorios | API-05..09, cadena clínica persistida y datos existentes | II |
| REQ-08 | p. 4 desactivación/archivo por baja administrativa | A3/A4/B3/B4/B5, cuatro | Parcial: campos SQL | API-10 conserva historia/motivo/fecha, carreras y rollback | II |
| REQ-09 | p. 3 usuario/institución; p. 4 enrutamiento al autenticarse | B2/B5/A4, cuatro | Pendiente | Sesión/CSRF/permisos; cuentas de distintas instituciones; sin selector externo | II |
| REQ-10 | p. 4 información ordenada e interfaz uniforme | A4/A5, cuatro | Parcial: panel homogéneo de salud | Mismo flujo/componentes, carga/vacío/error y especializaciones | II |
| REQ-11 | p. 2 justificación; p. 4 comparativo de modelado, consistencia/transacciones y seguridad | B5 compila; A5 aporta sección propia, cuatro | Pendiente documento final | Comparativo breve con evidencia de cada motor y asignación | II |
| REQ-12 | p. 2 información pública, confidencial y restringida | A5/B5, cuatro | Pendiente matriz final | Matriz por dato y control aplicable | I/II |
| REQ-13 | p. 2 análisis completo, pacientes existentes/nuevos, cuatro instituciones, operaciones en lenguaje sencillo | A5/B5, cuatro | Parcial: modelos existentes | Entidades, atributos y operaciones trazados al flujo | I |

El contexto p. 1 requiere justificar atención hospitalaria estricta, odontología
ágil, resultados variables y seguimiento pediátrico. Tutores, vacunas/crecimiento y
exámenes/resultados evidencian esos casos. Ingreso/cama/alta, citas y procedimientos
se completan donde el modelo y demostración lo necesiten. Pagos reales, pasarelas,
HA, microservicios y despliegue público no son requisitos del PDF. Auditoría,
backups y lint son mejoras justificadas que no desplazan las operaciones obligatorias.

| Institución / slug estable | Motor / dueño | Justificación inicial para desarrollar en comparativo |
|---|---|---|
| Hospital / hospital | PostgreSQL 16 / B | Integridad relacional y transacciones estrictas |
| Pediatría / pediatrico | MySQL 8.4 InnoDB / B | Seguimiento longitudinal relacionado y restricciones |
| Laboratorio / laboratorio | MongoDB 7 / A | Resultados variables y referencias para conjuntos crecientes |
| Odontología / odontologica | Firestore / A | Operaciones documentales simples y gestión técnica reducida; UI ágil común |

SQLite/Realm/LiteDB no sirven como motores institucionales (PDF p. 2). B2 usará
PostgreSQL técnico para identidad, separado de hospital: no quinta institución ni
nuevo motor asignado. Migrar usuarios existentes con inventario, respaldo y reversión.

## 3. Arquitectura y decisiones operativas

React → DRF → identidad/permisos → casos de uso → puertos → adaptador institucional.
Institución desde principal autenticado, nunca desde selector de motor del navegador.
Dominio/aplicación no importan drivers; vistas no ejecutan SQL.

- ORM Django solo para User, perfil institucional/profesional, roles, sesiones y admin.
  Conservar inicialmente User estándar; evitar cambios tardíos de AUTH_USER_MODEL.
- Datos clínicos SQL con psycopg/mysql-connector-python, parámetros y transacciones
  explícitas. No modelos ORM clínicos ni managed=False como atajo general.
- PyMongo y SDK oficial Firestore; sin ODM ni Firebase Auth paralelo.
- Sesión Django + CSRF: sessionid HttpOnly, csrftoken; sin token en localStorage.
  Máximo 8 horas desde login y cookie expira al cerrar navegador; logout invalida.
- Identidad en base PostgreSQL técnica separada con privilegios específicos. Revisar
  migrate automático de Compose antes de cambiar DATABASES; no borrar usuarios.
- Escritura/archivo SQL bloquean paciente raíz en la misma transacción. Mongo con
  documentos separados usa replica set y modificación condicional de raíz en la
  transacción; lectura snapshot sola no impide la carrera. Firestore lee paciente
  en la transacción de escritura y archivo modifica ese documento.
- B es dueño de Compose: preparará replica set de un nodo con datos preservados.
  A prepara scripts/pruebas en su zona; solo los casos transaccionales reales de
  A3 dependen de esa capacidad, no sus otros módulos.

## 4. Módulos completos y aceptación

Cada módulo incluye diseñar, implementar, probar, documentar y publicar. Un PR
entrega un módulo coherente; avances parciales se declaran parciales.

| Módulo | Dueño y entrega demostrable | Base existente y aceptación final |
|---|---|---|
| A1 Persistencia Firestore | Modelo odontológico, colecciones/relaciones, validación, seed y documentación | Reutilizar 7 documentos/12 pruebas; justificar diseño y fecha civil, mapeo de ocurrencias y recuperación sin seed en destino |
| A2 Persistencia MongoDB | Laboratorio, validadores/índices, exámenes/resultados variables, DEMO y consistencia | Reutilizar 9 documentos/7 pruebas; justificar crecimiento/consultas, alinear fallback URI; invalidación/duplicado/conflicto sin sobrescritura |
| A3 Adaptadores NoSQL | Ocho métodos y catálogo Mongo/Firestore contra §5–6 | Hoy solo salud. Suite real común, errores/IDs, aislamiento, rollback y carreras archivo/escritura |
| A4 React | Login, pacientes, historial/consulta/diagnóstico/tratamiento/receta/archivo, especializaciones y estados UI | Reutilizar mocks/panel/8 pruebas; avanzar sin API mediante mocks explícitos; cierre con API real, cuatro instituciones, accesibilidad y build |
| A5 Calidad y evidencia A | E2E, seguridad cliente, consistencia/recuperación NoSQL, documentos académicos | Reutilizar recuperación Firestore; completar evidencia, clasificación y sección comparativa A |
| B1 Contratos y núcleo | Entidades, tipos, ocho puertos, errores/contexto, casos de uso, fábrica y suite compartida | Especificación 1.0.0 aquí; consolidar puerto real 4→8 y catálogo, probar sin bases/UI con dobles |
| B2 Identidad y acceso | ORM técnico, login/me/csrf/logout, perfil/rol/sesión y autorización | Sin login actual. Hashing/expiración/CSRF, 401/403/404, aislamiento y migración técnica reversible probados |
| B3 PostgreSQL hospital | Modelo corregido, fecha explícita, persistencia hospitalaria y transacciones | Reutilizar init.sql y 6 experimentos; migración incremental, ocho métodos/catálogo, integridad/rollback y especialización necesaria |
| B4 MySQL pediatría | Modelo pediátrico, tutores/vacunas/crecimiento y persistencia transaccional | Reutilizar init.sql y 7 experimentos; cita nullable/ocurrencia diagnóstica, ocho métodos/catálogo, FKs y rollback sin perder historia |
| B5 API y calidad central | DRF/casos de uso, validación, errores, autorización, integración y documentos centrales | Sin CRUD actual. §5 operativo, cuatro adaptadores reales, fallos seguros y comparativo compilado con aportes A5 |

Orden B recomendado: B1 → B2 → B3 → B4 → B5; casos de uso/API se prueban con dobles
mientras se completan motores. A cierra lo reutilizable A1/A2 y elige A3 o A4 según
capacidad disponible; A4 puede avanzar con mocks antes de API real. Un solo módulo
publicable por rama a la vez; no mezclar otro trabajo en el PR pendiente.
Dependencias reales: runtime/suite B1 para certificar A3, B2/B5 para E2E A4 y replica
set para transacciones Mongo. No impiden modelos, semillas, UI ni pruebas propias.

## 5. CONTRACT-API-01@1.0.0 — especificación del nuevo flujo

**Normativa desde esta reorganización; implementación pendiente.** Integra los
candidatos de docs/pablo/fase0, que pasan a antecedentes. No exige otra ronda de
aprobación para comenzar. Plan operativo 2.0 no significa API 2.0. B1 materializa
esta especificación en código/pruebas; A puede consumirla desde ahora.

### 5.1 DTOs y formato

JSON UTF-8; IDs opacos string no vacíos; identificacion string. Slugs de §2.
Fechas civiles YYYY-MM-DD, válidas y no futuras en nacimiento/consulta. Timestamps
UTC ISO-8601 con Z. No convertir fechas civiles a medianoche UTC en React. Archivo
usa fecha civil America/Guatemala, según columnas DATE. Sin motores, drivers, SQL,
contraseñas o referencias SDK en respuestas clínicas.

Trim en textos salvo password, que se preserva exactamente. Obligatorios no vacíos
ni null. Opcionales se omiten; null solo en lectura indicada. Rechazar campos
desconocidos, motor/institucion/usuario_id/medico_id e IDs generados en cuerpos.
Query desconocida/repetida: 400. La institución no se recibe del cliente clínico.

El cuerpo de una escritura debe ser objeto JSON, no lista/escalar. En respuestas
paginadas count es entero >=0, limit/offset son enteros y results es array. Los
DTO de lectura conservan los campos de creación y añaden los indicados; Login no
devuelve password y Archivo se proyecta como Paciente, no repite el campo motivo.
usuario.rol es uno de los cinco roles de §5.3; usuario.institucion es un slug de §2.

| DTO entrada | Campos | Salida adicional |
|---|---|---|
| Login | username y password strings no vacíos | {usuario:{id,username,rol,institucion}}; sesión por cookie |
| PacienteCreate | identificacion 1..20; nombres/apellidos 1..100; fecha_nacimiento | id, estado activo/inactivo/archivado, motivo_archivo/fecha_archivo null hasta archivo |
| ConsultaCreate | fecha; notas_evolucion 1..5000; cita_id string opcional | id, paciente_id; cita_id null si no existe |
| DiagnosticoCreate | codigo_cie10 1..20; descripcion 1..5000 | id de ocurrencia, consulta_id |
| TratamientoCreate | indicaciones_generales 1..5000 | id, diagnostico_id de ocurrencia |
| RecetaCreate | medicamento_id string; dosis/frecuencia 1..100; via_administracion 1..100 opcional | id, tratamiento_id; via_administracion null si omitida |
| Archivo | estado literal archivado; motivo 1..200 | Paciente con motivo/fecha de archivo; conserva identidad/historia |

MySQL: ID diagnóstico externo = consulta_diagnostico.id, no catálogo diagnostico.id;
tratamiento referencia esa ocurrencia y consulta. Receta externa = detalle_receta.id,
tratamiento desde cabecera. PostgreSQL usa diagnostico.id por ocurrencia. A genera
identidades equivalentes NoSQL. Consulta obtiene profesional habilitado del principal,
nunca un médico elegido arbitrariamente en el body. Mapeos de columnas en adaptadores.

### 5.2 Operaciones y extensiones

| ID | HTTP / ruta | Entrada | Éxito | Ejemplo negativo |
|---|---|---|---|---|
| API-01 | POST /api/auth/login/ | Login + CSRF | 200 {usuario}, sesión rotada | credenciales inválidas: 401 UNAUTHORIZED uniforme |
| API-02 | GET /api/auth/me/ | sesión | 200 {usuario} | sin sesión: 401 |
| API-03 | GET /api/pacientes/ | q/limit/offset opcionales | 200 {count,limit,offset,results:[Paciente]} | limit=0: 400 |
| API-04 | POST /api/pacientes/ | PacienteCreate | 201 Paciente | identificación vacía: 400; duplicada institucional: 409 |
| API-05 | GET /api/pacientes/{id}/historial/ | id paciente | 200 {paciente,consultas} | ausente/ajeno: mismo 404 |
| API-06 | POST /api/pacientes/{id}/consultas/ | ConsultaCreate | 201 Consulta | fecha 2026-02-30: 400; archivado: 409 |
| API-07 | POST /api/consultas/{id}/diagnosticos/ | DiagnosticoCreate | 201 Diagnostico | descripción vacía: 400; padre ajeno: 404 |
| API-08 | POST /api/diagnosticos/{id}/tratamientos/ | TratamientoCreate | 201 Tratamiento | indicaciones vacías: 400; ocurrencia ausente: 404 |
| API-09 | POST /api/tratamientos/{id}/recetas/ | RecetaCreate | 201 Receta | dosis vacía: 400; medicamento ausente/ajeno: 404 |
| API-10 | PATCH /api/pacientes/{id}/estado/ | Archivo | 200 Paciente archivado | motivo vacío: 400; distinto motivo tras archivo: 409 |
| AUTH-CSRF | GET /api/auth/csrf/ | anónimo permitido | 200 {csrfToken:string} y cookie csrftoken | no necesita identidad clínica |
| AUTH-LOGOUT | POST /api/auth/logout/ | sesión + CSRF | 204 sin cuerpo; invalida sesión | sin sesión: 401; CSRF incorrecto: 403 |
| CAT-01 | GET /api/medicamentos/ | sesión + q/limit/offset | 200 {count,limit,offset,results:[{id,nombre,presentacion}]} | rol insuficiente: 403; query inválida: 400 |

Las tres extensiones no se cuentan entre las diez operaciones iniciales. Catálogo:
presentacion string o null, nombre proyectado de cada esquema, solo habilitados;
si no existe columna estado, el catálogo existente se considera habilitado sin
inventar estado persistido. UI consume IDs retornados, no alias DEMO sin resolver.

Historial: consultas → diagnosticos → tratamientos → recetas anidados, con DTOs
y padres. Vacíos = []. Consulta por fecha e id string ascendentes; hijos por id
string ascendente. No truncado silencioso; paginar historia requiere evolución
contractual. Los estados de lectura conservan inactivo heredado; creación es activo.

### 5.3 Búsqueda, sesión y permisos

limit entero 1..100 (20); offset entero >=0 (0). q opcional, máximo 100 caracteres
tras trim + Unicode NFC + lower; campos con misma normalización. Prefijo literal
de identificación/nombres/apellidos por OR, sin subcadena, regex ni comodines.
No quitar acentos. q vacío = sin filtro; %/_ se escapan como literales en SQL.
pac coincide con Paciente, aci no; DEMO- coincide con DEMO-0001. Count antes de
paginar. Orden de pacientes por identificación original e id como cadenas; adaptar
colaciones si difieren. Incluye inactivos/archivados. Catálogo aplica prefijo en
nombre y ordena por nombre normalizado e id. No snapshot entre solicitudes de páginas.

React: credentials: include y X-CSRFToken en escrituras. Pedir AUTH-CSRF al entrar
y después de login, que rota el secreto Django. Login anónimo también exige CSRF.
CORS/CSRF solo origen de desarrollo localhost:5173 y mismo hostname. Cookies Secure
cuando se use HTTPS. B2 implementa 401 deliberadamente: SessionAuthentication sola
puede producir 403 y no satisface el contrato. Inactivo o sin perfil/institución
válida no accede. Superusuario técnico no salta aislamiento clínico.

| Operación | admin | medico | secretaria | enfermero | laboratorista (solo laboratorio) |
|---|---|---|---|---|---|
| API-02/03 | Sí | Sí | Sí | Sí | Sí |
| API-04 | Sí | Sí | Sí | No | Sí |
| API-05 | Sí | Sí | No | Sí | Sí |
| API-06 | Sí* | Sí* | No | No | Sí* |
| API-07/08/09 | Sí* | Sí* | No | No | No |
| API-10 | Sí | No | No | No | No |
| CAT-01 | Sí | Sí | No | No | No |

*Vínculo profesional habilitado obligatorio; admin no concede prescripción por sí
solo. Laboratorista registra atención/resultados, no diagnóstico clínico ni receta.
Para demostrar el flujo común en cuatro motores, cuentas medico/admin habilitadas
por institución. Etiqueta visible odontólogo no crea rol contractual nuevo.
Especializaciones definen extensiones/DTO/permisos sin modificar rutas ajenas.
API-02..10/CAT-01 requieren sesión. Rol insuficiente: 403 antes de buscar recurso;
con permiso pero padre ajeno/ausente: mismo 404. Identidad institucional solo de sesión.

### 5.4 Archivo, errores y ejemplos

Duplicados de identificación se evalúan por institución. API-06..09 exigen activo
bajo exclusión atómica. Archivo preserva hijos; mismo motivo repetido conserva
fecha y devuelve 200, otro motivo 409. Inactivo/archivado rechaza nuevas escrituras
clínicas y especializadas. Escritura confirmada antes del archivo se conserva;
después del commit de archivo no puede confirmar otra. No reactivación en v1.
Cita ausente/ajena 404; cita de otro paciente/profesional o consumida 409.

```json
{"error":{"code":"VALIDATION_ERROR","message":"Datos inválidos","fields":{"identificacion":["Este campo es obligatorio"]}}}
```

fields siempre objeto, vacío si no aplica; mapea nombres de campo string a arrays
de mensajes string. code es uno de los códigos enumerados y message es string no
vacío. 400 VALIDATION_ERROR incluye JSON
malformado; 401 UNAUTHORIZED; 403 FORBIDDEN incluye CSRF; 404 NOT_FOUND;
409 CONFLICT; 415 UNSUPPORTED_MEDIA_TYPE; 405 METHOD_NOT_ALLOWED;
500 INTERNAL_ERROR; 503 SERVICE_UNAVAILABLE. No filtrar SQL/trazas/expedientes.
Timeout no es duplicado. Mensaje uniforme para usuario inexistente/inactivo al login.

Los diez pares DEMO request/response válidos e inválidos completos existen en
backend/apps/historiales/fixtures/contrato_v1.json y su copia frontend. Sus metadatos
candidato son históricos: B1/A4 los actualizan en sus archivos sin cambiar formas
silenciosamente. No son pruebas HTTP. Ejemplos adicionales de extensiones:

```json
{"csrfToken":"DEMO-token-no-utilizable"}
```

```json
{"count":1,"limit":20,"offset":0,"results":[{"id":"DEMO-M-1","nombre":"Medicamento DEMO (no administrar)","presentacion":null}]}
```

CAT-01 con limit=0 → 400 VALIDATION_ERROR/fields.limit; logout válido 204 sin JSON;
logout sin CSRF → 403 FORBIDDEN. B1 añade fixtures de extensiones; el token DEMO no
es una sesión real. Las cookies/headers son conducta a implementar, no ya disponible.

## 6. CONTRACT-REPO-01@1.0.0 y pruebas de comportamiento

JsonMap = Mapping[str, Any]. Contexto validado de construcción: institucion (slug),
usuario_id, rol y profesional_id string o null; no del body clínico. Cada operación
se limita a ese contexto. Un adaptador sin contexto puede hacer health_check,
pero no operaciones clínicas. Conservar create(Institution) para salud; B1 añade
create_clinical(contexto), sin romper cuatro registros ni aceptar motor HTTP.

```python
def registrar_paciente(self, paciente: JsonMap) -> JsonMap: ...
def listar_pacientes(self, *, q: str = "", limit: int = 20, offset: int = 0) -> JsonMap: ...
def obtener_historial(self, paciente_id: str) -> JsonMap: ...
def registrar_consulta(self, paciente_id: str, consulta: JsonMap) -> JsonMap: ...
def registrar_diagnostico(self, consulta_id: str, diagnostico: JsonMap) -> JsonMap: ...
def registrar_tratamiento(self, diagnostico_id: str, tratamiento: JsonMap) -> JsonMap: ...
def registrar_receta(self, tratamiento_id: str, receta: JsonMap) -> JsonMap: ...
def archivar_paciente(self, paciente_id: str, motivo: str) -> JsonMap: ...
```

Entradas DTO Create de §5.1, retornos DTO lectura; listar devuelve página y obtener
historial devuelve árbol. Catálogo en puerto auxiliar MedicamentoCatalogo:
`listar_medicamentos(*, q: str = "", limit: int = 20, offset: int = 0) -> JsonMap`.
No noveno método oculto en historial. Mismo contexto para ambos puertos.

B1 materializa en domain/errors.py: DatosInvalidos (400), NoAutenticado (401),
AccesoDenegado (403), RecursoNoEncontrado (404), Conflicto (409) y
PersistenciaNoDisponible (503). Inesperados → INTERNAL_ERROR en presentación,
registro seguro. No cruzan excepciones de drivers. Ese archivo todavía no existe:
no importar código inexistente y declarar dependencia resuelta.

Aplicación valida DTO/permisos; adaptador relaciones, unicidad, estado y atomicidad.
Escritura completa o sin cambios; receta MySQL cabecera+detalle en una transacción.
Archivo requiere dos clientes/conexiones y barreras para probar ambos órdenes y
rollback, no solo sleep. Sin transacciones distribuidas ni reintento ciego de POST.

B1 entrega suite reutilizable por fabricante de repositorio, fixtures y limpieza
limitados a destinos aislados. Mismos casos contra los cuatro: cadena clínica e IDs,
alta/listado/lectura, duplicado/validación, ausente y referencias cruzadas, archivo
idempotente/inactivo, fallo intermedio sin parciales, concurrencia, búsqueda/paginación
y catálogo. HTTP aparte para sesión/CSRF/permisos/selección institucional. La prueba
actual test_contract_sql solo comprueba ejemplos: no sustituye persistencia real.

### Evolución contractual sin aprobaciones entre células

B mantiene contrato central. Corrección de implementación preserva versión; adición
compatible publica minor con ejemplos/pruebas antes del consumidor. Incompatibles:
major y transición; /api/ conserva v1 y /api/v2/ puede coexistir, puertos v1/v2 se
mantienen hasta migración probada. No renombrar v1 en sitio. PR declara versión y
corre suites de proveedor/consumidor aplicables; no requiere aprobación humana ajena.
Regresión se corrige en el módulo causante. Falta implementación → doble explícito
en tests/desarrollo, nunca éxito simulado en producción. Escalar solo contradicción
no resoluble mediante contrato, pérdida de datos, seguridad o incumplimiento académico.

## 7. Propiedad exclusiva

Prioridad: excepciones A específicas → resto de backend B → tabla → archivo nuevo
no listado B hasta asignación explícita. Un dueño por ruta, sin archivos simultáneos.

| Rutas actuales/futuras | Único dueño |
|---|---|
| frontend/** (package, vite, Dockerfile, tests, mocks, docs) | Jennifer |
| db/mongo/**; db/firebase/** (incluye Dockerfile, seeds, pruebas y docs) | Jennifer |
| backend/apps/historiales/infrastructure/adapters/mongo_adapter.py y firestore_adapter.py | Jennifer |
| backend/apps/historiales/test_*_nosql.py; docs/jennifer/** | Jennifer |
| GUIA_JENNIFER_AGENTES.md | Jennifer |
| backend/** salvo excepciones A: config, domain, application, presentation, factory, manage.py, requirements, Dockerfile, fixtures, tests y futuras apps identidad | Pablo |
| db/postgres/**; db/mysql/**; docs/pablo/** | Pablo |
| PLAN_MAESTRO.md; GUIA_PABLO_AGENTES.md; README.md; CONTRIBUTING.md; ESTADO_INTEGRACION.md | Pablo |
| docker-compose.yml; .env.example; .gitignore; .github/**; tests/CI globales y documentación central arquitectura | Pablo |
| Nuevas rutas raíz/configuración no asignadas | Pablo |
| .env/credenciales/caches/datos locales no versionados | Cada operador, nunca un PR |
| .git/** | Administrado por Git, no edición manual de objetos/referencias |

A describe una capacidad de infraestructura en su doc/issue con valores y prueba;
B implementa el archivo central en B1/B5. No es pedir permiso, es dependencia técnica
con dueño. A continúa lo independiente. No introducir overlays que nadie incorpore
a comandos de ejecución. Dependencias de herramientas se justifican dentro del
módulo y se prueban; no migrar stack por preferencia.

Excepción documental inicial autorizada: Pablo reorganiza plan, ambos manuales y
referencias centrales, sin código A. Al integrar GUIA_JENNIFER_AGENTES.md vuelve a
Jennifer; resto conserva tabla. No duplicar maestros. Documentos anteriores de
fase0 son archivo histórico, no vuelven a imponer gates ni revisiones obligatorias.

## 8. Pruebas y criterios de cierre

Existen Django runner, Node --test, Vite build, unittest NoSQL y experimentos SQL.
No hay lint, pytest, Ruff, Black, ESLint, Vitest ni CI de pruebas configurados;
.github solo tiene plantilla PR. Añadir herramientas necesarias con su módulo.

```powershell
git status --short
git diff --check
docker compose config -q
docker compose ps -a
docker compose exec -T backend python manage.py check
docker compose exec -T backend python manage.py test apps.historiales
node --test frontend/tests/contract-fixtures.test.js
docker compose exec -T frontend npm run build
curl.exe -f http://localhost:8000/api/health/
curl.exe -f http://localhost:8000/api/health/databases/
```

Test React necesita checkout completo: contenedor frontend no ve fixture backend.
Ejecutar desde raíz con Node; no ocultar ENOENT como éxito. NoSQL en procesos
separados porque ambas suites importan seed_demo:
`python -m unittest discover -s db/firebase/tests -v` y
`python -m unittest discover -s db/mongo/tests -v`. Integración usa destinos aislados
y variables de READMEs, nunca bases ajenas. SQL: comandos en
docs/pablo/fase0/PRUEBAS_SQL_AISLADAS.md; ese DDL no es migración productiva.

Antes de commit: estado/diff, pruebas afectadas/contrato, secretos/datos reales y
propiedad. Antes de merge: sincronizar main y repetir lo afectado por esa
sincronización; comprobar aceptación y reglas GitHub. Fallo obligatorio impide merge.
Omitida, fallida, aprobada son estados distintos. Un build/captura no demuestra
persistencia, permisos ni rollback. Evidencia: comando, resultado, SHA y entorno.

## 9. Dos ramas permanentes, PR por módulo

Únicas ramas activas: main estable, feature/jennifer y feature/pablo. Sustituye la
limpieza anterior que dejó solo main. Ambas parten de todo el trabajo integrado.
No crear ramas por tarea/arreglo/documento ni ramas temporales sin imposibilidad
técnica demostrada y motivo documentado previamente.

```powershell
# Sin cambios locales pendientes; usar rama propia existente.
git fetch origin
git switch feature/pablo   # Jennifer: feature/jennifer
git merge origin/main
# Implementar un módulo y probar antes de commit.
git add -- <rutas-propias>
git commit -m "feat(auth): implementa sesiones institucionales"
git push -u origin feature/pablo
```

Conventional Commits obligatorio: tipo(scope): descripción; feat/fix/test/docs/chore/
refactor y descripción concreta. No «cambios», «final» ni «fix» sin explicación.
Conservar historia previa sin reescribir sus mensajes antiguos.

Un PR activo por rama hacia main; no empujar el módulo siguiente al PR abierto.
Tras integrar, conservar rama, actualizar desde main y preparar el siguiente módulo.
Preferir merge commit para conservar ancestros en ramas largas. Si GitHub exige
otro método, verificar diff siguiente sin resetear trabajo pendiente. Guardar cambios
propios explícitamente antes de sincronizar: commit coherente o stash local por rutas.
No reset --hard, force push ni rebase destructivo. Conflicto en fuente ajena lo resuelve
su dueño; no reemplazarlo con nuestra versión por rapidez.

PR: módulo/responsable, archivos/razón, versión API/REPO, funciones terminadas,
pruebas/comandos/resultados, limitaciones, evidencia, commits convencionales y alcance
de datos. Dueño integra cuando aceptación y GitHub lo permitan, sin revisión cruzada
obligatoria. No eludir protecciones con override administrativo. Restricción real de
plataforma se informa y el trabajo se conserva publicado; no se inventa una aprobación.

## 10. Continuación y riesgos técnicos

B empieza B1/suite común, luego B2 y capacidad Mongo central. A conserva A1/A2,
completa justificaciones y elige A3 o A4 con mocks según disponibilidad. No espera
endpoints para componentes, modelos o pruebas propias.

| Riesgo/dependencia | Resolución y dueño | Qué continúa |
|---|---|---|
| Runtime puerto/errores de ocho métodos ausente | B1 publica implementación/suite; no depende de aprobación A | A1/A2, UI y preparación A3; certificar integración cuando exista runtime |
| Mongo standalone no cumple archivo multidocumento | B configura replica set preservando datos; A prueba versión raíz | Modelos A2, Firestore, React |
| Fechas/vínculos históricos ambiguos | B3/B4 inventario, backup, expansión nullable, conciliación antes de NOT NULL | Pruebas en base nueva; no fechas/relaciones inventadas |
| SQLite versionado y migrate automático | B2 retira índice conservando archivo y planifica traslado/reversión | Núcleo y mocks sin mover datos activos |
| Diagramas/feedback de Entrega I fuera de Git | A5/B5 anotan faltantes y completan análisis verificable | Operaciones obligatorias, sin atribuir revisión docente inexistente |
| Especialización fuera del núcleo | Dueño propone extensión aditiva/pruebas; B publica contrato central | Modelos/componentes propios sin rutas ficticias productivas |
| GitHub exige revisión externa o falta permiso | Informar restricción concreta sin bypass | Trabajo preservado y tareas independientes |

No se imponen fechas inventadas. Contrato documentado no significa implementación
funcional, commit local no significa publicado, omitida no significa aprobada.
Los informes históricos de F0 conservan evidencia; su método queda sustituido aquí.
