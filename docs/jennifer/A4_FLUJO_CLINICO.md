# A4 — cadena clínica y archivo desde React

Jennifer, 22 de octubre de 2026, America/Guatemala. Base `8cec548` (A3).
Entrega exclusivamente en feature/jennifer, sin PR ni integración a main.
Contrato API/REPO 1.0.0; no se modifican backend, contratos centrales ni Compose.

## Entregado

La historia permite registrar un diagnóstico por ocurrencia en cada consulta,
un tratamiento en cada diagnóstico y una receta en cada tratamiento. Los IDs
proceden del padre seleccionado; no se piden IDs internos ni profesional en un
campo libre. El profesional se resuelve/autoriza en backend mediante el principal.

Receta busca medicamentos con CAT-01, estados de carga/vacío/error/reintento y
paginación. Selecciona un medicamento retornado por el catálogo; al buscar otra
página se borra la selección previa. Una respuesta inválida del catálogo es error,
no una lista vacía. Dosis/frecuencia obligatorias, vía opcional; las lecturas de
recetas resuelven el nombre consultando catálogo hasta encontrar los IDs necesarios.
Si el rol no tiene permiso CAT-01 o el medicamento no está disponible, se indica
«Nombre de medicamento no disponible» sin inventar un nombre. No se exponen IDs
para que el usuario intente resolverlos manualmente.

Admin puede archivar con motivo y confirmación explícita. Se muestra que la historia
se conserva y que se impiden nuevas escrituras; el paciente archivado y la cadena
clínica permanecen visibles tras actualizar. Se usa PATCH con estado=archivado.
Médico/admin pueden escribir diagnóstico/tratamiento/receta; los otros roles no
ofrecen esos botones. Estas reglas visuales no sustituyen permisos del servidor.

El formulario compartido conserva texto/selección ante un error, enfoca el primer
campo inválido y vincula los errores a sus controles. Tiene IDs de accesibilidad
únicos. Bloquea doble envío mediante ref antes del await; durante el guardado se
bloquean cambios de sección, búsqueda de pacientes, logout y operaciones competidoras.
Los éxitos vuelven a leer historial/listado; un fallo de esa lectura no reenvía la
escritura. Red/JSON de confirmación inválido indica actualizar antes de repetir,
sin reintento automático de POST/PATCH. 401 vuelve a login; 403/404/409/503 conservan
el error y el formulario según corresponda.

El cliente usa las rutas API-07/08/09/10 y CAT-01, cookies y X-CSRFToken existentes.
No se cambia login ni el contrato. El doble DEMO conserva los diez fixtures originales
intactos; agrega operaciones en memoria por institución, ocurrencias separadas,
catálogo sintético, permisos, conflictos y archivo idempotente. No crea cuentas,
persistencia clínica ni datos reales. Recargar la aplicación pierde ese estado DEMO.

## Ejecutar y comprobar

Desde checkout completo con las dependencias frontend instaladas:

```bash
npm --prefix frontend test
npm --prefix frontend run build

# Solo desarrollo: cuatro instituciones con rol admin para probar archivo.
VITE_CLINICAL_MODE=mock VITE_CLINICAL_DEMO_ROLE=admin npm --prefix frontend run dev
# Otra terminal, Node 22+ y Chromium:
npm --prefix frontend run test:browser
```

VITE_CLINICAL_DEMO_ROLE admite admin/medico/secretaria/enfermero/laboratorista y
predetermina medico. Es una configuración del doble, solo cuando DEV y modo mock
explícito están activos. No selecciona institución ni rol de una sesión real; los
builds de producción usan HTTP aun si se definen esas variables. El laboratorista
se debe probar en laboratorio, que es su institución contractual. La cuenta DEMO
mantiene el nombre sintético mostrado en el aviso; la cabecera muestra el rol.

## Evidencia de esta entrega

- **41 pruebas Node aprobadas, cero omitidas**, incluyendo las 33 anteriores.
  Transporte prueba rutas/IDs opacos, CSRF, PATCH, paginación/cancelación, catálogos
  inválidos, errores 400/401/403/404/409/503 sin reintentos. Doble prueba cadena y
  archivo en cuatro instituciones, ocurrencias, referencia de medicamento ausente,
  roles/vínculo profesional y padres de otra institución. Validación prueba campos,
  límites, trim, opcional e IDs opacos preservados.
- **Cuatro recorridos Chromium DEMO aprobados con admin**: alta/consulta, diagnóstico
  vacío con foco, diagnóstico/tratamiento, búsqueda sin resultados, selección de
  catálogo, receta, confirmación de archivo y cadena preservada; doble submit de
  paciente/consulta/diagnóstico/receta, duplicado de paciente y logout. Sin excepciones
  JavaScript. Es navegador real contra un doble, no E2E Django/motores.
- **Build de producción aprobado**, sin dependencias nuevas. También sintaxis/diff
  y conservación de los fixtures frente al backend.

Node 22 para las 41 pruebas (contenedor aislado); Node 24.19.0, React 19.3.0,
Vite 8.3.2 y Chromium locales para build/smoke. Dependencias/build/servidor se ejecutan
en copia temporal work/, sin node_modules, lock nuevo ni dist en la rama. El primer
npm install temporal no pudo usar la caché predeterminada; se repitió con caché
propia en work/ y terminó correctamente. No se modifica configuración global npm.

Identificar código probado mediante `git log -1 -- frontend/src/clinical/ClinicalActionForm.jsx`.
Comandos y resultados anteriores de A3 no se vuelven a contar como pruebas de A4.

## Qué sigue pendiente

Actualización posterior: el flujo común se probó con sesiones y cuatro motores
reales en A5 y nuevamente con el build de producción. Se prepararon pantallas
especializadas DEMO para las cuatro instituciones, con 50 pruebas cliente y siete
recorridos DEMO (cuatro completos y tres por rol). Evidencia y cierre pendiente en
[A4_ESPECIALIZACIONES_Y_CIERRE.md](A4_ESPECIALIZACIONES_Y_CIERRE.md).

**A4 no se declara completo:** falta publicar los contratos/rutas especializados,
conectar las pantallas a proveedores reales y ejecutar su E2E. No se inventan rutas
HTTP para sustituir esa dependencia. La recuperación clínica y el aporte académico
A ya tienen evidencia posterior en A5_RECUPERACION_NOSQL.md y
COMPARATIVO_Y_CLASIFICACION_A.md; no siguen pendientes por este texto histórico.

No se certifica persistencia, autorización Django ni transacciones por pasar los
mocks. No se ejecutaron altas o archivos contra datos de otro integrante. No se
modifica el PR de Pablo ni se publica esta entrega sobre main.
