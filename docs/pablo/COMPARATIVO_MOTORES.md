# Comparativo de motores y clasificación de datos

Pablo, 2026-10-21. Complementa maestro REQ-01/03/04/11/12/13 y B5.
No hay benchmarking de rendimiento ni revisión docente externa acreditada.
Las observaciones siguientes separan diseño, implementación y evidencia.

| Institución / motor | Asignación y modelo | Consistencia implementada | Evidencia y límite |
|---|---|---|---|
| Hospital / PostgreSQL 16 | Atención con relaciones estrictas: paciente, médico, cita, consulta, diagnóstico, tratamiento, prescripción e ingreso/cama/alta | FKs, constraints, índices de ocupación, transacciones y bloqueo de fila paciente; lectura snapshot | B3 y pruebas HTTP B5 reales; no se afirma throughput ni cobertura de facturación |
| Pediatría / MySQL 8.4 InnoDB | Seguimiento longitudinal: paciente, tutores por vínculo, aplicaciones de vacunas, controles en kg/cm y cadena clínica | FKs compuestas por ocurrencia/consulta, unicidad de cita, transacciones y bloqueo raíz; receta cabecera/detalle indivisible | B4 y HTTP B5 reales; DDL con commit implícito requiere fases/respaldo; no evalúa percentiles ni calendarios clínicos |
| Laboratorio / MongoDB 7 | Resultados variables por examen; contacto pequeño embebido y consultas/resultados crecientes separados | Validadores/índices preparatorios A; infraestructura B5 habilita transacciones rs0 | Seeds/modelo A y prueba técnica commit/abort; adaptador clínico, archivo concurrente y API persistida pendientes A3 |
| Odontología / Firestore emulado | Gestión documental por paciente/cita, diagnósticos breves y renglones embebidos en fixture; procedimientos crecientes separados | Seed transaccional A; referencias lógicas, sin FKs SQL | Modelo/exportación/seed A; no certifica puerto clínico ni restricciones/índices del servicio cloud; flujo API pendiente A3 |

SQL conserva entidades con atributos atómicos y relaciones por claves. En MySQL
el diagnóstico del catálogo no identifica la ocurrencia: la tabla puente determina
consulta/paciente y el tratamiento la referencia explícitamente. Los dos motores
preservan fecha civil de consulta; una cita no demuestra esa fecha. La cabecera
de receta MySQL y sus detalles permiten varios medicamentos sin multiplicar
datos de la cabecera. El parentesco depende del vínculo tutor–paciente; no del
tutor global. Los campos heredados se conservan sin inventar asociaciones o unidades.
Diagramas y mapeos: [B3](B3_POSTGRESQL.md) y [B4](B4_MYSQL.md).

Mongo permite campos de resultado diferentes sin forzar una tabla por modalidad;
eso no elimina validación, índices ni consistencia de referencias. Separar
colecciones crecientes evita documentos raíz sin límite. En el futuro proveedor,
la transacción debe escribir la versión del paciente para competir con archivo.
rs0 de un nodo aporta capacidad transaccional, sin redundancia ni alta disponibilidad.

En Firestore, embebido pequeño reduce lecturas relacionadas; datos crecientes
requieren documentos y consultas/índices apropiados. El fixture tiene límites
propios (por ejemplo 1–10 renglones) que no pueden truncar el historial contractual.
Los IDs de ocurrencia deben permanecer estables aun si el diagnóstico está
embebido. El emulador no prueba latencia, costos, cuotas, disponibilidad ni reglas
de producción. La agilidad del flujo depende de diseño/UI y no se presume por
elegir un motor documental.

## Operaciones en lenguaje de usuario

1. La persona inicia sesión; su perfil decide institución, rol y profesional.
2. Busca pacientes existentes por prefijo o registra uno nuevo. Se evita duplicar
   identificación dentro de la misma institución, sin mezclar expedientes ajenos.
3. Abre el historial y registra consulta, diagnóstico, tratamiento y medicamento
   del catálogo institucional; todos conservan sus relaciones e identidades.
4. Admin archiva por motivo administrativo. Se conservan paciente y atenciones
   anteriores; no se aceptan atenciones posteriores al archivo confirmado.
5. Hospital dispone de ingreso/cama/alta; pediatría dispone de tutor, vacuna y
   crecimiento por puertos auxiliares. Laboratorio/odontología conservan los
   modelos especializados de A; sus flujos clínicos integrados siguen pendientes.

El mismo contrato permite comparar salidas, no hacer una transacción distribuida
entre instituciones. No hay motor compartido para reemplazar a un proveedor
ausente. La fábrica no convierte salud conectada en capacidad clínica.

## Clasificación y controles

| Información | Clasificación del proyecto | Acceso/control implementado o pendiente |
|---|---|---|
| Nombres de catálogo y documentación académica sin personas | Pública como referencia | CAT-01 requiere además sesión/rol institucional para resolver IDs utilizables; no publica stock/precios |
| Identificación, nacimiento, contacto y tutores | Confidencial | Sesión/perfil, aislamiento institucional y permisos administrativos; no imprimir cuerpos en logs |
| Evolución, diagnósticos, tratamientos, recetas, resultados y mediciones | Restringida | Roles de historial/escritura y profesional habilitado; transacciones/archivo en SQL; control equivalente NoSQL pendiente A3 |
| Credenciales, hashes, cookies/tokens, perfiles técnicos | Restringida | Django como fuente única; hashes de contraseña, CSRF, expiración absoluta, rotación/logout; sin contraseñas en DTOs |
| Respaldos, dumps y exportaciones de expedientes | Restringida | Directorio local ignorado y permisos privados del proceso; restauración aislada, hashes y conservación del origen; no se promete cifrado en reposo implementado |
| Estado agregado de conectividad sin personas | Pública en entorno local de desarrollo | Endpoints de salud actuales; no sustituye permisos clínicos ni certificación de proveedor |

Los IDs opacos no anonimizan un expediente. Los catálogos públicos como concepto
no justifican publicar datos de paciente. Session cookies son HttpOnly/Lax;
CSRF valida escrituras, incluido login; Secure se configura al servir HTTPS.
No se implementaron fuentes alternativas de usuario desde tablas legacy o Firebase
Auth. No se amplía acceso por ser superusuario técnico.

El entorno Docker es local: puertos del host ligados a loopback, Mongo sin auth
de servidor y Firestore emulado con credenciales anónimas. Django es la frontera
de autorización de aplicación. Esto no certifica endurecimiento, aislamiento de
red, cifrado ni reglas de un despliegue público. Runtime SQL separado de owner,
sin DDL/borrado/credenciales legacy; secretos reales permanecen fuera de Git.

Fuentes A consultadas sin modificarlas: [MongoDB](../../db/mongo/README.md) y
[Firestore](../../db/firebase/README.md). Falta el aporte A5 final y el feedback
docente/diagramas de Entrega I ausentes del repositorio. Este comparativo no
atribuye esas revisiones ni convierte modelos/fixtures en funcionalidad clínica.
