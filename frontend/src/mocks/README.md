# A-C0-T1 — fixtures cliente del contrato candidato

**PROVISIONAL / modo mock.** PR-01 del plan, no un número GitHub. Base
`f35207d7854e06122cfb30ee475b806cf0650c1e`, incluye PR #2 de Pablo. F0 continúa
abierto: esta entrega permite revisar estructuras desde React sin fingir que las
diez operaciones, una sesión o un adaptador clínico ya existen.

## Archivos y uso

- `contrato_v1.json`: copia **sin modificaciones** del fixture B en
  `backend/apps/historiales/fixtures/contrato_v1.json` de la base indicada.
- `contract-fixtures.js`: acceso a los diez casos y sus respuestas válida/inválida;
  cada llamada devuelve una copia independiente para evitar contaminación entre UI.
- `ui-scenarios.js`: ejemplos derivados para lista/historial vacíos, historial
  archivado conservado y errores 400/401/403/404/405/409/415/500/503 según D0-04.
- `REVISION_A_C0.md`: revisión A, decisiones y dependencias concretas de B-C0-T1.

```javascript
import { getFixtureMetadata, getResponseFixture } from './contract-fixtures.js'
import { getUiScenarios } from './ui-scenarios.js'

const metadata = getFixtureMetadata() // mostrar modo mock al conectarlo a una UI
const login = getResponseFixture('API-01')
const lista = getResponseFixture('API-03')
const historial = getResponseFixture('API-05')
const invalido = getResponseFixture('API-04', { invalid: true })
const estados = getUiScenarios()
```

Los envoltorios `{status, body}` describen fixtures, no son el JSON que enviará la
API: el cuerpo es `body`. Los `request` de GET en el archivo describen parámetros
de consulta; no autorizan enviar cuerpos GET. Los mensajes de los escenarios
adicionales son ilustrativos, no textos normativos de error. React deberá usar
`error.code` y `fields` al integrar. La metadata es local al modo mock, no se añade
a respuestas API ni a los DTOs de Pablo.

Se preservan nombres, rutas, fechas civiles, null en lectura y cadenas de IDs del
candidato. La identificación es cadena. No se transforma fecha civil con `Date`
ni se convierte BSON en componentes. El ejemplo de login contiene solo las cadenas
sintéticas de B `DEMO-*`: no crea usuario, sesión, cookie ni token.

No hay servidor mock, interceptores HTTP, estado clínico mutable ni lógica de
persistencia. No se añadieron rutas, fetch, almacenamiento del navegador ni cambios
a `src/api/health.js`, `App.jsx` o `HomePage.jsx`. Nada activa estos fixtures en el
panel real. Loading y error de red serán estados de UI/servicio, no payloads API.
Los ejemplos cubren hospital como el fixture B original: no acreditan ejecución
contra cuatro motores ni permisos de laboratorista.

## Pruebas y build

Desde `frontend/`, Node **22.12+** (Node 22 del Dockerfile) o 24:

```bash
npm run test:contract
npm install --no-package-lock --no-audit --no-fund
npm run build
```

`test:contract` es un script nuevo para el runner nativo `node --test`; no instala
Vitest, Jest, ESLint, mock servers ni otra dependencia. Las pruebas de fixtures no
necesitan `npm install` porque usan módulos nativos. El build sí requiere instalar
las dependencias ya declaradas; se conserva la política actual sin archivo lock.
Este comando de instalación no sustituye un acuerdo futuro sobre reproducibilidad
de dependencias.

La suite comprueba copia exacta de los ejemplos B, diez operaciones, aislamiento
entre consumidores, JSON sin tipos internos/secretos en respuestas, relaciones
del historial y rutas, fechas/null/UTF-8, archivo/vacío y formato de errores. Si B
cambia su fixture, la comparación falla: revisar el cambio antes de copiar la nueva
versión y actualizar la referencia, no ocultar el fallo transformando campos.

## Evidencia de esta entrega

- Node 24.19.0 / npm 11.9.0: **8 pruebas OK, 0 omitidas**.
- `npm run build`: Vite 8.3.2, **OK**. El build conserva la aplicación de salud;
  no prueba pantallas clínicas ni integración de endpoints candidatos.
- Compilación Vite independiente de `ui-scenarios.js` como módulo de navegador,
  con `write: false`: **OK**. Comprueba que la importación JSON también es válida
  para el bundler, sin conectar fixtures al flujo real de la aplicación.
- Sintaxis Node, revisión de archivos propios y `git diff --check`: **OK**.
- Nuevas dependencias: **ninguna**; no se modifican archivos B ni infraestructura.

## Cierre pendiente

Esta entrega cubre preparación/revisión estática de A-C0-T1. No declara su DoD
completo: falta ratificación A↔B y ajustar la copia al SHA final del contrato,
revisión cruzada y Gate F0. Identidad diagnóstica MySQL y coordinación de
infraestructura Mongo se detallan en la revisión adjunta. Puede revisarse como
borrador sin bloquear las otras verificaciones de Jennifer.
