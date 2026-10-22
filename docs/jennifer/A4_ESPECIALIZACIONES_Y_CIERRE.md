# A4 — especializaciones y criterios de cierre

**Documento histórico:** sus pendientes de contrato/transporte/E2E ya se cerraron
en la entrega posterior [A4_CIERRE_REAL.md](A4_CIERRE_REAL.md). No usar el estado
DEMO de este documento como estado actual de la rama.

Jennifer, 22 de octubre de 2026. Base: `866b9f3`. Cambios solo en frontend y
documentación propia. No se modifica B5, contratos centrales, PR #16 ni main.

**A4 sigue pendiente de cierre integral.** El flujo común ya funciona con HTTP y
cuatro motores reales. Se completó la preparación de pantallas especializadas
mediante un servicio DEMO explícito; no se presentan como operaciones persistidas.
La API B5 inspeccionada en `feature/pablo` sigue en `0ecf7d5` y publica únicamente
las rutas comunes. No existen rutas HTTP especializadas que estas pantallas puedan
consumir conforme al plan. El código de esta entrega se identifica mediante
`git log -1 -- frontend/src/clinical/SpecialtyDemoPanel.jsx`.

## Pantallas preparadas

| Institución | Operaciones DEMO | Fuente y límites |
|---|---|---|
| Hospital | Ingreso, listado y alta | Campos de CONTRACT-HOSPITAL-01, selección de cama/ingreso por etiqueta, timestamps UTC explícitos, exclusividad de cama, alta no anterior al ingreso e idempotencia. Catálogo de camas DEMO: no hay catálogo HTTP publicado. |
| Pediatría | Tutores, vacunas y crecimiento | Campos PED-01, selección de vacuna, fechas civiles y medidas string con unidades kg/cm y dos decimales. Sin cálculo de percentiles/calendario ni inferencia de unidades heredadas. |
| Laboratorio | Registro y lectura de resultados | Prototipo basado en el modelo A2: examen de catálogo, instante UTC, estado y hasta 50 campos con texto/número/booleano y unidad/referencia opcional. No interpreta rangos médicos. El identificador DEMO del examen no define el futuro DTO HTTP ni migra referencias BSON legadas. |
| Odontología | Registro y lectura de procedimientos | Prototipo basado en A1: pieza FDI, descripción, estado y tratamiento seleccionado desde la misma historia; consulta derivada de ese tratamiento. No hay ruta ni puerto público especializado certificado. No se incluyen pagos, que no son requisito obligatorio del plan. |

Las operaciones `specialtyDemo.list/catalog/save` son una interfaz interna del
doble de frontend; **no son contratos del backend** ni una propuesta de rutas HTTP.
Hospital/PED-01 aportan campos de repositorio, pero todavía falta definir su
transporte HTTP, catálogos y proyección final. Los permisos del doble se inspiran
en B3/B4 y en el rol laboratorista; no sustituyen autorización del servidor.

El servicio HTTP no posee `specialtyDemo`. Las pantallas se muestran solo cuando
`service.mode === 'mock'` y existe ese doble. Un fallo del backend no activa mocks.
Producción continúa usando HTTP aun con variables VITE de DEMO. No se guardan
datos en localStorage ni se escriben colecciones, cuentas o semillas.

## Comportamiento y permisos

- Los formularios comparten el bloqueo de navegación/acciones durante guardado,
  evitan doble envío con ref y conservan valores/errores cuando falla el registro.
  Etiquetas, errores vinculados y foco del primer campo inválido están presentes.
- Los catálogos tienen carga, vacío, error y reintento; el usuario selecciona
  etiquetas. Tratamientos e ingresos ajenos al paciente no se ofrecen ni aceptan.
- Después de archivar se conserva la lectura especializada y desaparecen las
  acciones de escritura. El doble rechaza también llamadas directas posteriores.
- Admin/médico operan sus especializaciones. Secretaría pediátrica gestiona
  tutores desde el listado sin solicitar/recibir historial clínico ni seguimiento
  de vacunas/crecimiento. Enfermería solo lee; laboratorista registra resultados
  de su institución sin obtener diagnóstico o prescripción.
- Cada institución/paciente tiene registros DEMO propios. Logout conserva el
  estado de la ejecución, pero impide leer/escribir sin sesión DEMO; recargar
  elimina toda esa memoria. No hay persistencia ni concurrencia distribuida.

## Evidencia ejecutada

- **50 pruebas Node 22 aprobadas, cero omitidas**: 41 previas y nueve nuevas.
  Incluyen referencias cruzadas, roles, archivo, cama ocupada/reutilización,
  cronología/idempotencia de alta, tipos de resultados, FDI, fechas imposibles,
  desconocidos/null, decimales explícitos y separación entre doble y cliente HTTP.
- **Cuatro recorridos Chromium DEMO completos** con admin: flujo común seguido de
  las siete altas especializadas, lectura posterior, doble submit y archivo que
  conserva los registros y retira las acciones. Sin errores JS.
- **Tres recorridos Chromium por rol**: secretaría con tutor sin acceso a historia,
  enfermería de lectura y laboratorista con resultado sin prescripción. Cada uno
  cierra sesión. No se presentan estas pruebas como autorización Django.
- **Build de producción aprobado**, con VITE_CLINICAL_MODE=mock y rol DEMO admin
  deliberadamente activados, API apuntando al entorno desechable A5. El build
  siguió usando HTTP, sin aviso DEMO.
- **Cuatro recorridos Chromium del build de producción con HTTP real** contra B5
  `0ecf7d5` y adaptadores A3 de la copia A5: login, alta, consulta, diagnóstico,
  tratamiento, catálogo, receta, archivo y logout. Bases/roles/catálogos/cuentas
  nuevos y sintéticos. No se vuelve a atribuir esta evidencia a especializaciones.

Se utilizó copia temporal fuera del checkout para dependencias, build, servidores,
logs y perfiles. No se añadieron dependencias, lock, dist ni datos clínicos al Git.
El primer smoke nuevo esperaba una frase de error distinta a la del selector;
se ajustó esa expectativa y los cuatro recorridos finales pasaron. La ejecución
nativa Node 24 resumió por archivo; el conteo de 50 procede del runner Node 22.

## Reproducir frontend

```bash
npm --prefix frontend test
npm --prefix frontend run build

# Servidor de desarrollo DEMO admin:
VITE_CLINICAL_MODE=mock VITE_CLINICAL_DEMO_ROLE=admin npm --prefix frontend run dev
# Otra terminal:
npm --prefix frontend run test:browser
```

Para cada rol, reiniciar el servidor con `VITE_CLINICAL_DEMO_ROLE` igual al rol
elegido y ejecutar el smoke con `A4_DEMO_BROWSER_ROLE` del mismo valor:

```bash
A4_DEMO_BROWSER_ROLE=secretaria npm --prefix frontend run test:browser
# Repetir con enfermero y laboratorista y su servidor correspondiente.
```

Node 22+ y Chromium; BROWSER_URL permite un servidor local en otro puerto. El
smoke completo sin A4_DEMO_BROWSER_ROLE exige admin o médico con vínculo DEMO;
admin comprueba también archivo. Para HTTP real, usar la reproducción A5 con
fuentes frontend de esta entrega y destinos nuevos: el smoke no borra ejecuciones
anteriores. En esta ejecución se sirvió el build mediante Vite preview en 18173,
con el origen local permitido por a5_settings de la copia temporal.

## Qué falta exactamente para cerrar A4

1. Publicar extensiones centrales: rutas/métodos, DTOs, permisos y respuestas de
   hospital/PED-01 y contratos de laboratorio/odontología, incluidos catálogos
   de camas, vacunas y tipos de examen. Los campos de repositorio no permiten
   deducir por sí solos los endpoints. Esta publicación es de la zona de Pablo.
2. Implementar o completar el transporte especializado y los proveedores reales
   correspondientes. NoSQL requerirá extensiones propias de Jennifer conforme
   al contrato; los ejemplos A1/A2 no sustituyen repositorios operativos.
3. Conectar las pantallas al servicio HTTP autorizado, manteniendo IDs opacos,
   sesión/CSRF y prohibición de escrituras tras archivo. Ajustar el prototipo
   al contrato publicado, sin imponer el formato interno DEMO al backend.
4. Ejecutar E2E real especializado en cuatro motores, comprobar lectura posterior,
   permisos, referencias y archivo. Solo entonces cambiar A4 a cerrado.

El pendiente del arranque compartido para merge se documenta por separado en
ARRANQUE_FLUJO_COMUN.md. No es un reemplazo de estos criterios A4 ni una razón
para rehacer el flujo común ya probado.
