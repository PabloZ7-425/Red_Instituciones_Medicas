# Auditoría de cobertura — implementacion

Jennifer, 22 de octubre de 2026, America/Guatemala.
Fuente auditada: **177935fc87223172fc8a574fc9bfed6822254bae**, sin cambios de
aplicación pendientes al iniciar la revisión. Es descendiente de main 4dccf85.
La auditoría añade documentos y sondas de lectura; **no corrige ni despliega** la
aplicación, no cambia main, feature/jennifer, feature/pablo ni sus PR.

> **Seguimiento:** AUC-01..04 corregidos en `implementacion`. Ver [cierre con evidencia](CIERRE_AUC_01_04.md). AUC-05 corregida con [regresión aislada](CIERRE_AUC_05.md). AUC-06 implementada con [SQL real validado; navegador pendiente](CIERRE_AUC_06.md). AUC-07..12 continúan abiertos. El dictamen y los conteos siguientes describen la revisión original, conservada como antecedente.

## Dictamen original

**El alcance propuesto todavía no está cerrado.** Existe una base operativa amplia,
pero se encontraron cuatro bloqueos funcionales prioritarios y pendientes de
estados, recorridos guiados y verificación. Las 60 pruebas backend, 58 cliente y
11 recorridos HTTP registrados sí pasaron en su ejecución; no cubrían los casos
negativos encontrados aquí ni certificaban todas las funciones administrativas.

La matriz completa está en [MATRIZ_COBERTURA.md](MATRIZ_COBERTURA.md) y
[MATRIZ_COBERTURA.csv](MATRIZ_COBERTURA.csv): tabla → función → pantalla → permiso
→ prueba → estado/pendiente, incluyendo tablas técnicas y legado justificado.

| Inventario declarado | B: base con evidencia | P: parcial / por cerrar | T: técnico / legado |
|---|---:|---:|---:|
| Hospital, 27 tablas | 6 | 19 | 2 |
| Pediatría, 37 tablas | 13 | 19 | 5 |
| Laboratorio, 13 colecciones v2 + 6 legadas | 7 | 4 | 8 |
| Odontología, 12 colecciones v2 | 7 | 3 | 2 |
| Total, 95 destinos declarados | **33** | **45** | **17** |

La identidad Django se evalúa aparte: User, PerfilInstitucional, Profesional y
las tablas internas del framework. No se suman al inventario de motores clínicos.
El manifiesto tiene 75 entradas, pero 74 destinos distintos: diagnostico_ingreso
comparte la tabla diagnostico. Las colecciones diagnosticos/recetas y las reservas
internas se añadieron expresamente a la matriz, aunque no estén en el manifiesto.

**B no significa 100% del proceso terminado.** Solo acredita la función y evidencia
indicadas en esa fila. P agrupa tanto defectos como falta de prueba dirigida; no
significa que 45 tablas carezcan de implementación. T evita exigir pantallas de
contraseñas antiguas, reservas o evidencias de migración. No se infiere un porcentaje
de terminación a partir de estos conteos ni se afirma inventariar un servidor vivo.

## Hallazgos prioritarios originales — corregidos en el seguimiento

### AUC-01 · P1 · Cama ocupada produce error interno en el traslado

**Confirmado mediante sonda aislada.** La consulta obtiene id_ingreso, pero la
comprobación siguiente accede a id_cirugia. Si la cama está ocupada, aparece
KeyError en lugar de Conflicto/409. El ensayo nativo anterior solo trasladó a una
cama libre, por eso pasó.

Fuente: [repository.py, línea 317](../../backend/apps/operaciones/repository.py#L317).
Cierre: rechazar correctamente una cama ocupada, sin alterar ingreso/movimientos;
probar cama libre, ocupada y dos traslados concurrentes al mismo destino.

### AUC-02 · P1 · Alta hospitalaria deja abierto el movimiento de cama

**Confirmado por revisión del código y esquema.** El traslado crea un movimiento
con fecha_hora_fin nula. dar_alta cierra ingreso_hospitalario, pero no el movimiento
vigente, y el esquema no declara un trigger que lo complete. El inventario de
movimientos puede seguir indicando ocupación después del alta.

Fuentes: [repository.py, línea 358](../../backend/apps/operaciones/repository.py#L358),
[dar_alta, línea 370](../../backend/apps/historiales/infrastructure/adapters/postgres_clinical.py#L370).
Cierre: cerrar ingreso y movimiento de forma atómica y cronológicamente coherente;
probar ingreso→traslado→alta, repetición y rollback.

### AUC-03 · P1 · Tratamiento de ingreso no puede continuar a receta/farmacia

**Confirmado por trazado de rutas, interfaz y consultas SQL.** Se puede crear un
diagnóstico de ingreso y un tratamiento desde operaciones. Sin embargo, la API
clínica de recetas resuelve el tratamiento mediante JOIN consulta; un diagnóstico
que solo tiene id_ingreso queda fuera y devuelve 404. Prescripciones no tiene
alta operativa y el expediente solo dibuja diagnósticos de consulta. No existe un
recorrido accesible completo de tratamiento hospitalario→receta→despacho.

Fuentes: [resolución de padres, línea 207](../../backend/apps/historiales/infrastructure/adapters/postgres_clinical.py#L207),
[historial, línea 161](../../backend/apps/historiales/infrastructure/adapters/postgres_clinical.py#L161),
[definiciones de recursos](../../backend/apps/operaciones/resources.json).
El test nativo receta un tratamiento ambulatorio y registra después el diagnóstico
de ingreso; no acredita una receta originada en ese ingreso.
Cierre: soportar ambos orígenes sin fabricar una consulta y probar el recorrido
hospitalario completo por API e interfaz.

### AUC-04 · P1 · Reclamación no exige que autorización y factura correspondan a la misma consulta

**Confirmado mediante sonda aislada de reglas.** Se comprueban paciente común,
póliza, aprobación y montos individuales; no se compara consulta_id de la
factura con consulta_id de la autorización. Dos consultas del mismo paciente
pueden quedar mezcladas. Tampoco se observa un control del acumulado reclamado
por factura; cada reclamo se compara aisladamente con total_seguro.

Fuente: [repository.py, línea 338](../../backend/apps/operaciones/repository.py#L338).
La sonda confirma la primera omisión; la del acumulado se identifica por revisión,
sin afirmar una ejecución real de reclamos duplicados.
Cierre: consistencia factura/consulta/póliza/autorización y saldo reclamable,
con pruebas de misma persona/diferente consulta y reclamos parciales concurrentes.

## Pendientes de cierre funcional y experiencia

### AUC-05 · P2 · Ediciones parciales no revalidan siempre la cronología completa

**Seguimiento actual:** corregida con [pruebas aisladas](CIERRE_AUC_05.md). La descripción siguiente conserva el hallazgo original.

**Confirmado mediante sonda aislada.** validate(partial=True) compara solo las
fechas incluidas en el PATCH; después se mezclan con el registro guardado y no se
revalida el intervalo en todos los recursos. Una póliza puede recibir fecha_fin
anterior a su fecha_inicio existente. No hay CHECK equivalente en su tabla.

Fuentes: [catalog.py, línea 102](../../backend/apps/operaciones/catalog.py#L102),
[merge en repository.py, línea 184](../../backend/apps/operaciones/repository.py#L184).
Cierre: validar el estado combinado, incluyendo campos no editados; probar PATCH
de un único extremo, ambos extremos y null opcional.

### AUC-06 · P2 · Ciclo de factura/pago queda parcialmente definido

**Seguimiento actual:** implementado el ciclo de emisión, pago parcial/total,
anulación y reversión con saldos por pagador. Ver [pruebas y límites](CIERRE_AUC_06.md).
La descripción siguiente conserva el hallazgo original; SQL real está verificado y falta el recorrido financiero E2E en navegador.

**Parcialmente reproducido.** Un pago de 12 sobre 20 no cambia el estado de la
factura, aunque PostgreSQL define Parcial. El código solo marca Pagada cuando
coincide con el total; mientras tanto sigue Pendiente y puede aceptar conceptos
nuevos. En pediatría Pagada se decide por total_paciente, sin resolver el cobro de
la parte del seguro. No hay tarea explícita para emisión, anulación o reversión.

Fuente: [repository.py, línea 375](../../backend/apps/operaciones/repository.py#L375).
Cierre: acordar estados y qué se permite después de un pago, separar saldo de
paciente/seguro y probar pago parcial→total y los cierres/anulaciones aplicables.
No implica añadir SAT ni pasarela bancaria al proyecto.

### AUC-07 · P2 · Faltan transiciones completas en estados clínicos y administrativos

**Confirmado por interfaz/contratos; prueba dirigida pendiente.** Cirugía, examen,
autorización y reclamación ofrecen edición de estado, pero no una máquina de
transiciones completa con condiciones por paso. En laboratorio los resultados y
en odontología los procedimientos admiten estado inicial, pero no tienen tarea
ni PATCH para pasar un registro pendiente a finalizado/realizado: crear otro
registro no resuelve por sí solo el ciclo del anterior.

Fuentes: [resources.json](../../backend/apps/operaciones/resources.json),
[rutas especializadas](../../backend/apps/historiales/presentation/urls.py),
[reglas operativas](../../backend/apps/operaciones/repository.py#L262).
Cierre: definir y probar transiciones permitidas, terminales y cancelaciones por
institución, sin sobrescribir historia clínica de forma arbitraria.

### AUC-08 · P2 · La evidencia no cubre cada operación y rol de la matriz

**Confirmado por inspección de pruebas.** BO edita medicamentos en cuatro motores,
pero en Agenda solo abre y cancela el formulario. No prueba Guardar cita,
reprogramar ni Atender cita desde la pantalla. NH/NP sí vinculan una cita a la
consulta por repositorio SQL; eso no prueba el nuevo botón del navegador ni ese
circuito en los dos motores documentales. Tampoco se ejecutan edición/baja de cada
catálogo ni todos los cambios de estado y combinaciones de rol/recurso.

Fuentes: [browser-operations.mjs, línea 110](../../frontend/tests/browser-operations.mjs#L110),
[tests operativos](../../backend/apps/operaciones/tests.py).
Cierre: pruebas dirigidas de los circuitos faltantes y matriz de permisos positivos
/negativos por tipo de tarea. No contar un alta nativa como CRUD/E2E completo.

### AUC-09 · P2 · Flujo guiado y administración de usuarios requieren ajustes

**Confirmado por lectura de componentes.** El botón Continuar cambia la sección,
pero no conserva automáticamente el padre recién creado (factura, examen, etc.).
El usuario debe buscarlo otra vez. Algunas tareas de solo lectura devuelven al
expediente sin abrir directamente la acción adecuada. En Usuarios y permisos se
pueden mantener a la vez el formulario de alta y el de vínculo profesional; el
listado corta en 200 usuarios sin búsqueda/paginación.

Fuentes: [OperationsWorkspace, línea 96](../../frontend/src/operations/OperationsWorkspace.jsx#L96),
[AccountsPanel](../../frontend/src/operations/AccountsPanel.jsx),
[AccountsView.get](../../backend/apps/operaciones/accounts.py#L27).
Cierre: conservar paciente/padre/tarea entre pasos, garantizar editor único también
en cuentas y completar la navegación del listado. Probar cancelación y recuperación
sin pérdida silenciosa de datos ingresados.

### AUC-10 · P2 · Revisar coherencia de desactivación profesional entre motores e identidad

**Vínculo causal confirmado; comportamiento completo pendiente de prueba.** B2
usa Profesional.habilitado para construir el contexto. El catálogo operativo
NoSQL se modifica en otro documento y no sincroniza ese espejo. A diferencia de
los proveedores SQL, la escritura clínica NoSQL no vuelve a consultar ese catálogo
profesional. Desactivar el documento operativo no demuestra haber revocado la
capacidad clínica del usuario vinculado.

Fuentes: [principal.py](../../backend/apps/identidad/principal.py),
[NoSQL _authorize](../../backend/apps/historiales/infrastructure/adapters/mongo_adapter.py#L58),
[guardado operativo](../../backend/apps/operaciones/repository.py#L241).
Cierre: definir el efecto de cada desactivación y probarlo en la sesión existente
y siguiente petición, para las cuatro instituciones. No se propone otra
fuente de autenticación ni cambiar cuentas de otro entorno durante esta auditoría.

### AUC-11 · P2 · Falta la comparación de eficiencia comprometida

No hay registro comparativo de pasos/campos digitados antes/después. Hay evidencia
de precarga, selectores y cálculos; no de ahorro de pasos ni tiempo medido.
Cierre: medir los seis recorridos acordados con criterios idénticos: atención,
vacuna, ingreso, traslado, resultado y pago. Registrar pasos, campos manuales,
errores/retrocesos y tiempo si se mide. No inventar porcentajes.

### AUC-12 · Pendiente de integración · Entorno compartido y actualización existentes

La ampliación solo tiene ensayo aislado de bases nuevas. El upgrade MySQL requiere
seleccionar manualmente ALTER ausentes; no hay evidencia del upgrade completo
sobre una copia poblada con datos/roles reales de entrega ni de su repetición.
Cierre: respaldo/restauración verificada, ensayo sobre copia existente,
permisos/esquema, sesión y recorridos con cada rol; conservar estado y versión.
Esto es un pendiente de habilitación, no una razón para modificar datos compartidos
sin inventario ni para contar el ensayo de otra versión como este despliegue.

## Método y evidencia adicional

Se revisaron schemas SQL, modelos/validadores de los dos motores documentales,
resources.json, autorización, repositorios, rutas, componentes y pruebas. Se
contrastaron los documentos con los logs previos disponibles de ops-certified-03
(fuente 7679e3c; 177935f solo añadió documentación de esa aplicación).

Se ejecutaron cuatro sondas locales de lectura/validadores, sin clientes de base,
sin sesión real y sin mutar aplicación o datos. Reproducción:

```bash
PYTHONPATH=backend python docs/implementacion/auditoria_comprobaciones.py
```

[Resultado de las sondas](AUDITORIA_COMPROBACIONES.json): AUC-01, AUC-05, primera
parte de AUC-04 y comportamiento parcial de AUC-06. El resto se identifica como
revisión estática o prueba pendiente; no se presenta como integración ejecutada.
El JSON conserva los defectos de la fuente auditada. AUC-01, AUC-04, AUC-05 y AUC-06 cuentan con correcciones posteriores y pruebas enlazadas; las sondas históricas no son tests de aceptación que legitimen
esos comportamientos ni reemplazan los tests de regresión que deberán añadirse
al corregirlos.

## Orden recomendado

1. **Hecho:** corregir AUC-01..04 con pruebas de regresión; ver el cierre enlazado.
2. Completar cronología y ciclos de estado/facturación (AUC-05..07 y AUC-10).
3. Cerrar los recorridos por interfaz y permisos (AUC-08), con padres conservados
   y un editor por tarea (AUC-09).
4. Medir eficiencia (AUC-11) y validar la habilitación en copia compartida (AUC-12).
5. Actualizar esta matriz con prueba y SHA por cierre; recién entonces evaluar
   otro PR. Esta auditoría no autoriza merge ni declara la ampliación terminada.
