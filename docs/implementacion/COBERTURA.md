# Cobertura de tablas y colecciones

> **Actualización:** AUC-01 a AUC-04 corregidos; ver [cierre y pruebas](CIERRE_AUC_01_04.md). El alcance completo sigue pendiente: AUC-05 a AUC-12. Consultar [auditoría](AUDITORIA_COBERTURA.md) y [matriz actualizada](MATRIZ_COBERTURA.md).

La interfaz se organiza por tareas. Usar una tabla no significa dar acceso directo
al usuario a cada columna, contraseña, reserva técnica o tabla heredada.

## hospital

| Tabla/colección | Función | Escritura |
|---|---|---|
| especialidad | Especialidades · Catálogos | Alta / edición |
| medico | Profesionales médicos · Catálogos | Alta / edición |
| enfermero | Personal de enfermería · Catálogos | Alta / edición |
| pabellon_edificio | Pabellones · Catálogos | Alta / edición |
| habitacion | Habitaciones · Catálogos | Alta / edición |
| cama | Camas · Catálogos | Alta / edición |
| quirofano | Quirófanos · Catálogos | Alta / edición |
| paciente | Pacientes · Atención y seguimiento | API clínica y expediente existentes |
| ingreso_hospitalario | Ingresos hospitalarios · Hospitalización | API clínica y expediente existentes |
| movimiento_cama | Traslados de cama · Hospitalización | Alta |
| emergencia | Emergencias y triaje · Hospitalización | Alta |
| cita | Agenda de citas · Agenda | Alta / edición |
| consulta | Consultas · Atención y seguimiento | API clínica y expediente existentes |
| signos_vitales | Signos vitales · Hospitalización | Alta |
| diagnostico | Diagnósticos · Atención y seguimiento | API clínica y expediente existentes |
| cirugia | Cirugías · Hospitalización | Alta / edición |
| equipo_quirurgico | Equipo quirúrgico · Hospitalización | Alta |
| tratamiento | Tratamientos · Atención y seguimiento | Alta |
| medicamento | Medicamentos · Catálogos | Alta / edición |
| receta_prescripcion | Prescripciones · Atención y seguimiento | Alta operativa y API clínica; consulta e ingreso |
| despacho_farmacia | Despachos de farmacia · Farmacia | Alta |
| aplicacion_enfermeria | Administración de medicamentos · Farmacia | Alta |
| factura | Facturas · Caja y seguros | Alta |
| detalle_factura | Conceptos de factura · Caja y seguros | Alta |
| pago | Pagos · Caja y seguros | Alta |

Diagnóstico de ingreso tiene tarea propia y conserva el origen hospitalario. Los
tratamientos usan el diagnóstico de consulta o de ingreso, sin inventar consultas.

## pediatrico

| Tabla/colección | Función | Escritura |
|---|---|---|
| especialidad | Especialidades · Catálogos | Alta / edición |
| medico | Profesionales médicos · Catálogos | Alta / edición |
| paciente | Pacientes · Atención y seguimiento | API clínica y expediente existentes |
| tutor | Tutores · Catálogos | Alta / edición |
| paciente_tutor | Vincular tutor existente · Atención y seguimiento | Alta |
| cita | Agenda de citas · Agenda | Alta / edición |
| consulta | Consultas · Atención y seguimiento | API clínica y expediente existentes |
| diagnostico | Diagnósticos · Atención y seguimiento | API clínica y expediente existentes |
| consulta_diagnostico | Diagnósticos de consulta · Atención y seguimiento | API clínica y expediente existentes |
| tratamiento | Tratamientos · Atención y seguimiento | API clínica y expediente existentes |
| vacuna | Vacunas · Catálogos | Alta / edición |
| aplicacion_vacuna | Aplicaciones de vacunas · Atención y seguimiento | API clínica y expediente existentes |
| receta | Recetas · Atención y seguimiento | API clínica y expediente existentes |
| medicamento | Medicamentos · Catálogos | Alta / edición |
| detalle_receta | Medicamentos recetados · Atención y seguimiento | API clínica y expediente existentes |
| tipo_examen | Tipos de examen · Catálogos | Alta / edición |
| examen | Solicitudes de examen · Atención y seguimiento | Alta / edición |
| resultado_examen | Resultados de examen · Atención y seguimiento | Alta |
| control_de_crecimiento | Controles de crecimiento · Atención y seguimiento | API clínica y expediente existentes |
| antecedente_medico | Antecedentes médicos · Atención y seguimiento | Alta |
| signos_vitales | Signos vitales · Atención y seguimiento | Alta |
| servicio_medico | Servicios médicos · Catálogos | Alta / edición |
| aseguradora | Aseguradoras · Catálogos | Alta / edición |
| plan_seguro | Planes de seguro · Catálogos | Alta / edición |
| poliza_paciente | Pólizas de pacientes · Caja y seguros | Alta / edición |
| cobertura_servicio | Coberturas de servicios · Catálogos | Alta / edición |
| autorizacion_seguro | Autorizaciones de seguro · Caja y seguros | Alta / edición |
| factura | Facturas · Caja y seguros | Alta |
| reclamacion_seguro | Reclamaciones de seguro · Caja y seguros | Alta / edición |
| detalle_factura | Conceptos de factura · Caja y seguros | Alta |
| metodo_pago | Métodos de pago · Catálogos | Alta / edición |
| pago | Pagos · Caja y seguros | Alta |

## laboratorio

| Tabla/colección | Función | Escritura |
|---|---|---|
| pacientes | Pacientes · Atención y seguimiento | API clínica y expediente existentes |
| consultas | Consultas · Atención y seguimiento | API clínica y expediente existentes |
| tratamientos | Tratamientos · Atención y seguimiento | API clínica y expediente existentes |
| medicamentos | Medicamentos · Catálogos | Alta / edición |
| profesionales_operativos | Profesionales · Catálogos | Alta / edición |
| citas | Agenda de citas · Agenda | Alta / edición |
| tipos_examen | Tipos de examen · Catálogos | Alta / edición |
| resultados | Resultados de exámenes · Atención y seguimiento | API clínica y expediente existentes |
| pagos | Pagos · Caja y seguros | Alta |

Diagnósticos, recetas y sus relaciones se gestionan desde la API/expediente clínico
existente, aunque no tengan una pantalla administrativa separada.

## odontologica

| Tabla/colección | Función | Escritura |
|---|---|---|
| pacientes | Pacientes · Atención y seguimiento | API clínica y expediente existentes |
| consultas | Consultas · Atención y seguimiento | API clínica y expediente existentes |
| tratamientos | Tratamientos · Atención y seguimiento | API clínica y expediente existentes |
| medicamentos | Medicamentos · Catálogos | Alta / edición |
| profesionales_operativos | Profesionales · Catálogos | Alta / edición |
| citas | Agenda de citas · Agenda | Alta / edición |
| procedimientos | Procedimientos odontológicos · Atención y seguimiento | API clínica y expediente existentes |
| pagos | Pagos · Caja y seguros | Alta |

Diagnósticos, recetas y sus relaciones se gestionan desde la API/expediente clínico
existente, aunque no tengan una pantalla administrativa separada.

## Identidad, mantenimiento y legado

- usuario de PostgreSQL; usuario/rol/institucion de MySQL y usuarios históricos
  Mongo: preservados, sin autenticación paralela ni exposición de contraseñas.
  Su función de acceso es sustituida por User/PerfilInstitucional/Profesional de
  B2 y la pantalla Usuarios y permisos. No se inventa una sincronización con
  credenciales heredadas. Las instituciones/roles válidos son los del contrato.
- pediatria_schema_version, hospital_schema_version y pediatria_conciliacion:
  control de esquema/evidencias de mantenimiento. No son formularios clínicos.
  Las migraciones/conciliaciones conservan sus procedimientos B3/B4; no se permite
  editar evidencias desde el navegador para aparentar una migración correcta.
- identificaciones de Firestore y clinico_identificaciones de Mongo: reservas
  internas de unicidad utilizadas por el alta clínica, no datos a llenar a mano.
- operaciones_unicidad: reservas de nombres de catálogo; un nombre reservado no
  se reutiliza silenciosamente al renombrar el registro. Los registros existentes
  permanecen referenciados por ID.
- Los modelos históricos v1 permanecen intactos; no se transforman datos ambiguos
  ni unidades antiguas por inferencia para mostrar una supuesta cobertura total.

## Alcance funcional y límites

Se implementa operación administrativa académica, no una pasarela bancaria,
facturación electrónica SAT ni adjudicación automática de seguros. El usuario
registra la autorización/cobertura efectivamente acordada; el sistema comprueba
relaciones e importes y calcula totales/saldos. Los pagos de caja pediátrica son
del paciente; el importe del seguro se sigue mediante autorización/reclamación.
No se inventa una regla universal de deducibles, percentiles, dosis, triaje o
recomendaciones médicas que no está definida por el esquema/requisitos.

La evidencia distingue cobertura funcional de aprobación de cada regla clínica
posible y de operación productiva. La revisión con usuarios reales y la habilitación
en el entorno de entrega siguen siendo necesarias antes del uso diario allí.
