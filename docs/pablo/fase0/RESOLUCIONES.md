# Resoluciones B tras revisión A — base común f35207d

Responsable: Pablo / célula B. Seguimiento de B-C0-T1, D0-03 y D0-07.
Referencia común: `f35207d7854e06122cfb30ee475b806cf0650c1e`.

## Estado y alcance

Jennifer comunicó visto bueno técnico a arquitectura, separación ORM/drivers,
sesiones con CSRF, IDs string, fechas ISO, errores y paginación. Este visto bueno
no equivale a ratificación completa de las diez decisiones ni de todas las
extensiones propuestas. Fase 0 continúa abierta.

Se inspeccionaron los borradores GitHub #3 (Firestore) y #4 (MongoDB). Sus modelos
son preparatorios, no adaptadores clínicos ratificados. Permanecen independientes;
este cambio solo añade documentación B. No modifica fuentes A, contratos activos,
init.sql, bases pobladas, Compose ni configuración Django.

Este documento concreta el diseño SQL que B puede implementar en C2 tras el
gate, y presenta propuestas de contrato que A debe revisar. El DDL siguiente es
un boceto revisable: **no es una migración lista para ejecutar**. La suite actual
no prueba estos cambios SQL. C2 entregará scripts versionados y pruebas en bases
aisladas, incluyendo rollback y conservación de datos existentes.

## 1. PostgreSQL: fecha de consulta

Decisión interna B: persistir la fecha clínica explícita en `consulta.fecha DATE`.
El DTO ya incluye `fecha`, por lo que no cambia la forma del contrato. No derivarla
de la fecha de cita, ingreso ni fecha de creación del registro: una cita puede
haberse reprogramado y su fecha no demuestra cuándo ocurrió la consulta.

Secuencia propuesta para una base poblada:

1. Respaldar e inventariar consultas y dependencias en un entorno aislado.
2. Añadir `fecha DATE` nullable en migración incremental.
3. Completar fechas históricas solo con datos confirmados y trazabilidad de su
   origen. Si no existen, registrar esos IDs como pendientes; no usar CURRENT_DATE
   ni una fecha ficticia para satisfacer NOT NULL.
4. Verificar que no quedan NULL y aplicar NOT NULL antes de habilitar el adaptador
   contractual. Si quedan fechas desconocidas, la activación queda bloqueada;
   exponer null requeriría revisar el contrato con A.
5. Para instalaciones nuevas, incorporar DATE NOT NULL sin valor predeterminado
   a init.sql en el mismo PR C2. El adaptador siempre envía la fecha validada.

```sql
-- Fase de expansión sobre datos existentes; no ejecutar desde este documento.
ALTER TABLE consulta ADD COLUMN fecha DATE;
-- Después de conciliación explícita y prueba de ausencia de NULL:
ALTER TABLE consulta ALTER COLUMN fecha SET NOT NULL;
```

Aceptación C2: alta con fecha distinta de la cita conserva la fecha recibida;
inserción sin fecha falla; fechas históricas sin evidencia bloquean el cierre;
rollback de la operación no deja consulta parcial. Las restricciones de no
futuro se validan en aplicación con reloj de la zona clínica; no CHECK dependiente
de una fecha de sistema que cambie entre ejecuciones.

## 2. MySQL: consulta sin cita

Decisión interna B: `consulta.cita_id` será nullable. Se conserva su FK y su UNIQUE:
una cita existente se usa como máximo una vez; múltiples consultas sin cita usan
NULL. El adaptador no creará citas artificiales.

```sql
ALTER TABLE consulta MODIFY COLUMN cita_id INT NULL;
```

Validar dentro de la transacción que cita y consulta pertenecen al mismo paciente
y profesional, cuando exista cita. La FK actual solo prueba existencia. Si hay
carrera por la misma cita, UNIQUE resuelve el conflicto; devolver CONFLICT sin
exponer el SQL. La fecha de consulta sigue siendo su columna DATE NOT NULL.

Aceptación C2: dos consultas sin cita son válidas; cita inexistente falla por FK;
segunda consulta con la misma cita falla por UNIQUE; cita de otro paciente se
rechaza en el adaptador y no deja registros parciales.

## 3. MySQL: relaciones explícitas diagnóstico → tratamiento → receta

Decisión interna B: conservar `consulta_diagnostico`, `tratamiento.consulta_id` y
`receta.consulta_id`; agregar vínculos verificables, sin inferir parentescos por
coincidencia de consulta al leer el historial.

- `consulta_diagnostico`: clave única `(consulta_id, diagnostico_id)` después de
  auditar duplicados; no eliminar duplicados silenciosamente. Añadir también
  UNIQUE `(consulta_id, id)` para referenciar una ocurrencia específica.
- El `id` externo de Diagnostico en MySQL será `consulta_diagnostico.id`, como
  string, nunca `diagnostico.id` del catálogo reutilizable. API-07 devuelve esa
  ocurrencia y API-08 la recibe: consulta y paciente quedan determinados sin
  pedir un selector adicional al navegador.
- `tratamiento.consulta_diagnostico_id`: FK compuesta junto con `consulta_id`
  hacia `(consulta_id, id)` de consulta_diagnostico. Impide asociar tratamiento
  a una ocurrencia perteneciente a otra consulta.
- `tratamiento`: clave única `(consulta_id, id)` como destino de la siguiente FK.
- `receta.tratamiento_id`: FK compuesta junto con `consulta_id` hacia tratamiento.
  Impide prescripción enlazada a tratamiento de otra consulta.

```sql
ALTER TABLE consulta_diagnostico
  ADD CONSTRAINT uq_consulta_diagnostico UNIQUE (consulta_id, diagnostico_id),
  ADD CONSTRAINT uq_ocurrencia_consulta UNIQUE (consulta_id, id);
ALTER TABLE tratamiento ADD COLUMN consulta_diagnostico_id INT NULL;
ALTER TABLE tratamiento
  ADD CONSTRAINT fk_tratamiento_origen
    FOREIGN KEY (consulta_id, consulta_diagnostico_id)
    REFERENCES consulta_diagnostico (consulta_id, id),
  ADD CONSTRAINT uq_tratamiento_consulta UNIQUE (consulta_id, id);
ALTER TABLE receta ADD COLUMN tratamiento_id INT NULL;
ALTER TABLE receta
  ADD CONSTRAINT fk_receta_origen
    FOREIGN KEY (consulta_id, tratamiento_id)
    REFERENCES tratamiento (consulta_id, id);
```

Estas columnas nacen nullable para preservar filas previas. La activación final
exige conciliación explícita y conversión a NOT NULL de ambos vínculos; no asignar
el primer diagnóstico o tratamiento encontrado. Si una consulta contiene varios
candidatos, requerir evidencia de asociación. No borrar historial no conciliado.
MySQL realiza commits implícitos con DDL: C2 debe separar expansión, conciliación
y restricciones; un ROLLBACK de aplicación no revierte ALTER TABLE. Respaldos y
reversión de esquema deben ensayarse antes de aplicar cambios al volumen local.

La receta común representa un renglón de medicamento. En MySQL, su ID externo
será `detalle_receta.id` como string y su tratamiento provendrá de la cabecera
`receta`. Una receta histórica con varios detalles produce varios DTOs con IDs
distintos, conservando sus datos. Para API-09 se crea cabecera y un detalle en
una transacción; no reutilizar una cabecera arbitraria. La fecha interna de la
cabecera procede del día clínico de la prescripción, no se inventa desde consulta.
La asociación y proyección concretas se probarán antes del adaptador C4.

Aceptación C2: relación cruzada entre consultas falla por FK; combinación válida
funciona; padre inexistente falla; un fallo al insertar detalle revierte cabecera;
una consulta con dos diagnósticos conserva ambas ramas sin mezclar tratamientos.
Un código de catálogo compartido por dos consultas produce dos IDs de ocurrencia
distintos; registrar tratamiento con uno de ellos nunca afecta la otra consulta.
En PostgreSQL el id externo sigue siendo diagnostico.id, que ya pertenece a un
solo origen. A deberá conservar identidad de ocurrencia equivalente en NoSQL.

## 4. D0-03: propuesta de rol laboratorista, pendiente A↔B

Proponer `laboratorista` como rol restringido a `laboratorio`, sin convertirlo en
`medico` ni conceder prescripción. Se habilita la cuenta solo si tiene identidad
profesional verificable. Perfil ausente o rol/institución incompatibles se rechazan.

| Operación | laboratorista propuesto |
|---|---|
| API-02 /me | Sí |
| API-03 listado | Sí, datos administrativos mínimos |
| API-04 alta de paciente | Sí, dentro de laboratorio |
| API-05 historial | Sí, dentro de laboratorio |
| API-06 consulta | Sí, registro de atención de laboratorio; paciente activo |
| API-07 diagnóstico clínico | No; requiere médico autorizado |
| API-08 tratamiento | No |
| API-09 receta | No |
| API-10 archivo | No; reservado al admin institucional |

Órdenes/muestras/resultados son especializaciones de A y no obtienen rutas
inventadas en las diez operaciones. Sus permisos deben acordarse antes de
implementarlas. Si A necesita API-07 para hallazgos de laboratorio, debe delimitar
semántica y permisos: no confundir un resultado analítico con diagnóstico clínico.

Con esta propuesta, el contexto interno de repositorio se denominaría profesional
validado; en hospital/pediatría se mapea a médico, en laboratorio al laboratorista.
No agregar `medico_id` ni `profesional_id` al cuerpo enviado por el navegador.
No cambia las ocho firmas de puerto. Requiere revisión de A porque aclara la
precondición de API-06 y la matriz anterior solo contemplaba cuatro roles.

## 5. D0-07: escritura concurrente y archivo

Propuesta contractual: después del commit de archivo no puede confirmarse una
nueva consulta, diagnóstico, tratamiento, receta ni escritura clínica especializada
para ese paciente. Una escritura que gana el bloqueo y confirma antes puede
quedar en el historial conservado. No basta comprobar estado al entrar a la vista.

Secuencia SQL que implementará B en C3/C4, con un único orden de bloqueo:

1. Resolver el paciente raíz desde el padre solicitado, dentro del repositorio
   institucional; ausencia/ajeno devuelve NOT_FOUND.
2. Bloquear paciente con `SELECT ... FOR UPDATE` en la misma conexión/transacción.
3. Para escritura clínica, exigir estado activo bajo bloqueo; de otro modo,
   CONFLICT. Revalidar la cadena de relaciones antes de insertar.
4. Para archivo, actualizar estado/motivo/fecha bajo ese mismo bloqueo. Repetición
   del mismo motivo conserva fecha; otro motivo devuelve CONFLICT.
5. Confirmar o revertir toda la operación y liberar el bloqueo. No realizar llamadas
   a otros motores dentro de esa transacción. Aplicar también a especializaciones.

Se usa una fila paciente por unidad de exclusión; las relaciones clínicas son
inmutables en este núcleo y no hay borrado físico. MySQL debe usar lectura de
bloqueo para estado, sin confiar en un snapshot anterior de lectura ordinaria.
SQL parametrizado, sin IDs interpolados. Un deadlock o timeout revierte todo;
reintentos deben estar acotados y no repetir un POST ya confirmado a ciegas.

Prueba obligatoria: dos conexiones y barreras controladas, no sleeps como única
sincronización. Probar ambas órdenes: archivo primero → escritura 409 sin fila
nueva; escritura primero → archivo conserva la fila confirmada; rollback del
escritor → archivo puede continuar sin filas parciales. Nunca un commit clínico
posterior al archivo basado en una comprobación previa sin bloqueo.

### Entrada que necesita resolver A para MongoDB y Firestore

Firestore debe leer el documento paciente en la misma transacción que crea o
actualiza los documentos clínicos, y archivo debe modificar ese documento.
Los reintentos deben revalidar activo, no reutilizar una lectura previa.
Es una condición contractual; A conserva el diseño e implementación del adaptador.

Mongo actual es standalone y el borrador #4 conserva pacientes y consultas en
documentos separados. Leer activo y luego insertar en consultas deja una carrera;
una actualización condicional solo en paciente tampoco hace atómico el insert
en otra colección. Un candado en memoria no coordina varios procesos Django.

Para mantener ese modelo y la garantía, B propone evaluar con A un replica set
local con transacciones multidocumento en un PR de infraestructura exclusivo,
dueño y evidencia acordados. La transacción de escritura debe además modificar
un contador/versión del paciente activo para competir con archivo: **solo leer
paciente dentro de una transacción snapshot no garantiza exclusión con archivo**.
Si A elige otra estructura de agregado, debe demostrar la misma garantía sin
prometer atomicidad entre documentos independientes. B no modifica Compose,
validadores Mongo ni decisiones de embebido/referencia por su cuenta.

Pendiente de A: elegir mecanismo viable y demostrar la carrera en su motor antes
de marcar D0-07 ratificada. El seed preparatorio y su idempotencia no acreditan
esta garantía clínica. No se bloquean sus pruebas independientes de integración
Mongo ni export/import Firestore mientras se resuelve la decisión.

## 6. Corrección basal de salud

PR GitHub #5, rama `fix/pablo-salud-resultado-falso`, commit
`030464b89095546a0c230534e46164c1ff65adda`: el servicio respeta el booleano
retornado por health_check. Cuatro pruebas nuevas incluyen False por cada motor,
todos conectados, excepción aislada y respuesta HTTP. Suite completa: **12 OK**;
Django check y Compose config sin incidencias. PR separado, sin merge automático.

## 7. Handoff verificable

| Punto reportado por A | Salida de B | Estado |
|---|---|---|
| Fecha consulta PostgreSQL | DATE explícita y expansión/conciliación/restricción definidas | Diseño B resuelto; implementación C2 pendiente |
| Cita MySQL | Nullable, conservar FK/UNIQUE, validar paciente/profesional | Diseño B resuelto; implementación C2 pendiente |
| Relaciones MySQL | FKs compuestas, conciliación histórica y proyección por detalle | Diseño B resuelto; implementación C2 pendiente |
| Rol laboratorista | Matriz mínima sin prescripción, contexto profesional | Propuesta de contrato pendiente A↔B |
| Protección tras archivo | Bloqueo raíz SQL, requisito transaccional NoSQL y prueba concurrente | SQL diseñado; decisión Mongo/aceptación A pendientes |
| Salud devuelve False | PR #5 con pruebas aprobadas | Pendiente revisión e integración |

La base común continúa siendo f35207d hasta un merge acordado. PR #3 y #4 no
se fusionaron ni modificaron. Este documento no cambia las aprobaciones históricas
de DECISIONES.md ni declara endpoints, migraciones o garantías aún no probadas.

## Validación de esta rama documental

Antes de commit y PR: `git diff --check` sin errores; en el contenedor backend,
`python manage.py check` sin incidencias y `python manage.py test apps.historiales`
con **8 pruebas OK**. Esta rama parte directamente de f35207d y no incluye las
cuatro pruebas del PR #5. La diferencia completa respecto de main es este único
documento. El DDL se revisó contra init.sql, pero no se ejecutó: no se afirma
que haya migraciones aplicadas ni pruebas SQL o de concurrencia aprobadas.

## Continuación tras revisión A-C0 del PR #7

La revisión publicada por Jennifer en #7 acepta como dirección el rol restringido
y transacciones Mongo sobre replica set, pero mantiene pendiente la reserva de
infraestructura y la ratificación. La identidad de ocurrencia MySQL de la sección
3 se precisó para resolver su observación; no se aprobó unilateralmente un cambio
de contrato. La corrección de salud #5 ya quedó integrada en main f671245.

### Semántica propuesta de q para acordar con A

`q` es un prefijo literal de identificación, nombres o apellidos, combinados por
OR. Se recortan espacios exteriores, se normaliza Unicode NFC y se convierten
query y campos con lower antes de comparar. No se eliminan acentos; `%`, `_`,
`*` y barras se tratan como caracteres literales, nunca comodines o regex. Consulta
vacía o solo espacios equivale a listado sin filtro. Máximo 100 caracteres después
de normalizar; límite/offset y orden siguen los del candidato inicial.

Ejemplos: q=DEMO- encuentra identificacion DEMO-0001; q=pac encuentra nombres
Paciente; q=aci no encuentra Paciente; q=% no lista todos los registros. Mantener
apellidos/nombres como campos separados, sin prometer búsqueda por palabras en
cualquier posición. La semántica se aplica antes de count y paginación: no filtrar
solo la página ya obtenida. A debe revisar índices/proyección Firestore para este
prefijo; el mecanismo interno es de cada adaptador, el resultado debe coincidir.

Esto precisa la propuesta anterior de búsqueda sin fijar implementación. Requiere
confirmación A y pruebas equivalentes; no modificar mocks ni esquemas NoSQL desde B.

### Suministro propuesto del catálogo de medicamentos

Un fixture incrustado en React no garantiza IDs válidos en la base autenticada.
Se propone la extensión **CAT-01**, GET `/api/medicamentos/`, fuera de las diez
operaciones iniciales, para resolver referencias de API-09. No se implementa
ni se anuncia disponible hasta aprobar explícitamente esta extensión con A.

- Institución derivada solo del usuario autenticado. Permiso de lectura para
  admin y medico de esa institución; laboratorista sin prescripción no necesita
  este catálogo en el flujo común. Usuario sin sesión 401; rol insuficiente 403.
- Query q opcional, limit y offset con las mismas reglas del listado de pacientes;
  q compara prefijo literal del nombre de medicamento, sin campos clínicos.
- Respuesta 200 `{count,limit,offset,results}`; cada elemento tiene `id` string,
  `nombre` y `presentacion` string o null. Orden por nombre normalizado y luego id.
  No contiene stock, precios, motor ni credenciales. Solo medicamentos habilitados.
- PostgreSQL proyecta nombre_comercial; MySQL nombre. Si un esquema no dispone de
  estado, el catálogo cargado por seed se considera habilitado; no inventar estado
  persistido. Las proyecciones de A siguen bajo su propiedad.
- Dataset DEMO por institución con alias estables de seed; la UI usa el ID externo
  que devuelve el catálogo, no un ID numérico supuesto ni un alias sin resolver.
  API-09 valida existencia de medicamento en la misma institución y transacción.
- Caso vacío: results=[], count=0. Un medicamento inexistente en API-09 devuelve
  404. El catálogo solo es lectura; no añade CRUD, compras ni control farmacéutico.

Ejemplo sintético candidato:

```json
{"count":1,"limit":20,"offset":0,"results":[{"id":"DEMO-M-1","nombre":"Medicamento DEMO (no administrar)","presentacion":null}]}
```

A debe confirmar que CAT-01 cubre la UI y sus adaptadores; si se acuerda otra
forma de suministro, registrar la alternativa antes de ratificar. Hasta entonces
se conservan los diez fixtures iniciales, sin agregar rutas ficticias a React.
