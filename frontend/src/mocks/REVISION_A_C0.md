# Revisión A para B-C0-T1 — candidatos API/REPO y resoluciones #6

Tarea `A-C0-T1`, Jennifer / Célula A. Base examinada:
`f35207d7854e06122cfb30ee475b806cf0650c1e`. PR #6 revisado en
`7010e47d4dfaffc14a5aea476448a7a3eeff7413`.

**Estado:** revisión y fixtures provisionales; no ratificación bilateral completa,
no F0 cerrado. Se conserva el visto bueno técnico de A ya comunicado; no modifica
los contratos de B ni atribuye a Pablo decisiones que todavía debe revisar.

## Diez operaciones desde React y NoSQL

| ID | Verificación cliente | Observación para integración |
|---|---|---|
| API-01 login | Respuesta `{usuario}` y error 401 compatibles | Sesión/CSRF reales pendientes B; fixture no simula cookies ni tokens |
| API-02 me | Identidad coincide con login; institución devuelta por servidor | Cuenta profesional validada, nunca selector editable de motor |
| API-03 lista | `count/limit/offset/results`, identificación string, vacío coherente | Incluye archivados según candidato; precisar si q significa prefijo o subcadena antes de indexar NoSQL |
| API-04 alta | Cuatro campos de creación, estado/ID generados en respuesta | Unicidad por institución debe garantizarse también con concurrencia |
| API-05 historial | Cadena consulta → diagnóstico → tratamiento → receta sin pérdida de IDs | Solo DEMO acotado en este candidato; no truncar historias silenciosamente |
| API-06 consulta | `fecha` civil, notas y cita opcional; lectura admite cita null | PostgreSQL DATE explícita y cita nullable MySQL están diseñados en #6; falta implementación C2 |
| API-07 diagnóstico | ID propio y `consulta_id`, CIE-10/descripcion | Aceptar instancia clínica concreta, no confundir catálogo compartido con ocurrencia |
| API-08 tratamiento | Recibe ID diagnóstico en ruta, devuelve relación | MySQL debe resolver diagnóstico a una sola consulta/paciente; ver bloqueo inferior |
| API-09 receta | ID tratamiento y medicamento, dosis/frecuencia/vía | Un renglón por DTO; catálogo por institución aún debe entregarse a UI, sin inventar una nueva ruta |
| API-10 archivo | Paciente archivado conserva datos y ramas del historial | Mismo motivo conserva fecha; motivo distinto 409; garantía de exclusión pendiente de implementar |

Se avalan para consumo cliente el envoltorio de errores, las diez rutas candidatas,
las ocho responsabilidades del puerto y la separación de salud/persistencia.
DTOs y fixtures no acreditan endpoints activos, permisos, transacciones ni CRUD.

## D0-03/04/05 — posición de A

- **D0-03:** compatible la propuesta de `laboratorista` restringido a laboratorio,
  con alta/lectura/atención y sin diagnóstico clínico, tratamiento, receta ni
  archivo. No convertirlo en médico ni interpretar resultados como diagnósticos.
  Identidad profesional proviene del principal validado por B. Esto acepta la
  dirección del diseño de #6; aún falta registrarla en la matriz contractual final.
- **D0-04:** se aceptan estructura y códigos propuestos incluidos 405/415/503;
  errores generales usan `fields: {}`. Sin sesión se espera 401 y CSRF/rol 403;
  B debe configurar y probar ese comportamiento real, no asumirlo de DRF.
- **D0-05:** ID opaco string en todos los DTOs y referencias. Las fixtures usan
  IDs DEMO estables, sin dictar si el almacenamiento será SQL, BSON o Firestore.
  Los clientes no interpretan el ID ni lo usan como autorización. Campos de
  fecha civil del candidato, incluido archivo, se conservan `YYYY-MM-DD`;
  timestamps, si se añaden mediante acuerdo, UTC ISO Z y presentación Guatemala.
  No derivar fecha clínica desde UTC ni desde cita automáticamente. Opcionales
  de entrada se omiten, null se rechaza según candidato; null en lectura se
  conserva en cita, motivo/fecha archivo y vía cuando corresponda.

## D0-06/08 — evidencia y traducción pendiente

PR #3 conserva modelo y seed Firestore; PR #4 conserva esquema/seed Mongo.
No se vuelve a definir su modelo dentro de los fixtures de React. Esos seeds son
preparatorios y **no** cumplen todavía los DTOs finales: receta vinculada a consulta
o diagnóstico embebido sin los campos del candidato requieren mapear relaciones
explícitas durante C3/C4, nunca reconstruirlas por coincidencia ambigua.

- Mongo: `ObjectId`, fechas BSON y referencias de resultados quedan internos;
  adaptador entregará IDs externos y fecha civil contractual. Diagnósticos
  embebidos necesitan ID propio localizable para API-08. Límites del agregado y
  su mapeo completo aún se ratifican; el límite de un fixture no es el de la API.
- Firestore: referencias lógicas paciente/consulta/diagnóstico/tratamiento se
  resuelven dentro de la institución. No devolver DocumentReference, rutas ni
  Timestamp del SDK. Historial del seed no se presenta como contrato ya adaptado.
- D0-08: en PR #3 ya se demostró exportación nativa, instancia nueva con `--import`
  y verificación de siete documentos sin volver a sembrar. Pendiente coordinar
  persistencia/exportación en Docker local; no se edita Compose desde este PR.

## D0-07 — elección técnica A para mantener el modelo separado

Para pacientes/consultas/resultados en documentos separados, **A elige diseñar
replica set local y transacciones multidocumento**; no prometer la garantía con
Mongo standalone. Esto define la dirección técnica, no autoriza modificar Compose.

Cada escritura clínica transaccional debe localizar el paciente raíz, comprobar
activo y modificar condicionalmente una versión/contador de ese mismo paciente,
además de escribir los documentos hijos. Archivo modifica estado y esa raíz bajo
el mismo protocolo. Una lectura snapshot sola o un candado de proceso no bastan.
El reintento debe reevaluar el estado; no repetir un POST confirmado a ciegas ni
introducir efectos externos en callbacks reejecutables.

Firestore leerá paciente dentro de la transacción que escribe los hijos; archivo
modifica ese documento. El modelo SQL de bloqueo raíz de #6 es compatible con
la misma semántica. Se requieren pruebas con dos operaciones coordinadas, ambos
órdenes y rollback; las pruebas de seed existentes no certifican esta garantía.

Siguiente infraestructura propuesta: PR exclusivo, dueño temporal A para Mongo,
revisión B y reserva previa de Compose. Diseñar arranque y transición preservando
datos existentes, sin down -v ni volúmenes borrados. Mientras ese acuerdo no esté
registrado, seguir tareas A independientes; no tocar Compose en esta rama.

## Dependencias precisas de Pablo y estado de aprobación

| Dependencia | Por qué importa | Entrega esperada |
|---|---|---|
| Identidad de diagnóstico MySQL | UNIQUE(consulta_id, diagnostico_id) aún permite un diagnóstico compartido entre consultas; API-08 solo recibe un ID diagnóstico | Definir ID externo de ocurrencia, por ejemplo consulta_diagnostico.id, o demostrar cardinalidad uno-a-uno con conciliación de datos. No cambiar el JSON cliente |
| Búsqueda q | El candidato dice qué campos, pero no prefijo/subcadena | Semántica concreta realizable en cuatro motores antes de elegir índices |
| Catálogo medicamento | API-09 exige medicamento_id y no hay entrega cliente de catálogo | Fixtures/bootstrap acordados por institución; no solicitar a UI un ID interno escrito a mano |
| Consolidación del puerto | Actual: 4 métodos, incluido desactivar; candidato: 8, incluido archivar | Tipos, DTOs, errores y contexto profesional en cambio B revisado; A no edita domain/ports.py |
| D0-07 infraestructura | Transacciones Mongo necesitan topología compatible | Reserva de archivo y revisión del diseño, después pruebas de carrera por motor |

La fecha PostgreSQL explícita, cita nullable MySQL y FKs compuestas propuestas en
#6 reciben visto bueno de A **como diseño**. La identidad de ocurrencia diagnóstica
debe precisarse antes de ratificar el flujo completo. Las ocho firmas y fixtures
pueden revisarse ahora, sin afirmar que su implementación definitiva está autorizada.

## Aceptación de A-C0-T1

- [x] Diez operaciones revisadas y copia cliente exacta de los ejemplos B.
- [x] Login/me, paciente, lista, historial, archivo y errores sintéticos disponibles.
- [x] Casos NoSQL de conversión/relaciones descritos sin modificar archivos B.
- [x] Pruebas estáticas de consumidor y build React ejecutados.
- [ ] Resolver dependencias contractuales y registrar ratificación A↔B con SHA.
- [ ] Actualizar copia a esa versión final, repetir pruebas si cambia y revisión cruzada.
- [ ] Gate F0 conjunto y cierre del PR-01 del plan.
