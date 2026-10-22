# A4 cerrado — React, API y especializaciones reales

Jennifer, 22 de octubre de 2026. Estado: **A4 cerrado en feature/jennifer**, pendiente
de la decisión/procedimiento de integración a main. Esta evidencia sustituye el
pendiente técnico de A4_ESPECIALIZACIONES_Y_CIERRE.md, que se conserva como historia
de la preparación DEMO. No implica finalizar todo A5 ni la entrega académica.

## Alcance y autorización

Jennifer pidió «cierra A4» y después «Esta bien hazlo» al proponerse publicar
contratos/rutas y conectarlas. Se comunicó la interpretación: autorización para
los cambios centrales necesarios **solo en feature/jennifer**, como excepción al
límite de archivos del plan. No se cambia la propiedad permanente ni se edita la
rama de Pablo, su PR #16 o main. B5 `0ecf7d5` se incorporó sin conflictos mediante
merge `a1747cd`; A1/SQLite se conservaron. El resto son cambios de esta entrega,
identificables por `git log -1 -- docs/jennifer/A4_CIERRE_REAL.md`.

## Resultado funcional

El flujo común conserva login/cookies/CSRF, búsqueda/alta de pacientes, historia,
consulta, diagnóstico, tratamiento, catálogo/receta y archivo en cuatro motores.
La interfaz ahora opera además con HTTP real:

- Hospital: ingreso y alta, con camas e ingresos seleccionados por etiquetas.
- Pediatría: tutores, aplicaciones de vacuna y controles en kg/cm; secretaría
  gestiona tutores desde listado sin solicitar historia ni seguimiento clínico.
- Laboratorio: resultados con campos numéricos, texto y booleanos, examen de
  catálogo y estado. Laboratorista puede registrarlos sin prescribir.
- Odontología: procedimientos por pieza FDI, ligados al tratamiento de la misma
  historia, con consulta resuelta por el servidor.

El contrato aditivo está en [SPECIALTY_API_01.md](SPECIALTY_API_01.md). Componentes
con nombre histórico SpecialtyDemoPanel/specialty-demo se reutilizan con un servicio
HTTP separado: el sufijo/aviso DEMO solo aparece si el modo es mock. El servicio
HTTP no utiliza el doble ni lo activa por fallos. Fechas, decimales, tipos JSON y
IDs se transforman según contrato, sin pedir IDs internos a mano. Catálogos con
carga/vacío/error/reintento; formularios con errores vinculados, foco, conservación
de datos y bloqueo de doble envío/navegación durante guardado. Archivo retira las
acciones y conserva todas las lecturas.

Cerrar sesión cancela las cadenas de lecturas especializadas y bloquea nuevas
lecturas de esa cadena; login las reactiva. Esto evita que una consulta secundaria
de catálogo continúe después de invalidar la sesión. No hay reintentos automáticos
de escrituras. Un resultado de red/JSON no confirmado indica actualizar antes de
repetir. Los mensajes HTTP no simulan persistencia.

## Evidencia final

| Comprobación | Resultado |
|---|---|
| Cliente Node 22, incluidos tipos/rutas/CSRF, paginación, errores y cancelación al logout | **55 aprobadas, 0 omitidas** |
| Backend sin destinos externos, config.test_settings | 212 descubiertas: **99 aprobadas, 113 omitidas** por activación/destinos de integración. Incluye seis nuevas pruebas de especialización; no son 212 integraciones reales. |
| Contrato NoSQL común nativo, namespaces A3 generados | **49 aprobadas, 0 omitidas**, replica set a3 y proyectos emulados aislados |
| Chromium del build de producción, flujo común y siete operaciones especializadas | **4 recorridos aprobados**, HTTP real y cuatro motores |
| Chromium HTTP por rol: secretaría, enfermería, laboratorista | **3 recorridos aprobados**, sin excepciones JS ni fallos HTTP inesperados |
| A5 HTTP/nativo común | **8 aprobadas, 0 omitidas** |
| Nuevas pruebas HTTP/nativas especializadas | **6 aprobadas, 0 omitidas** |
| Auditoría de cuatro puertos B5 y comprobación de arranque | Código 0; **18 comprobaciones OK** |
| Build producción, sintaxis y git diff --check | Aprobados |

Los recorridos crean datos nuevos y vuelven a leerlos desde API. Las seis pruebas
especializadas comparan esas respuestas con repositorios/conexiones nativas:
un ingreso/alta, un tutor/vacuna/control, un resultado con `[3.5,false,texto]` y un
procedimiento por pieza. Comprueban siete rechazos de escritura tras archivo,
proyección de tutores sin historia para secretaría, rol/institución antes del body,
referencia cruzada de tratamiento, fallo inyectado que revierte hijo **y versión
raíz**, y cuatro carreras nativas archivo/escritura (dos por motor NoSQL). Son
solapamientos con barrera, no una garantía de haber forzado ambos órdenes de commit.
También verifican orden temporal con milisegundos y catálogo de examen ausente/ajeno.

## Entorno y reproducción

Se usaron exclusivamente contenedores/volúmenes desechables propios, bases nuevas,
cuentas DEMO y catálogos sintéticos de A5; mismos motores/herramientas que A5.
No se aplicaron procedimientos sobre datos compartidos. Fuentes temporales de
backend/apps, db/mongo y frontend se copiaron desde esta entrega. La comparación
final de fuentes usadas excluye solo pycache y metadatos locales, no los módulos
de ejecución. La reproducción publicada admite fijar ambos refs al commit final
de esta rama, que ya contiene B5:

```bash
python docs/jennifer/a5/configure.py --runtime /ruta/nueva/work/a5-runtime \
  --pablo-ref <commit-de-esta-entrega> --jennifer-ref <commit-de-esta-entrega>
# Iniciar los servicios nuevos como en A5_INTEGRACION_REAL.md y ejecutar prepare.py.
python docs/jennifer/a5/prepare.py --runtime /ruta/nueva/work/a5-runtime
python docs/jennifer/a5/check_startup.py --runtime /ruta/nueva/work/a5-runtime
python docs/jennifer/a5/serve.py --runtime /ruta/nueva/work/a5-runtime
```

La preparación A5 ahora añade cama, vacuna, catálogo de exámenes y esquema LAB-01
solo en sus destinos vacíos. En la copia frontend, build con
VITE_API_URL=http://127.0.0.1:18005/api; servir `npm run preview -- --host 127.0.0.1
--port 18173`. Se probó ese build aun con VITE_CLINICAL_MODE=mock definido: producción
usó HTTP sin avisos de simulación. Después, desde el checkout de la entrega:

```bash
export A5_RUNTIME=/ruta/nueva/work/a5-runtime
export A5_REAL_HTTP=1
export A5_BROWSER_PASSWORD=DEMO-only-isolated-A5-2026
BROWSER_URL=http://127.0.0.1:18173/ npm --prefix frontend run test:browser:real
python docs/jennifer/a5/test_http.py
python docs/jennifer/a5/test_specialties.py
# Cada rol se ejecuta una vez contra sus fixtures dedicados:
A4_HTTP_BROWSER_ROLE=secretaria npm --prefix frontend run test:browser:real
A4_HTTP_BROWSER_ROLE=enfermero npm --prefix frontend run test:browser:real
A4_HTTP_BROWSER_ROLE=laboratorista npm --prefix frontend run test:browser:real
python docs/jennifer/a5/stop.py --runtime "$A5_RUNTIME"
```

Los fixtures del navegador requieren destinos nuevos; no ejecutarlos de nuevo sobre
datos compartidos ni asumir que borran ejecuciones previas. Las suites NoSQL y
común se reproducen con las variables/guardas de sus documentos. La contraseña
publicada solo corresponde a esas cuentas desechables, no a usuarios persistentes.

## Incidencias y límites

El primer ensayo HTTP especializado encontró una espera insuficiente al cargar
opciones; el smoke ahora espera botones habilitados. Otro ensayo completó las
cuatro instituciones pero detectó una lectura de vacunas 401 después de logout:
se corrigió la cancelación, se añadió regresión Node y se repitió desde bases
nuevas. La validación de un entero JSON extremadamente grande produjo OverflowError
en el primer test unitario: se corrigió el orden de validación y se repitió la
suite. Solo los resultados finales aprobados se cuentan en la tabla.

No se certifica despliegue productivo, TLS, autorización directa de Mongo/Firebase,
HA, rendimiento, conciliación universal de históricos ni recuperación de identidad
SQL. La recuperación NoSQL previa sigue documentada para su conjunto probado;
esta entrega no afirma haber repetido un ensayo frío con las nuevas colecciones.
El arranque/actualización compartidos y controles de GitHub siguen siendo una
comprobación separada antes de recomendar merge. A5 mantiene el cierre documental
académico y cualquier evidencia adicional de entrega que corresponda.
