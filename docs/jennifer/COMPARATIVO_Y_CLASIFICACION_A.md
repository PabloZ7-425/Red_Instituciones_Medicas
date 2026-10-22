# A5 — aportación NoSQL al comparativo y clasificación de datos

Jennifer, 22 de octubre de 2026. REQ-04/11/12/13 del plan 2.0. Complementa el
comparativo central de Pablo; no cambia contratos ni atribuye revisión docente.

Actualización de cierre A4: resultados y procedimientos ya tienen API/UI real
certificada en el entorno desechable, contrato SPECIALTY-API-01 y persistencia
transaccional. Ver A4_CIERRE_REAL.md. Las referencias a falta de flujo especializado
en la evidencia inicial inferior quedan sustituidas por esta entrega; no cambia
los límites de producción, recuperación o conciliación de históricos.

## Elección y modelo documental

| Institución | Elección y modelo propio | Justificación y límites observados |
|---|---|---|
| Laboratorio / MongoDB | A2 conserva resultados por examen, con campos variables; A3 usa pacientes compactos y colecciones clínicas v2 separadas | Resultados con números/texto/booleanos no exigen una columna SQL para cada examen. Consultas, ocurrencias, tratamientos y recetas crecen como documentos referenciados; no se acumula la historia completa en el paciente. LAB-01 ya opera resultados v2 con catálogo e historial separado y evidencia HTTP/nativa de A4. |
| Odontología / Firestore | A1 define pacientes, citas, consultas, diagnósticos, tratamientos, recetas y procedimientos; A3 opera el núcleo v2 con IDs string | Documentos pequeños y operaciones directas favorecen gestión simple. Se conserva paciente raíz como punto de consistencia; el árbol público se compone desde referencias. ODONTO-01 tiene evidencia UI/API/transacción; el modelo no demuestra por sí solo ventajas de rendimiento/costo. |

Embebidos pequeños del modelo A2 (contacto/tutor y campos de un resultado) se leen
con su dueño y tienen estructura acotada. Los conjuntos crecientes se referencian:
la vida clínica del paciente no debe hacer crecer indefinidamente un único documento.
En v2 los campos clínicos del paciente son planos; sus consultas/diagnósticos/
tratamientos/recetas tienen identidad propia. Un código CIE-10 repetido no identifica
una ocurrencia: dos consultas pueden compartir código y conservar tratamientos
independientes. Los modelos DEMO anteriores no se convierten en datos v2 mediante
inferencias de fechas o relaciones.

Mongo tiene validadores e índices únicos institucionales; Firestore no impone las
mismas restricciones de esquema/relación del servidor: el backend y transacciones
aplican el contrato. Referenciar un ID no equivale a una clave foránea automática.
El mapeo público elimina BSON, referencias SDK, profesional interno y versiones;
las fechas civiles siguen siendo strings YYYY-MM-DD. Las referencias y fechas de
los fixtures heredados se conservan sin reinterpretarlas globalmente.

## Consistencia comparada con SQL

| Aspecto | PostgreSQL / MySQL, módulos B | MongoDB, A3 | Firestore, A3 |
|---|---|---|---|
| Relaciones | FK/UNIQUE y restricciones nativas; aplicación verifica contexto | Referencias verificadas por aplicación dentro de transacción | Lecturas de padres/referencias en la transacción antes de encolar escrituras |
| Archivo frente a escritura | Bloqueo de fila raíz, según B3/B4 | Snapshot y modificación de versión raíz; necesita replica set | Lectura y cambio de raíz; SDK vuelve a verificar activo al reintentar |
| Historia | Lectura transaccional del árbol, esquema relacional | Lectura snapshot y proyección JSON | Transacción read-only y proyección JSON |
| Recuperación | Evidencia B3/B4 de respaldos y ensayos propios | Dump/restore nativo; BSON, índices y validadores verificados | Export/import nativo del emulador; documentos/tipos verificados |
| Entorno probado aquí | Integración HTTP A5 con roles SQL limitados | Replica set local de un nodo, no HA | Emulador local; no Firebase productivo |

El éxito de una conexión de salud no demuestra persistencia, aislamiento o archivo.
La evidencia A3 incluye concurrencia/rollback nativos y A5 añade React/HTTP real con
los cuatro motores. La recuperación clínica nueva conserva historias creadas por
el repositorio, no solamente fixtures exactos: el origen se apaga y el destino se
lee sin seed; luego admite escritura en el paciente activo y sigue rechazando el
archivado. No se comparan aquí throughput, latencia o costos: no se hizo benchmark.

## Clasificación y controles

Esta matriz es la propuesta verificable del proyecto académico. «Público» describe
sensibilidad; no significa que deba existir una ruta anónima. El contrato clínico
requiere sesión y restringe CAT-01 a admin/médico incluso para un catálogo sin datos
personales. Un admin clínico continúa limitado a su institución.

| Clase | Ejemplos | Controles comprobados y tratamiento |
|---|---|---|
| Pública / sin datos personales | Código/esquema, documentación, catálogos ficticios y DEMO identificados | Se pueden versionar datos sintéticos. No usar el aspecto DEMO como garantía de que un dump contiene solo datos ficticios. |
| Confidencial | Identificación, nombres, nacimiento, datos de contacto y tutores | Sesión, institución del principal, permisos por operación, errores seguros y no-store. No publicar screenshots/dumps con datos reales. Tutores/seguimiento tienen flujo real; secretaría recibe solo tutores, sin historia ni medidas. |
| Restringida clínica | Evolución, diagnósticos, resultados, tratamientos, recetas, estado/motivo de archivo | Acceso institucional y por rol en backend; vínculo profesional para escribir; archivo conserva historia e impide nuevas escrituras. La lectura de secretaría está restringida por contrato. |
| Restringida de seguridad | Contraseñas/hashes, cookies, CSRF, claves de motores y respaldos clínicos completos | No se devuelven credenciales por API ni se guardan tokens en localStorage. HttpOnly/CSRF/logout comprobados; SQL runtime limitado. Secretos y exportaciones fuera de Git; respaldo en directorio privado. |

Los respaldos heredan la mayor sensibilidad de su contenido, incluidos usuarios
heredados si están en una base exportada. Los manifiestos registran hashes/counts
y metadatos, no ejemplos de datos clínicos. SHA-256 detecta cambios accidentales;
no autentica a un atacante que pueda reemplazar a la vez respaldo y manifiesto.
El almacenamiento debe preservar confidencialidad y acceso al manifiesto confiable.

Controles de API probados no sustituyen controles del motor. Mongo local sin auth
y Firestore Emulator permiten acceso directo a quien alcance esos servicios.
La prueba usa loopback/entornos dedicados; no certifica autorización de Mongo,
reglas Firebase, cifrado, TLS o despliegue productivo. Django ORM se utiliza para
identidad/sesiones, no como atajo para datos clínicos NoSQL/SQL.

## Trazabilidad y límites de cierre

- REQ-04: decisiones de embebido/referencia, A1/A2 y repositorios v2; demostración
  especializada de exámenes/procedimientos completada en A4.
- REQ-05..09: operaciones equivalentes, alta, cadena, archivo y enrutamiento común
  tienen evidencia real A3/A5 para los SHAs documentados.
- REQ-10: interfaz común y especializada completas en A4 con contrato publicado y E2E real.
- REQ-11/12: esta sección aporta comparación y clasificación; Pablo debe conciliar
  la versión central con las limitaciones y evidencia de cada módulo.
- REQ-13: paciente nuevo/existente dentro de v2 tiene lectura e historia trazadas.
  Un histórico fuera de versión requiere inventario y conciliación; no se declara
  migración clínica universal ni recuperación de todos los motores en este módulo.

Referencias: [A3](A3_NOSQL.md), [A4](A4_FLUJO_CLINICO.md),
[integración real](A5_INTEGRACION_REAL.md),
[recuperación clínica](A5_RECUPERACION_NOSQL.md).
