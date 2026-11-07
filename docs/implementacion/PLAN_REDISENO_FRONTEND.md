# Plan maestro de rediseño del frontend

Red de Instituciones Médicas · 6 de noviembre de 2026

Base revisada `implementacion` en `a445d79`. Plan de trabajo para Jennifer y Pablo.

## 1. Objetivo y punto de partida

Mejorar la jerarquía del expediente, la navegación de tareas, la legibilidad de las tablas y los formularios clínicos. El rediseño conserva React 19, Vite, JSX, la API Django y el flujo real con los cuatro motores. La sesión sigue determinando la institución, el rol y el alcance de cada persona.

| Área | Estado en el código | Trabajo de diseño |
| --- | --- | --- |
| Shell | `App.jsx` selecciona el servicio. `ClinicalPage.jsx` controla sesión, institución, paciente y espacio activo. El encabezado ya muestra institución y rol. | Dar ubicación y jerarquía al usuario. Mantener institución y rol a la vista como datos de la sesión. |
| Expediente | `History.jsx` ya muestra nombre, identificación, nacimiento, edad y estado, con pestañas clínica y especializada. Los registros se presentan como un árbol clínico. | Dar prioridad al resumen del paciente y ordenar la atención por consulta. Mantener los padres de diagnóstico, tratamiento y receta. |
| Operaciones | `OperationsWorkspace.jsx` obtiene recursos, campos, acciones y permisos del manifiesto. Mantiene borradores durante la sesión y enlaza tareas con el expediente. | Mejorar navegación, densidad de tabla y detalle. Conservar la composición por manifiesto y el contexto del paciente. |
| Diálogos | `TaskDialog.jsx` y los diálogos de operaciones ya usan `<dialog>`. El cierre se restringe mientras se guarda. | Unificar estilo, foco inicial y de retorno, descripción de errores y comportamiento de teclado. |
| Estilos | `styles.css` ya incluye foco visible y reglas responsive. Falta una escala compartida y un sistema de primitivos. | Introducir tokens y comprobar contraste, teclado y anchos en recorridos reales. |
| Especialidades | `SpecialtyDemoPanel.jsx` se usa con la API real y con el doble de desarrollo. | Aclarar el nombre y extraer puntos de extensión institucionales según el uso real, con el mismo contrato. |

## 2. Decisiones de diseño

- **Paciente e institución a la vista.** Mostrar identificación, edad y estado en el expediente, e institución y rol en el shell. El encabezado identifica la institución de la sesión.
- **Densidad y jerarquía.** Dar prioridad a las tareas frecuentes. En el expediente, usar una línea de tiempo por consulta con diagnósticos, tratamientos y recetas asociados al padre correcto.
- **Estados reutilizables.** Unificar carga, vacío, error, guardado y confirmación. Mostrar texto junto a color o icono. Preservar los datos ingresados ante errores de validación y conflicto dentro de la sesión activa.
- **Confirmaciones.** Archivo requiere motivo y confirmación. Las acciones financieras requieren una confirmación que explique el efecto. El cuerpo de la acción financiera conserva exactamente `{accion,version}`.
- **Permisos y catálogos.** Mostrar las acciones autorizadas por el manifiesto y las reglas clínicas. Usar el catálogo real de medicamentos para el selector con búsqueda. CIE-10 sigue como campo de texto validado hasta que exista un catálogo aprobado.
- **Sesión vencida.** En este rediseño se mantiene el retorno a login y la limpieza del contexto clínico en un 401. Si el equipo incorpora recuperación de borradores después de reautenticar, tratarla como un cambio separado. Requiere validar la misma cuenta, institución y acceso vigente antes de restaurar contenido, limitarlo a memoria y descartarlo en logout o cambio de cuenta.
- **Conflicto 409.** Conservar lo escrito, permitir consultar la versión actual y pedir una acción explícita antes de guardar de nuevo. La edición y las acciones financieras siguen usando la versión del servidor.

### Sistema visual

CSS plano con `frontend/src/styles/tokens.css` y `frontend/src/styles/ui.css`, introducido gradualmente junto con `styles.css`. Usar tipografía del sistema y SVG locales como punto de partida. Cualquier dependencia nueva se evalúa en un PR de la base.

| Área | Propuesta |
| --- | --- |
| Color | Neutros fríos, acento azul y colores semánticos. Matiz institucional en un detalle del encabezado junto al nombre. |
| Tipografía | Escala 12, 13, 14, 16, 20 y 24 px. Cuerpo de 14 px y números tabulares donde ayuden a comparar. |
| Espaciado | Escala de 4, 8, 12, 16, 24, 32 y 48 px. |
| Superficies | Radios de 4 px para controles y 8 px para paneles. Bordes de 1 px y sombra discreta para menús y diálogos. |
| Movimiento | Transiciones breves de 120–180 ms para opacidad y transformación. Respetar `prefers-reduced-motion`. |
| Distribución | Rejilla de hasta 12 columnas, ancho útil máximo de 1280 px y puntos de corte de 640, 1024 y 1280 px como base. |
| Densidad | Tabla compacta por defecto. Ofrecer densidad cómoda si el recorrido lo necesita. |

Usar una estética sobria con superficies sólidas, bordes ligeros y agrupaciones simples. Las referencias del plan original orientan decisiones puntuales: densidad de Linear, estados de tabla de Stripe Dashboard, formularios de Geist, comportamiento de primitivas de shadcn/ui y Radix, y mensajes de Atlassian.

### Primitivos y patrones

Los componentes nuevos compartidos viven en `frontend/src/components/ui/`. La base publica solo los primitivos que consume cada fase y sus ejemplos de uso. La paleta de comandos es opcional y queda al final.

| Archivo propuesto | Uso y estados |
| --- | --- |
| `Button.jsx` | Primario, secundario, discreto y peligro. Foco, deshabilitado y guardado. |
| `Input.jsx`, `Select.jsx`, `FormField.jsx` | Controles con etiqueta, ayuda, obligatorio u opcional, error asociado y foco. |
| `Combobox.jsx` | Búsqueda sobre referencias existentes. Abierto, cargando, vacío, error y selección por teclado. |
| `Dialog.jsx` | Composición alrededor de `<dialog>`. Formulario, detalle y confirmación con foco y Escape. |
| `DataTable.jsx` | Tabla compacta o cómoda con carga, vacío, error, selección y paginación del contrato. |
| `Tabs.jsx` | Secciones del expediente con navegación y foco por teclado. |
| `Toast.jsx`, `ErrorBanner.jsx` | Confirmación breve y errores recuperables con mensajes específicos y acción apropiada. |
| `Badge.jsx`, `Card.jsx` | Estado legible y agrupación de contenido. |
| `EmptyState.jsx`, `Skeleton.jsx` | Alternativas para vacío y carga, con movimiento reducible. |
| `Breadcrumb.jsx`, `Sidebar.jsx`, `PageHeader.jsx` | Ubicación, navegación y acciones contextualizadas. |
| `CommandPalette.jsx` | Acceso rápido opcional a tareas y búsqueda. |

- **Shell.** Barra lateral y encabezado de página. En pantallas pequeñas, navegación accesible que conserva el estado del paciente y la tarea.
- **Pacientes.** Búsqueda por prefijo, paginación real y alta visible para los roles que la permiten.
- **Expediente.** Resumen persistente del paciente, pestañas de atención y seguimiento, y consultas plegables. Conservar los flujos de cita, lectura y archivo.
- **Formularios.** Un editor por vez. Usar un panel o diálogo amplio según la tarea. Conservar el contexto del paciente, los errores por campo y la protección contra doble envío.
- **Operaciones y cuentas.** Listado, detalle y acciones que corresponden al manifiesto o al rol. Dar visibilidad a las confirmaciones y al resultado de cada acción.
- **Muestra de UI.** Si se añade una página de componentes, exponerla solo en desarrollo y mantener la navegación actual por estado. El plan no requiere introducir un router.

## 3. Propiedad de archivos

| Capa | Responsable | Alcance |
| --- | --- | --- |
| Base y contenedores compartidos | Pablo / A | `styles.css`, `styles/*`, `components/ui/*`, `App.jsx`, `clinical/ClinicalPage.jsx`, `History.jsx`, `TaskDialog.jsx`, `SpecialtyDemoPanel.jsx` y `operations/OperationsWorkspace.jsx`. También coordina cambios a formularios y cuentas compartidos. |
| Transporte y reglas | Pablo / A para coordinar | `api/*`, `operations/helpers.js` y `workflow.js`. Los cambios de contrato o autorización se discuten y revisan por separado. |
| Laboratorio y Pediatría | Pablo / A | `frontend/src/features/laboratorio/` y `frontend/src/features/pediatrico/` para composición o comportamiento de presentación específico. |
| Hospital y Odontología | Jennifer / B | `frontend/src/features/hospital/` y `frontend/src/features/odontologica/` para composición o comportamiento de presentación específico. |

Conservar una sola implementación para listado, expediente, formularios y operaciones compartidos. Extraer únicamente extensiones institucionales que tengan un límite claro. Los contenedores compartidos pasan el contexto de sesión, paciente, permisos y funciones existentes. Si una rama necesita ajustar una pieza compartida, coordinar un PR pequeño de la base y consumirlo desde `implementacion` después de integrarlo. Revisar juntos los cambios de shell y de los puntos de extensión.

## 4. Ramas y orden de integración

`implementacion` es la rama de destino. Cada PR tiene una pantalla, un recurso o una extracción revisable como unidad de trabajo.

| Orden | Rama | Trabajo y criterio |
| --- | --- | --- |
| 1 | `feat/ui-base` desde `origin/implementacion` | Pablo publica tokens, primitivos iniciales y puntos de extensión. La extracción mecánica se revisa por separado del cambio visual del shell. Antes de integrar, pasan la suite, la compilación y el recorrido de referencia. |
| 2 | `feat/ui-laboratorio`, `feat/ui-pediatrico` | Pablo inicia ambas desde `origin/implementacion` actualizado después de integrar la base. |
| 2 | `feat/ui-hospital`, `feat/ui-odontologica` | Jennifer inicia ambas desde el mismo `origin/implementacion` actualizado. En paralelo a la base puede preparar recorridos, criterios visuales y casos de prueba. |
| 3 | PRs acotados de pulido | Cada dueño corrige su capa. Los PRs apuntan a `implementacion` y se integran tras revisión y validación. |

Para comenzar la base desde un checkout limpio, usa la rama publicada.

```powershell
git fetch origin
git switch --track origin/feat/ui-base
```

Si ya tienes la rama local, usa `git switch feat/ui-base`. Para las ramas institucionales, actualiza `origin/implementacion` después del merge de la base y usa el nombre de cada rama. Si el checkout tiene cambios locales, guárdalos en su rama o usa un worktree separado. El equipo decide el merge tras revisar el PR.

## 5. Fases y aceptación

| Fase | Entregables | Aceptación |
| --- | --- | --- |
| 0. Fundación | Tokens y primitivos necesarios, puntos de extensión y shell. Separar la extracción y el cambio visual en commits o PRs revisables. | La extracción conserva comportamiento y presentación. El shell conserva los recorridos, estados y permisos de las cuatro instituciones. Pasan pruebas y build. |
| 1. Pantallas | Laboratorio y Pediatría por Pablo. Hospital y Odontología por Jennifer. Incorporar cambios comunes por su PR de base. | Por institución, verificar la cadena clínica real, archivo y una operación especializada. Revisar el comportamiento con un rol restringido. |
| 2. Integración y pulido | Estados de interfaz, responsive, foco, teclado, contraste, errores y revisión cruzada. | Pasan los recorridos con datos ficticios y API real, las pruebas del cliente y la compilación. |

### Revisión visual antes de integrar

El objetivo es un frontend pulido y reconocible como un solo producto. El shell, el expediente y los formularios deben compartir la misma jerarquía de texto, alineación, espaciado y tratamiento de estados. El expediente debe permitir ubicar al paciente, su estado y la acción principal de un vistazo. Cada institución mantiene su identidad en el encabezado y sus tareas especializadas dentro del mismo sistema visual.

En cada PR visual, adjunta capturas con datos ficticios de escritorio y móvil, junto con un caso de carga, vacío o error que corresponda a la pantalla. Revisa las capturas en pareja para detectar cortes de texto, acciones que desaparecen, elementos desalineados y cambios de densidad entre pantallas. Incluye el recorrido con teclado y la prueba con la API real.

### Checklist por PR

- [ ] `npm.cmd --prefix frontend test` y `npm.cmd --prefix frontend run build` desde la raíz. La línea base revisada tiene 65 pruebas del cliente.
- [ ] `GET /api/health/databases/` con `connected` verdadero en las cuatro instituciones. Repetir las pruebas de interfaz con el backend real.
- [ ] Recorrido con un paciente ficticio. Login, búsqueda, alta, consulta, diagnóstico, tratamiento, receta y archivo. Repetir lectura después de recargar y comprobar el rechazo de una nueva consulta después del archivo.
- [ ] Especialización. Hospital con cama, traslado y alta. Pediatría con tutor, vacuna y crecimiento. Laboratorio con resultados de campos variables. Odontología con procedimiento por pieza.
- [ ] Institución y rol. Verificar controles restringidos y rechazo de un expediente ajeno.
- [ ] Teclado. Foco visible, orden de Tab, Escape y retorno de foco en diálogos. Etiquetas y mensajes asociados a cada campo.
- [ ] Objetivo WCAG 2.2 AA. Comprobar contraste de texto y controles, avisos con texto, y movimiento reducido. Revisar a 360, 768 y 1280 px.
- [ ] Error y guardado. Verificar carga, vacío, validación, 401, 403, 409 y 503. Comprobar el estado después de volver a iniciar sesión, y la conservación de lo escrito ante validación o conflicto durante la sesión activa.
- [ ] Pruebas Chromium reales mediante el runner dedicado de la guía. Si cambia una etiqueta o estructura, actualizar las pruebas para que sigan comprobando el mismo comportamiento. [Guía de Docker][docker] · [Runner y evidencia][validacion]

## 6. Mensajes para cada agente

**Pablo / A**

> Parte de `origin/implementacion` en `feat/ui-base`. Separa la extracción sin cambio de comportamiento del shell visual. Publica los puntos de extensión y los primitivos necesarios, con pruebas. Tras integrar la base, trabaja Laboratorio y Pediatría en sus ramas de institución. Coordina los cambios a componentes compartidos mediante PRs revisables. Conserva contratos, permisos y rutas.

**Jennifer / B**

> Prepara en paralelo los recorridos y el QA de Hospital y Odontología. Tras integrar `feat/ui-base`, crea las dos ramas desde `origin/implementacion`. Usa las extensiones institucionales y los primitivos compartidos. Si una mejora requiere cambiar un componente común, coordina ese PR con Pablo. Verifica cada recorrido con la API real y adjunta el resultado a la revisión.

[docker]: https://github.com/PabloZ7-425/Red_Instituciones_Medicas/blob/implementacion/docs/implementacion/PRUEBA_DOCKER.md
[validacion]: https://github.com/PabloZ7-425/Red_Instituciones_Medicas/blob/implementacion/docs/implementacion/VALIDACION.md
