# Cliente React — avance A4: sesión, lectura y registro de pacientes

Contrato normativo: CONTRACT-API-01@1.0.0 del plan operativo 2.0. Se conservan
intactos los diez fixtures históricos y su comparación byte a byte con backend.
Sus metadatos «candidato» describen su origen histórico, no el contrato vigente.

## Implementado

- Navegación entre pacientes y el panel de conexiones existente.
- Login, recuperación de sesión con /me y logout. La institución proviene de la
  sesión; no hay selector de motor. La contraseña se vacía al enviar el formulario.
- Cliente HTTP separado: cookies con credentials: include, CSRF antes de login,
  nueva lectura CSRF tras su rotación, logout 204 sin intentar parsear JSON vacío.
  No persiste tokens/contraseña en localStorage ni reintenta escrituras a ciegas.
- Listado por prefijo y paginación de 20; búsqueda vacía, carga, error y reintento.
  Solicitudes anteriores se cancelan y sus resultados tardíos se ignoran.
- Historia paciente→consultas→diagnósticos→tratamientos→recetas, fechas civiles
  conservadas como texto, arrays vacíos y archivo con motivo/fecha sin borrar historia.
- Registro API-04 con identificación/nombres/apellidos/nacimiento; trim y límites
  20/100/100, calendario válido y nacimiento no futuro según America/Guatemala.
  Mantiene ceros iniciales y fechas civiles sin conversión a instantes. Muestra
  errores junto al campo y enfoca el primero; conserva el formulario ante 400/409.
  Durante el envío bloquea guardado/cancelación/logout y evita submits simultáneos.
  Error de red no se presenta como éxito ni se reintenta automáticamente: indica
  buscar la identificación antes de repetir, porque el resultado puede ser incierto.
  Tras éxito actualiza el filtro/listado y abre el historial vacío si el rol permite.
- Alta visible para admin/medico/secretaria y laboratorista solo en laboratorio.
  El mock comprueba esa matriz; el backend debe autorizarla de forma independiente.
- Secretaria puede ver listado; no se ofrece botón de historia para ese rol.
  Esto es presentación; la autorización e institución deben validarse en backend.
- Doble DEMO explícito, en memoria, para cuatro instituciones. Sus usuarios y clave
  son texto sintético para el navegador, no cuentas Django/Firebase/Mongo.

## Ejecutar

Desde un checkout completo con Node compatible con Vite 8:

```bash
npm --prefix frontend install --package-lock=false
npm --prefix frontend run dev
```

Por defecto usa HTTP real en `http://localhost:8000/api`; se puede configurar
`VITE_API_URL` manteniendo el prefijo `/api` y sin slash final. Utilizar el mismo
hostname que backend (localhost en ambos, o 127.0.0.1 en ambos) para cookies/CSRF.
CORS y trusted origins son configuración de Pablo. No se modificó Compose ni .env.

Para ver el avance sin API, activar DEMO **solo en desarrollo**:

```bash
VITE_CLINICAL_MODE=mock npm --prefix frontend run dev
```

PowerShell:

```powershell
$env:VITE_CLINICAL_MODE='mock'
npm --prefix frontend run dev
# Al terminar:
Remove-Item Env:VITE_CLINICAL_MODE
```

La pantalla muestra el aviso DEMO y las credenciales ficticias. Usuarios:
`DEMO-medico-hospital`, `DEMO-medico-pediatrico`, `DEMO-medico-laboratorio`,
`DEMO-medico-odontologica`; clave `DEMO-no-utilizar`. No usar datos reales.
El mock se activa solo con import.meta.env.DEV y esa variable explícita. Los
builds de producción usan HTTP aunque se haya definido VITE_CLINICAL_MODE=mock;
no existe fallback a datos ficticios ante errores de conexión o de API.

## Pruebas

```bash
npm --prefix frontend test
npm --prefix frontend run build
```

El primer comando ejecuta 26 pruebas (ocho históricas, diez de sesión/lectura y
ocho de registro). Estas verifican
la secuencia CSRF/login/rotación/logout, password sin trim, estados/campos de error,
red/cancelación, IDs opacos, sesión y búsqueda DEMO, archivo/fechas/vacíos/permisos.
Se añaden validación de fecha/textos, envío POST/CSRF, errores de alta, duplicados,
aislamiento DEMO y paginación tras crear varios pacientes.
Son dobles de transporte/servicio; no pruebas de autorización real de Django.

Smoke de navegador con Node 22+ y Chromium instalado, sin dependencias npm nuevas:

1. Iniciar Vite en modo DEMO como arriba en una terminal.
2. En otra terminal ejecutar:

```bash
npm --prefix frontend run test:browser
```

Usa por defecto `http://127.0.0.1:5173/`; `BROWSER_URL` permite otra URL local.
`CHROMIUM_PATH` permite la ruta al ejecutable (en Windows, Chromium o Chrome).
El script crea su propio perfil temporal e inicia únicamente su propio navegador
headless; lo cierra al terminar. Usa --no-sandbox para el contenedor de pruebas,
no cambia la configuración del navegador habitual. Exige el aviso DEMO antes de
introducir credenciales ficticias y rechaza destinos remotos. Recorre las cuatro
instituciones: login, búsqueda vacía/prefijo, historial, alta con campos inválidos,
fecha futura, alta válida/lectura posterior, doble submit, duplicado con datos
conservados y foco en el campo, cancelación, logout y ausencia de errores JS.

## Evidencia y pendientes

Ejecución 20 de octubre de 2026, America/Guatemala. Base de este incremento `651fbbf`;
commit de esta entrega identificable con `git log -1 -- frontend/README.md`.
Node 24.19.0, React 19.3.0, Vite 8.3.2, Chromium del entorno Codex:

- 26 pruebas Node: aprobadas, cero omitidas.
- Build de producción: aprobado.
- Cuatro recorridos Chromium DEMO: aprobados; sin excepciones JavaScript.
- git diff --check: aprobado.

**A4 sigue parcial.** Pendientes: consulta, diagnóstico,
tratamiento, selección de medicamentos CAT-01/receta, archivo y especializaciones.
La lectura actual de receta muestra dosis/frecuencia/vía; resolver el nombre del
medicamento desde catálogo se completará con CAT-01, sin pedir IDs a mano.
Falta E2E contra API real de cuatro instituciones. No se declara persistencia ni
seguridad real a partir del mock. B2/B5 deben entregar AUTH-CSRF/API-01/API-02/
AUTH-LOGOUT/API-03/API-04/API-05 con sesiones, CSRF, errores uniformes y roles; A3/B1 deben
conectar esas lecturas y el alta a los repositorios. El mock no altera puertos o endpoints.

El mock conserva las altas solo en memoria durante esa ejecución de la app,
separadas por institución, y las pierde al recargar. No modifica fixtures históricos.
El nombre de cuenta DEMO-medico corresponde al perfil de ejemplo; no habilita cuentas
reales ni sustituye roles del backend. Los tests de rol usan perfiles internos del doble.

Incidencias del smoke corregidas: esperar a que exista document.body antes de leer
texto; usar identificaciones DEMO de hasta 20 caracteres en todas las instituciones
(las largas fueron rechazadas correctamente por el formulario). La ejecución final
pasó los cuatro recorridos completos. No se ejecutó alta contra backend real.

Entrega exclusivamente en feature/jennifer, sin PR ni merge. A1/A2 permanecen
preservados en esa rama; no sincronizar ciegamente el revert de main sobre su código.
