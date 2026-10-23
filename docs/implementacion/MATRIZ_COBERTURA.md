# Matriz de cobertura auditada

Fuente original: implementacion `177935fc87223172fc8a574fc9bfed6822254bae`.
Fuente del primer cierre: `a65fabd0be60ee0146865348e8918c7b0ed79318`.
Actualizada con los cierres [AUC-01..04](CIERRE_AUC_01_04.md), [AUC-05](CIERRE_AUC_05.md), [AUC-06](CIERRE_AUC_06.md), [AUC-07](CIERRE_AUC_07.md), [AUC-08](CIERRE_AUC_08.md) y [AUC-09](CIERRE_AUC_09.md). [AUC-10](CIERRE_AUC_10.md) implementado, [AUC-11](CIERRE_AUC_11.md) medido con control manual; [AUC-12](PREPARACION_ENTREGA_AUC_12.md) conserva el pendiente compartido.
Último bloque: aplicación `7cf7603`, herramientas `1f3a6a6`; ver [evidencia AUC-10..12](CIERRE_AUC_10_12_VERIFICACION.json).
Esta matriz sustituye el inventario parcial anterior como evaluación de cobertura.
No declara 100% funcionalidad por tener una tabla en resources.json.

**B:** función base implementada y con la evidencia indicada; no certifica todos
sus casos, aceptación de usuario ni despliegue. **P:** implementación parcial o
hallazgo pendiente de cierre. **T:** técnico/legado con tratamiento explícito,
sin exigir un formulario clínico artificial.

Permisos: A admin, M médico, S secretaría, E enfermería, L laboratorista.
API08 comprueba los permisos HTTP de las 1,236 combinaciones declaradas; UI08 verifica recorridos representativos con sesiones reales.
CORE exige contexto institucional, rol y profesional en las escrituras clínicas;
secretaría tiene acceso administrativo a pacientes/tutores, no al historial médico.

Pruebas y lectura correcta:

- **REV10:** cuatro escenarios nativos/API de revocación y reactivación, misma sesión/nuevo login y B2; `test_professional_revocation.py`.

- **API09/UI09:** `test_guided.py` y `browser-guided.mjs`: cuentas completas más allá de 200, búsqueda, editor único y continuidad de tareas. Ver límites del cierre AUC-09.

- **API08:** matriz fija de 75 recursos y 17 combinaciones institución/rol; proveedor sustituido para aislar autorización.
- **UI08:** 72 escenarios de navegador con API y persistencia reales; 24 catálogos, agenda, caja, estados y cuentas. Ver alcance y límites en el cierre AUC-08.

- **T07:** `test_transitions.py`: grafos/terminales y API, cuatro escenarios SQL y tres escenarios que recorren cada motor documental. Concurrencia, archivo, conservación de campos/versión y rollback. Incluidos en las 54 pruebas finales; no acredita recorridos en navegador.
- **F06:** `test_finance.py` y `verify_finance.py`: SQL aislado/rollback, API con identidad SQLite y dos escenarios nativos aprobados en PostgreSQL/MySQL. La ejecución de 39 incluye ocho escenarios nativos en total y las regresiones anteriores. No acredita el recorrido financiero E2E en navegador.
- **NAUC:** `test_audit_blockers.py`, cuatro regresiones aisladas y cuatro escenarios SQL nativos; camas/concurrencia, alta/rollback, receta hospitalaria y reclamaciones/saldo.
- **NH:** NativeOperationsTests.test_hospital_full_operational_chain.
- **NP:** NativeOperationsTests.test_pediatrics_full_operational_chain.
- **ND:** NativeOperationsTests.test_documental_catalog_agenda_and_payments.
- **BC:** browser-real.mjs, flujo común/especializado en las cuatro instituciones.
- **BO:** browser-operations.mjs: alta/edición de medicamento, búsqueda, apertura
  y cancelación de formulario de cita, vínculo profesional y logout. No prueba
  todas las pantallas administrativas ni la atención de una cita. El cierre añade el recorrido hospitalario completo hasta receta/despacho/alta.
- **CN:** contrato NoSQL, test_clinical_nosql.py (49 pruebas, solo Mongo/Firestore).
  En filas SQL, CN no se toma como prueba SQL: B2/BC/NH/NP son las referencias.

Las tres pruebas nativas operativas son escenarios largos; crear una fila dentro
de uno no equivale a probar edición, baja, cambios de estado y todos los roles.
Las evidencias de ejecución anteriores se conservaron en VALIDACION.md. Esta
auditoría ejecutó sondas locales adicionales, no repitió el despliegue ni las suites.

Inventario físico definido: PostgreSQL 27 tablas, MySQL 37 tablas, Mongo v2 13
colecciones más 6 legadas y Firestore v2 12 colecciones (v1 coexiste en seis de
ellas). Estado actualizado: **78 B, 0 P y 17 T**; no equivale a un porcentaje de aceptación. Total 95 filas; no es un conteo de un servidor en vivo. Las tablas Django
se tratan aparte al final. El manifiesto tiene 75 entradas y 74 destinos: la
entrada hospitalaria diagnostico_ingreso comparte tabla diagnostico.

## hospital

| Tabla/colección | Función / pantalla | Permiso | Evidencia | Estado y pendiente |
|---|---|---|---|---|
| especialidad | Especialidades (alta y edición)<br>Catálogos → Especialidades | Lee: S,A,M,E; alta/edición: A | NH, API08, UI08 | B · Función base verificada en AUC-08; aceptación/entorno pendientes |
| medico | Profesionales médicos (alta y edición)<br>Catálogos → Profesionales médicos | Lee: S,A,M,E; alta/edición: A | NH, API08, UI08, REV10 | B · Función base verificada en AUC-08; aceptación/entorno compartido pendientes |
| enfermero | Personal de enfermería (alta y edición)<br>Catálogos → Personal de enfermería | Lee: S,A,M,E; alta/edición: A | NH, API08, UI08 | B · Función base verificada en AUC-08; aceptación/entorno pendientes |
| pabellon_edificio | Pabellones (alta y edición)<br>Catálogos → Pabellones | Lee: S,A,M,E; alta/edición: A | NH, API08, UI08 | B · Función base verificada en AUC-08; aceptación/entorno pendientes |
| habitacion | Habitaciones (alta y edición)<br>Catálogos → Habitaciones | Lee: S,A,M,E; alta/edición: A | NH, API08, UI08 | B · Función base verificada en AUC-08; aceptación/entorno pendientes |
| cama | Camas (alta y edición)<br>Catálogos → Camas | Lee: S,A,M,E; alta/edición: A | NH, NAUC, API08, UI08 | B · Función base verificada en AUC-08; aceptación/entorno pendientes |
| quirofano | Quirófanos (alta y edición)<br>Catálogos → Quirófanos | Lee: S,A,M,E; alta/edición: A | NH, API08, UI08 | B · Función base verificada en AUC-08; aceptación/entorno pendientes |
| paciente | Pacientes (alta clínica y consulta)<br>Atención y seguimiento → Pacientes; Pacientes y expedientes | Lee: A,M,S,E; escribe: API clínica con permisos CORE | NH, BC | B · Falta aceptación de usuario/entorno; sin defecto dirigido identificado en esta función base |
| ingreso_hospitalario | Ingresos hospitalarios (alta clínica y consulta)<br>Hospitalización → Ingresos hospitalarios; Pacientes y expedientes | Lee: A,M,E; escribe: API clínica con permisos CORE | NH, BC, NAUC, BO | B · AUC prioritarios cerrados; ver alcance del cierre |
| movimiento_cama | Traslados de cama (alta)<br>Hospitalización → Traslados de cama | Lee: A,M,E; alta: A,M | NH, NAUC | B · AUC prioritarios cerrados; ver alcance del cierre |
| emergencia | Emergencias y triaje (alta)<br>Hospitalización → Emergencias y triaje | Lee: A,M,E; alta: A,M | NH | B · Falta aceptación de usuario/entorno; sin defecto dirigido identificado en esta función base |
| cita | Agenda de citas (alta y edición)<br>Agenda → Agenda de citas | Lee: A,M,S; alta/edición: S,A,M | NH (BO solo abre/cancela formulario; no guarda ni atiende), API08, UI08 | B · Función base verificada en AUC-08; aceptación/entorno pendientes |
| consulta | Consultas (alta clínica y consulta)<br>Atención y seguimiento → Consultas; Pacientes y expedientes | Lee: A,M,E; escribe: API clínica con permisos CORE | NH, BC | B · Falta aceptación de usuario/entorno; sin defecto dirigido identificado en esta función base |
| signos_vitales | Signos vitales (alta)<br>Hospitalización → Signos vitales | Lee: A,M,E; alta: A,M,E | NH | B · Falta aceptación de usuario/entorno; sin defecto dirigido identificado en esta función base |
| diagnostico | Diagnósticos (alta clínica y consulta); incluye tarea diagnostico_ingreso<br>Atención y seguimiento → Diagnósticos; Hospitalización → Diagnósticos de hospitalización; Pacientes y expedientes | Lee: A,M,E; escribe: API clínica con permisos CORE | NH, BC, NAUC, BO | B · AUC prioritarios cerrados; ver alcance del cierre |
| cirugia | Cirugías (alta y edición)<br>Hospitalización → Cirugías | Lee: A,M,E; alta/edición: A,M | NH, T07, API08, UI08 | B · Función base verificada en AUC-08; aceptación/entorno pendientes |
| equipo_quirurgico | Equipo quirúrgico (alta)<br>Hospitalización → Equipo quirúrgico | Lee: A,M,E; alta: A,M | NH | B · Falta aceptación de usuario/entorno; sin defecto dirigido identificado en esta función base |
| tratamiento | Tratamientos (alta)<br>Atención y seguimiento → Tratamientos; Pacientes y expedientes | Lee: A,M,E; alta: A,M | NH, BC, NAUC, BO | B · AUC prioritarios cerrados; ver alcance del cierre |
| medicamento | Medicamentos (alta y edición)<br>Catálogos → Medicamentos | Lee: S,A,M,E; alta/edición: A | NH, BO | B · Falta aceptación de usuario/entorno; sin defecto dirigido identificado en esta función base |
| receta_prescripcion | Prescripciones de consulta e ingreso (alta clínica/operativa y consulta)<br>Atención y seguimiento → Prescripciones; Pacientes y expedientes | Lee: A,M,E; alta: A,M; API clínica con permisos CORE | NH, BC, NAUC, BO | B · AUC prioritarios cerrados; ver alcance del cierre |
| despacho_farmacia | Despachos de farmacia (alta)<br>Farmacia → Despachos de farmacia | Lee: A,M,E; alta: A,M | NH, NAUC, BO | B · AUC prioritarios cerrados; ver alcance del cierre |
| aplicacion_enfermeria | Administración de medicamentos (alta)<br>Farmacia → Administración de medicamentos | Lee: A,M,E; alta: A,M,E | NH, NAUC | B · AUC prioritarios cerrados; ver alcance del cierre |
| factura | Facturas (alta)<br>Caja y seguros → Facturas | Lee: A,M,S; alta: A,S | NH, F06, API08, UI08 | B · Función base verificada en AUC-08; aceptación/entorno pendientes |
| detalle_factura | Conceptos de factura (alta)<br>Caja y seguros → Conceptos de factura | Lee: A,M,S; alta: A,S | NH, F06, API08, UI08 | B · Función base verificada en AUC-08; aceptación/entorno pendientes |
| pago | Pagos (alta)<br>Caja y seguros → Pagos | Lee: A,M,S; alta: A,S | NH, F06, API08, UI08 | B · Función base verificada en AUC-08; aceptación/entorno pendientes |
| usuario | Legado de identidad preservado; acceso vigente sustituido por B2<br>Usuarios y permisos (B2), sin editar tablas heredadas | Sin acceso de contraseña heredada desde API; mantenimiento con responsable | B2/definiciones y fuentes de mantenimiento; no nueva certificación de migración | T · Preservar; no crear autenticación paralela |
| hospital_schema_version | Reserva de unicidad o control de mantenimiento<br>Sin formulario clínico; mantenimiento/alta transaccional | Sin acceso de contraseña heredada desde API; mantenimiento con responsable | B2/definiciones y fuentes de mantenimiento; no nueva certificación de migración | T · Verificar en habilitación; AUC-12 |

## pediatrico

| Tabla/colección | Función / pantalla | Permiso | Evidencia | Estado y pendiente |
|---|---|---|---|---|
| especialidad | Especialidades (alta y edición)<br>Catálogos → Especialidades | Lee: S,A,M,E; alta/edición: A | NP, API08, UI08 | B · Función base verificada en AUC-08; aceptación/entorno pendientes |
| medico | Profesionales médicos (alta y edición)<br>Catálogos → Profesionales médicos | Lee: S,A,M,E; alta/edición: A | NP, API08, UI08, REV10 | B · Función base verificada en AUC-08; aceptación/entorno compartido pendientes |
| paciente | Pacientes (alta clínica y consulta)<br>Atención y seguimiento → Pacientes; Pacientes y expedientes | Lee: A,M,S,E; escribe: API clínica con permisos CORE | NP, BC | B · Falta aceptación de usuario/entorno; sin defecto dirigido identificado en esta función base |
| tutor | Tutores (alta y edición)<br>Catálogos → Tutores | Lee: S,A,M,E; alta/edición: A,S | NP, API08, UI08 | B · Función base verificada en AUC-08; aceptación/entorno pendientes |
| paciente_tutor | Vincular tutor existente (alta)<br>Atención y seguimiento → Vincular tutor existente | Lee: A,M,S; alta: A,M,S | NP | B · Falta aceptación de usuario/entorno; sin defecto dirigido identificado en esta función base |
| cita | Agenda de citas (alta y edición)<br>Agenda → Agenda de citas | Lee: A,M,S; alta/edición: S,A,M | NP (BO solo abre/cancela formulario; no guarda ni atiende), API08, UI08 | B · Función base verificada en AUC-08; aceptación/entorno pendientes |
| consulta | Consultas (alta clínica y consulta)<br>Atención y seguimiento → Consultas; Pacientes y expedientes | Lee: A,M,E; escribe: API clínica con permisos CORE | NP, BC | B · Falta aceptación de usuario/entorno; sin defecto dirigido identificado en esta función base |
| diagnostico | Diagnósticos (alta clínica y consulta)<br>Atención y seguimiento → Diagnósticos; Pacientes y expedientes | Lee: A,M,E; escribe: API clínica con permisos CORE | NP, BC | B · Falta aceptación de usuario/entorno; sin defecto dirigido identificado en esta función base |
| consulta_diagnostico | Diagnósticos de consulta (alta clínica y consulta)<br>Atención y seguimiento → Diagnósticos de consulta; Pacientes y expedientes | Lee: A,M,E; escribe: API clínica con permisos CORE | NP, BC | B · Falta aceptación de usuario/entorno; sin defecto dirigido identificado en esta función base |
| tratamiento | Tratamientos (alta clínica y consulta)<br>Atención y seguimiento → Tratamientos; Pacientes y expedientes | Lee: A,M,E; escribe: API clínica con permisos CORE | NP, BC | B · Falta aceptación de usuario/entorno; sin defecto dirigido identificado en esta función base |
| vacuna | Vacunas (alta y edición)<br>Catálogos → Vacunas | Lee: S,A,M,E; alta/edición: A | NP, API08, UI08 | B · Función base verificada en AUC-08; aceptación/entorno pendientes |
| aplicacion_vacuna | Aplicaciones de vacunas (alta clínica y consulta)<br>Atención y seguimiento → Aplicaciones de vacunas; Pacientes y expedientes | Lee: A,M,E; escribe: API clínica con permisos CORE | NP, BC | B · Falta aceptación de usuario/entorno; sin defecto dirigido identificado en esta función base |
| receta | Recetas (alta clínica y consulta)<br>Atención y seguimiento → Recetas; Pacientes y expedientes | Lee: A,M,E; escribe: API clínica con permisos CORE | NP, BC | B · Falta aceptación de usuario/entorno; sin defecto dirigido identificado en esta función base |
| medicamento | Medicamentos (alta y edición)<br>Catálogos → Medicamentos | Lee: S,A,M,E; alta/edición: A | NP, BO | B · Falta aceptación de usuario/entorno; sin defecto dirigido identificado en esta función base |
| detalle_receta | Medicamentos recetados (alta clínica y consulta)<br>Atención y seguimiento → Medicamentos recetados; Pacientes y expedientes | Lee: A,M,E; escribe: API clínica con permisos CORE | NP, BC | B · Falta aceptación de usuario/entorno; sin defecto dirigido identificado en esta función base |
| tipo_examen | Tipos de examen (alta y edición)<br>Catálogos → Tipos de examen | Lee: S,A,M,E; alta/edición: A | NP, API08, UI08 | B · Función base verificada en AUC-08; aceptación/entorno pendientes |
| examen | Solicitudes de examen (alta y edición)<br>Atención y seguimiento → Solicitudes de examen | Lee: A,M,E; alta/edición: A,M | NP, T07, API08, UI08 | B · Función base verificada en AUC-08; aceptación/entorno pendientes |
| resultado_examen | Resultados de examen (alta y seguimiento de estado)<br>Atención y seguimiento → Resultados de examen | Lee: A,M,E; alta: A,M | NP, T07, API08, UI08 | B · Función base verificada en AUC-08; aceptación/entorno pendientes |
| control_de_crecimiento | Controles de crecimiento (alta clínica y consulta)<br>Atención y seguimiento → Controles de crecimiento; Pacientes y expedientes | Lee: A,M,E; escribe: API clínica con permisos CORE | NP, BC | B · Falta aceptación de usuario/entorno; sin defecto dirigido identificado en esta función base |
| antecedente_medico | Antecedentes médicos (alta)<br>Atención y seguimiento → Antecedentes médicos | Lee: A,M,E; alta: A,M | NP | B · Falta aceptación de usuario/entorno; sin defecto dirigido identificado en esta función base |
| signos_vitales | Signos vitales (alta)<br>Atención y seguimiento → Signos vitales | Lee: A,M,E; alta: A,M,E | NP | B · Falta aceptación de usuario/entorno; sin defecto dirigido identificado en esta función base |
| servicio_medico | Servicios médicos (alta y edición)<br>Catálogos → Servicios médicos | Lee: S,A,M,E; alta/edición: A | NP, API08, UI08 | B · Función base verificada en AUC-08; aceptación/entorno pendientes |
| aseguradora | Aseguradoras (alta y edición)<br>Catálogos → Aseguradoras | Lee: S,A,M,E; alta/edición: A | NP, API08, UI08 | B · Función base verificada en AUC-08; aceptación/entorno pendientes |
| plan_seguro | Planes de seguro (alta y edición)<br>Catálogos → Planes de seguro | Lee: S,A,M,E; alta/edición: A | NP, T07, API08, UI08 | B · Función base verificada en AUC-08; aceptación/entorno pendientes |
| poliza_paciente | Pólizas de pacientes (alta y edición)<br>Caja y seguros → Pólizas de pacientes | Lee: A,M,S; alta/edición: A,S | NP, API08, UI08 | B · Función base verificada en AUC-08; aceptación/entorno pendientes |
| cobertura_servicio | Coberturas de servicios (alta y edición)<br>Catálogos → Coberturas de servicios | Lee: S,A,M,E; alta/edición: A | NP, T07, API08, UI08 | B · Función base verificada en AUC-08; aceptación/entorno pendientes |
| autorizacion_seguro | Autorizaciones de seguro (alta y edición)<br>Caja y seguros → Autorizaciones de seguro | Lee: A,M,S; alta/edición: A,S | NP, NAUC, T07, API08, UI08 | B · Función base verificada en AUC-08; aceptación/entorno pendientes |
| factura | Facturas (alta)<br>Caja y seguros → Facturas | Lee: A,M,S; alta: A,S | NP, F06, API08, UI08 | B · Función base verificada en AUC-08; aceptación/entorno pendientes |
| reclamacion_seguro | Reclamaciones de seguro (alta y edición)<br>Caja y seguros → Reclamaciones de seguro | Lee: A,M,S; alta/edición: A,S | NP, NAUC, T07, API08, UI08 | B · Función base verificada en AUC-08; aceptación/entorno pendientes |
| detalle_factura | Conceptos de factura (alta)<br>Caja y seguros → Conceptos de factura | Lee: A,M,S; alta: A,S | NP, F06, API08, UI08 | B · Función base verificada en AUC-08; aceptación/entorno pendientes |
| metodo_pago | Métodos de pago (alta y edición)<br>Catálogos → Métodos de pago | Lee: S,A,M,E; alta/edición: A | NP, API08, UI08 | B · Función base verificada en AUC-08; aceptación/entorno pendientes |
| pago | Pagos (alta)<br>Caja y seguros → Pagos | Lee: A,M,S; alta: A,S | NP, F06, API08, UI08 | B · Función base verificada en AUC-08; aceptación/entorno pendientes |
| rol | Legado de identidad preservado; acceso vigente sustituido por B2<br>Usuarios y permisos (B2), sin editar tablas heredadas | Sin acceso de contraseña heredada desde API; mantenimiento con responsable | B2/definiciones y fuentes de mantenimiento; no nueva certificación de migración | T · Preservar; no crear autenticación paralela |
| institucion | Legado de identidad preservado; acceso vigente sustituido por B2<br>Usuarios y permisos (B2), sin editar tablas heredadas | Sin acceso de contraseña heredada desde API; mantenimiento con responsable | B2/definiciones y fuentes de mantenimiento; no nueva certificación de migración | T · Preservar; no crear autenticación paralela |
| usuario | Legado de identidad preservado; acceso vigente sustituido por B2<br>Usuarios y permisos (B2), sin editar tablas heredadas | Sin acceso de contraseña heredada desde API; mantenimiento con responsable | B2/definiciones y fuentes de mantenimiento; no nueva certificación de migración | T · Preservar; no crear autenticación paralela |
| pediatria_conciliacion | Reserva de unicidad o control de mantenimiento<br>Sin formulario clínico; mantenimiento/alta transaccional | Sin acceso de contraseña heredada desde API; mantenimiento con responsable | B2/definiciones y fuentes de mantenimiento; no nueva certificación de migración | T · Verificar en habilitación; AUC-12 |
| pediatria_schema_version | Reserva de unicidad o control de mantenimiento<br>Sin formulario clínico; mantenimiento/alta transaccional | Sin acceso de contraseña heredada desde API; mantenimiento con responsable | B2/definiciones y fuentes de mantenimiento; no nueva certificación de migración | T · Verificar en habilitación; AUC-12 |

## laboratorio

| Tabla/colección | Función / pantalla | Permiso | Evidencia | Estado y pendiente |
|---|---|---|---|---|
| clinico_pacientes | Pacientes (alta clínica y consulta)<br>Atención y seguimiento → Pacientes; Pacientes y expedientes | Lee: A,M,S,L,E; escribe: API clínica con permisos CORE | ND, BC, CN | B · Falta aceptación de usuario/entorno; sin defecto dirigido identificado en esta función base |
| clinico_consultas | Consultas (alta clínica y consulta)<br>Atención y seguimiento → Consultas; Pacientes y expedientes | Lee: A,M,L,E; escribe: API clínica con permisos CORE | ND, BC | B · Falta aceptación de usuario/entorno; sin defecto dirigido identificado en esta función base |
| clinico_tratamientos | Tratamientos (alta clínica y consulta)<br>Atención y seguimiento → Tratamientos; Pacientes y expedientes | Lee: A,M,L,E; escribe: API clínica con permisos CORE | ND, BC | B · Falta aceptación de usuario/entorno; sin defecto dirigido identificado en esta función base |
| clinico_medicamentos | Medicamentos (alta y edición)<br>Catálogos → Medicamentos | Lee: A,L,M,E; alta/edición: A | ND, BO | B · Falta aceptación de usuario/entorno; sin defecto dirigido identificado en esta función base |
| clinico_profesionales_operativos | Profesionales (alta y edición)<br>Catálogos → Profesionales | Lee: S,A,L,M,E; alta/edición: A | ND, API08, UI08, REV10 | B · coherencia profesional verificada |
| clinico_citas | Agenda de citas (alta y edición)<br>Agenda → Agenda de citas | Lee: A,M,S,L,E; alta/edición: S,A,L,M | ND (BO solo abre/cancela formulario; no guarda ni atiende), API08, UI08 | B · Función base verificada en AUC-08; aceptación/entorno pendientes |
| clinico_tipos_examen | Tipos de examen (alta y edición)<br>Catálogos → Tipos de examen | Lee: A,L,M,E; alta/edición: A | ND, API08, UI08 | B · Función base verificada en AUC-08; aceptación/entorno pendientes |
| clinico_resultados | Resultados de exámenes (alta clínica y seguimiento de estado)<br>Atención y seguimiento → Resultados de exámenes; Pacientes y expedientes | Lee: A,M,L,E; escribe: API clínica con permisos CORE | ND, BC, T07, API08, UI08 | B · Función base verificada en AUC-08; aceptación/entorno pendientes |
| clinico_pagos | Pagos (alta)<br>Caja y seguros → Pagos | Lee: A,S; alta: A,S | ND | B · Falta aceptación de usuario/entorno; sin defecto dirigido identificado en esta función base |
| clinico_diagnosticos | Diagnóstico de una consulta<br>Pacientes y expedientes → Consultas y tratamientos | Lee: A,M,E,L; escribe: A,M + profesional | BC, CN | B · No requiere pantalla CRUD separada; falta aceptación en entorno compartido |
| clinico_recetas | Receta de tratamiento<br>Pacientes y expedientes → Consultas y tratamientos | Lee: A,M,E,L; escribe: A,M + profesional | BC, CN | B · No requiere pantalla CRUD separada; falta aceptación en entorno compartido |
| clinico_identificaciones | Reserva de unicidad o control de mantenimiento<br>Sin formulario clínico; mantenimiento/alta transaccional | Sin acceso de contraseña heredada desde API; mantenimiento con responsable | B2/definiciones y fuentes de mantenimiento; no nueva certificación de migración | T · Verificar en habilitación; AUC-12 |
| clinico_operaciones_unicidad | Reserva de unicidad o control de mantenimiento<br>Sin formulario clínico; mantenimiento/alta transaccional | Sin acceso de contraseña heredada desde API; mantenimiento con responsable | B2/definiciones y fuentes de mantenimiento; no nueva certificación de migración | T · Verificar en habilitación; AUC-12 |
| pacientes (sin prefijo, legado A2) | Datos A2 preservados; no son el flujo clínico v2<br>No se editan con OPERACIONES-01 | Mantenimiento según A2/B5; sin login alternativo | CN preserva legado; fixtures A2 en db/mongo | T · Conciliación explícita si se necesitan datos reales heredados; no migración por inferencia |
| consultas (sin prefijo, legado A2) | Datos A2 preservados; no son el flujo clínico v2<br>No se editan con OPERACIONES-01 | Mantenimiento según A2/B5; sin login alternativo | CN preserva legado; fixtures A2 en db/mongo | T · Conciliación explícita si se necesitan datos reales heredados; no migración por inferencia |
| resultados_examen (sin prefijo, legado A2) | Datos A2 preservados; no son el flujo clínico v2<br>No se editan con OPERACIONES-01 | Mantenimiento según A2/B5; sin login alternativo | CN preserva legado; fixtures A2 en db/mongo | T · Conciliación explícita si se necesitan datos reales heredados; no migración por inferencia |
| tipos_examen (sin prefijo, legado A2) | Datos A2 preservados; no son el flujo clínico v2<br>No se editan con OPERACIONES-01 | Mantenimiento según A2/B5; sin login alternativo | CN preserva legado; fixtures A2 en db/mongo | T · Conciliación explícita si se necesitan datos reales heredados; no migración por inferencia |
| medicamentos (sin prefijo, legado A2) | Datos A2 preservados; no son el flujo clínico v2<br>No se editan con OPERACIONES-01 | Mantenimiento según A2/B5; sin login alternativo | CN preserva legado; fixtures A2 en db/mongo | T · Conciliación explícita si se necesitan datos reales heredados; no migración por inferencia |
| usuarios (sin prefijo, legado A2) | Datos A2 preservados; no son el flujo clínico v2<br>No se editan con OPERACIONES-01 | Mantenimiento según A2/B5; sin login alternativo | CN preserva legado; fixtures A2 en db/mongo | T · Conciliación explícita si se necesitan datos reales heredados; no migración por inferencia |

## odontologica

| Tabla/colección | Función / pantalla | Permiso | Evidencia | Estado y pendiente |
|---|---|---|---|---|
| pacientes | Pacientes (alta clínica y consulta)<br>Atención y seguimiento → Pacientes; Pacientes y expedientes | Lee: A,M,S,L,E; escribe: API clínica con permisos CORE | ND, BC, CN | B · Falta aceptación de usuario/entorno; sin defecto dirigido identificado en esta función base |
| consultas | Consultas (alta clínica y consulta)<br>Atención y seguimiento → Consultas; Pacientes y expedientes | Lee: A,M,L,E; escribe: API clínica con permisos CORE | ND, BC | B · Falta aceptación de usuario/entorno; sin defecto dirigido identificado en esta función base |
| tratamientos | Tratamientos (alta clínica y consulta)<br>Atención y seguimiento → Tratamientos; Pacientes y expedientes | Lee: A,M,L,E; escribe: API clínica con permisos CORE | ND, BC | B · Falta aceptación de usuario/entorno; sin defecto dirigido identificado en esta función base |
| medicamentos | Medicamentos (alta y edición)<br>Catálogos → Medicamentos | Lee: A,L,M,E; alta/edición: A | ND, BO | B · Falta aceptación de usuario/entorno; sin defecto dirigido identificado en esta función base |
| profesionales_operativos | Profesionales (alta y edición)<br>Catálogos → Profesionales | Lee: S,A,L,M,E; alta/edición: A | ND, API08, UI08, REV10 | B · coherencia profesional verificada |
| citas | Agenda de citas (alta y edición)<br>Agenda → Agenda de citas | Lee: A,M,S,L,E; alta/edición: S,A,L,M | ND (BO solo abre/cancela formulario; no guarda ni atiende), API08, UI08 | B · Función base verificada en AUC-08; aceptación/entorno pendientes |
| procedimientos | Procedimientos odontológicos (alta clínica y seguimiento de estado)<br>Atención y seguimiento → Procedimientos odontológicos; Pacientes y expedientes | Lee: A,M,E; escribe: API clínica con permisos CORE | ND, BC, T07, API08, UI08 | B · Función base verificada en AUC-08; aceptación/entorno pendientes |
| pagos | Pagos (alta)<br>Caja y seguros → Pagos | Lee: A,S; alta: A,S | ND | B · Falta aceptación de usuario/entorno; sin defecto dirigido identificado en esta función base |
| diagnosticos | Diagnóstico de una consulta<br>Pacientes y expedientes → Consultas y tratamientos | Lee: A,M,E; escribe: A,M + profesional | BC, CN | B · No requiere pantalla CRUD separada; falta aceptación en entorno compartido |
| recetas | Receta de tratamiento<br>Pacientes y expedientes → Consultas y tratamientos | Lee: A,M,E; escribe: A,M + profesional | BC, CN | B · No requiere pantalla CRUD separada; falta aceptación en entorno compartido |
| identificaciones | Reserva de unicidad o control de mantenimiento<br>Sin formulario clínico; mantenimiento/alta transaccional | Sin acceso de contraseña heredada desde API; mantenimiento con responsable | B2/definiciones y fuentes de mantenimiento; no nueva certificación de migración | T · Verificar en habilitación; AUC-12 |
| operaciones_unicidad | Reserva de unicidad o control de mantenimiento<br>Sin formulario clínico; mantenimiento/alta transaccional | Sin acceso de contraseña heredada desde API; mantenimiento con responsable | B2/definiciones y fuentes de mantenimiento; no nueva certificación de migración | T · Verificar en habilitación; AUC-12 |

## Identidad central Django

| Modelo/tabla funcional | Función y pantalla | Permiso | Evidencia | Estado |
|---|---|---|---|---|
| User / auth_user | Alta, activación, búsqueda y paginación institucional; Usuarios y permisos | A, institución propia, sin staff/superuser | PermissionTests, BO, API08/UI08, API09/UI09; identidad SQLite de prueba | B · navegación y editor único verificados; aceptación/entorno pendientes |
| PerfilInstitucional | Asignación de rol inicial, activo y vínculo profesional | A, institución propia | PermissionTests, BO, API08, UI08, API09/UI09 | B · roles, activación y vínculo verificados; coherencia profesional verificada en REV10 |
| Profesional | Vínculo de perfil a referencia externa | A, institución propia | BO, REV10 cuatro instituciones | B · B2 y elegibilidad nativa verificados |
| Django sessions, permisos, grupos, admin_log y migraciones | Sesiones/autorización y mantenimiento del framework | B2 / administrador técnico autorizado | Suite B2 anterior y pruebas de sesión | T · sin formularios clínicos, no sustituir por tablas usuario heredadas |

Flujo guiado verificado en AUC-09. Medición controlada documentada en [AUC-11](CIERRE_AUC_11.md).
Habilitación compartida pendiente: AUC-12; respaldo/restauración y upgrade ensayados localmente. Hallazgos y orden de cierre en
[AUDITORIA_COBERTURA.md](AUDITORIA_COBERTURA.md). Datos editables en
[MATRIZ_COBERTURA.csv](MATRIZ_COBERTURA.csv).
