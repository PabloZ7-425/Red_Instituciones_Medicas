# B-C0-T1 — Propuesta de decisiones de Fase 0

Fecha: 2026-10-20. Responsable: Pablo / célula B. PR del plan: PR-02.
Base: `e9b2efafa51ca897765d9055f39be219da5a41bb`.

**Estado: propuesta para revisión A↔B. No ratificada.** Este documento no
cierra el gate F0 ni autoriza migraciones. Complementa el
[plan maestro](../../../PLAN_MAESTRO.md) y la
[guía de Pablo](../../../GUIA_PABLO_AGENTES.md). Los archivos nuevos de esta
carpeta pertenecen a la propuesta B; los documentos compartidos se conservan.

## Decisiones que propone B

| ID | Propuesta concreta | Confirmación pendiente |
|---|---|---|
| D0-01 | Sesión Django con cookie HttpOnly; CSRF en login y escrituras; sesión expira a las 8 horas, sin persistencia al cerrar navegador. Rotar sesión al entrar e invalidarla al salir. HTTPS y cookie Secure en un eventual entorno HTTPS. | Jennifer debe confirmar consumo de cookies, CSRF y expiración desde React. |
| D0-02 | ADR-ORM-01: Django ORM solo para identidad, grupos, permisos y sesiones. Base PostgreSQL técnica `identidad`, usuario con privilegios solo sobre ella, separada de `hospital`. Conservar inicialmente el User de Django y proponer perfil institucional uno a uno. | Pablo y Jennifer deben ratificar el diseño y su interpretación académica. No crear base ni migrar todavía. |
| D0-03 | Roles comunes `admin`, `medico`, `secretaria`, `enfermero`, todos limitados a su institución. Ver matriz inferior. Sin registro público ni privilegios clínicos globales por ser superusuario técnico. | A debe validar necesidades de laboratorio/odontología y mapeos de sus roles. |
| D0-04 | Envoltorio `{error:{code,message,fields}}`; 400 validación, 401 sin sesión, 403 permisos/CSRF, 404 recurso ausente o ajeno, 409 conflicto, 500 interno, 503 persistencia no disponible. | Ratificar códigos adicionales y autenticador DRF que produzca 401 sin sesión; SessionAuthentication por sí sola puede producir 403. |
| D0-07 | Una escritura común por transacción; archivo conserva historial y bloquea nuevas escrituras clínicas. Lectura de historial coherente por operación, sin prometer una transacción distribuida entre motores. No reintentar POST automáticamente sin idempotencia. | A debe confirmar límites realizables en Mongo standalone y Firestore; SQL usa transacciones de sus drivers, no transaction.atomic de Django. |
| D0-09 | Mantener Django test runner y SimpleTestCase para ejemplos contractuales; pruebas reales SQL en C3/C4. Build con npm existente. No agregar pytest, lint ni dependencias para C0. | Revisión A; no presentar pruebas de ejemplos como pruebas de endpoints. |

## Decisiones donde B requiere entrada de A

| ID | Propuesta / solicitud concreta | Dueño y estado |
|---|---|---|
| D0-05 | IDs opacos string, fechas YYYY-MM-DD, timestamps UTC con Z. Confirmar conversión de ObjectId y referencias externas sin filtrar tipos del driver. | A propone, B revisa; pendiente. |
| D0-06 | Solicitar diagramas y ejemplos NoSQL de paciente → consulta → diagnóstico → tratamiento → receta, límites de documento y unicidad de identificación. | A propone; pendiente. B no determina embebido/referencias. |
| D0-08 | Solicitar comando reproducible de inicialización y exportación/importación del emulador con fixtures DEMO. | A propone; pendiente. No cambiar Compose/Firestore desde B. |
| D0-10 | Priorizar flujo común; después hospital ingreso/cama/alta y pediatría tutor/vacuna/crecimiento. Solicitar modelos y observaciones de Entrega I antes de cambiar SQL. | Ambos; pendiente evidencia académica y prioridad final. |

## Matriz propuesta D0-03

Todos los roles pueden usar `/me`; login solo requiere credenciales válidas.
Un usuario inactivo, sin perfil o sin institución válida no recibe sesión clínica.

| Operaciones | admin | medico | secretaria | enfermero |
|---|---|---|---|---|
| API-03 listar pacientes | Sí | Sí | Sí | Sí |
| API-04 alta paciente | Sí | Sí | Sí | No |
| API-05 historial completo | Sí | Sí | No | Sí |
| API-06..09 escritura clínica | Sí | Sí | No | No |
| API-10 archivo | Sí | No | No | No |

Listado administrativo devuelve solo datos identificativos y estado. La matriz
no concede a enfermería facultades de prescripción. Administración de cuentas
queda en Django admin restringido; no añade una operación al núcleo API.
La cuenta clínica debe estar ligada a un profesional habilitado para crear consultas;
el servidor obtiene `medico_id` de ese vínculo, jamás del cuerpo enviado por React.
El mapeo profesional de instituciones NoSQL requiere confirmación de A.

## Detalles de sesión que requieren acuerdo

- Proponer GET `/api/auth/csrf/` para obtener cookie CSRF y POST
  `/api/auth/logout/` para invalidar sesión (204). Son dos extensiones propuestas
  de autenticación; las diez operaciones del plan mantienen sus IDs.
- React enviaría `credentials: include` y cabecera `X-CSRFToken`; conservar
  nombres estándar `sessionid` y `csrftoken`, sin token de acceso en localStorage.
- En desarrollo usar el mismo hostname `localhost` para frontend y backend;
  CORS con credenciales y orígenes CSRF explícitos se implementarán en C1.
- CSRF debe cubrir también el login anónimo. Mensaje de credenciales inválidas
  uniforme para usuario inexistente/inactivo, sin revelar cuál falló.
- No añadir ni activar estas rutas en este PR. Jennifer debe revisar el flujo
  antes de fijar versión; no anunciar soporte de sesión que aún no existe.

## Hallazgos SQL que debe resolver C2

| Hallazgo comprobado | Resolución propuesta, pendiente de revisión |
|---|---|
| Hospital guarda identificación en dpi_cui(20); MySQL en identificacion(100). | DTO común limitado a 20, mapeo explícito sin renombrar columnas existentes. |
| PostgreSQL consulta exige médico; MySQL exige además cita y fecha. | Médico derivado del principal. Proponer cita_id opcional en DTO; C2 debe habilitar consulta sin cita en MySQL o acordar otra precondición antes de ratificar. Nunca crear citas ficticias silenciosamente. |
| MySQL tratamiento se relaciona con consulta, no diagnóstico; receta también cuelga de consulta. | C2 debe definir migración incremental que preserve relación con diagnóstico/tratamiento antes de afirmar conformidad del adaptador. No inferir asociaciones ambiguas al leer. |
| Diagnóstico MySQL exige código; hospital permite CIE-10 nulo. | Proponer codigo_cie10 obligatorio común, con mapeo revisado al código MySQL. A debe confirmar equivalencia documental. |
| PostgreSQL receta_prescripcion representa un medicamento; MySQL separa cabecera/detalle. | Proponer una receta común por medicamento; documentar proyección y transacción de cabecera/detalle. Sin cambiar hoy los esquemas. |
| Estado SQL también permite inactivo y fecha_baja es DATE. | DTO de lectura admite activo/inactivo/archivado; archivo escribe motivo_baja/fecha_baja. fecha_archivo es fecha sin hora, no timestamp inventado. |
| SQLite está ignorado pero continúa versionado. | Limpieza en PR separado: git rm --cached, conservar archivo local; no mezclarla con contrato ni migración. |

## Plan de migración de identidad (solo diseño)

Antes de C1: ratificar ubicación; inventariar usuarios/sesiones existentes sin
exponerlos; definir copia de seguridad y reconciliación de credenciales de tablas
`usuario` clínicas, que no serán fuentes de login paralelas. No copiar contraseñas
desconocidas como si fueran hashes Django: requerir restablecimiento si procede.
Validar en base técnica de prueba el esquema, perfil, vínculo profesional e
institución; documentar comandos con alias explícito, conteos y reversión.
Revisar el `manage.py migrate` automático de Compose antes de cambiar DATABASES.
La reversión debe restaurar configuración y respaldo ensayado, preservando las
escrituras posteriores según ventana acordada; ninguna migración automática aquí.

## Criterio de continuación

Faltan ratificación A↔B de D0-01..10, ejemplos revisados, evidencia de ambos
equipos y reserva de archivos para C1. Los contratos y las rutas aquí son
propuestos; `domain/ports.py` conserva su interfaz actual hasta revisión A.
La siguiente entrega de implementación será B-C1-T1 únicamente al cerrar F0.
