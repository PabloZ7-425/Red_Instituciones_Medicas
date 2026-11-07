# Traspaso de Pablo para integrar el rediseño

6 de noviembre de 2026. Rama de entrega: **`feat/ui-base`**. Destino según el
[plan vigente](docs/implementacion/PLAN_REDISENO_FRONTEND.md): **`implementacion`**.

## Commits que debes integrar

| Commit | Contenido |
| --- | --- |
| `7d90e1b` | Preparación y reparación del profesional nativo de las cuentas DEMO; pruebas de idempotencia y rechazo de datos incompatibles. |
| `34d66f2` | Presentación de Laboratorio y Pediatría, extensiones compartidas, pruebas Chromium y capturas. |

El commit posterior contiene este traspaso. Integra la rama completa para
incluirlo. No hace falta recuperar archivos de `.local/` para compilar o fusionar.
La base común de ambas ramas es `e0e6010`.

## Estado de validación

- 65 pruebas del frontend aprobadas y build de producción aprobado.
- Cuatro pruebas nuevas de preparación DEMO aprobadas.
- Chromium DEMO: cadena y especialidades en las cuatro instituciones; roles de
  secretaría y laboratorista comprobados.
- Chromium contra Docker compartido: Pediatría y Laboratorio completaron alta,
  consulta, diagnóstico, tratamiento, receta, especialidad y archivo. La lectura
  posterior a recargar conservó la historia y bloqueó nuevas escrituras.
- En ambas instituciones, 400/403/409/503 inyectados en el navegador conservaron
  los valores del formulario especializado. Escape no cerró durante el envío.
  La invalidación real de la sesión devolvió 401 y limpió el contexto clínico.
- Runner dedicado `verify_native.py --run --browser`: **117 aprobadas, cero
  fallidas y cero omitidas**, más cuatro recorridos operativos y siete
  clínicos/de roles de Chromium. Usó motores desechables y terminó con código 0.
- Anchos de 360, 768 y 1280 px comprobados sin desbordamiento de página.

[Detalle, reproducción y capturas](docs/implementacion/REDISENO_PABLO.md).
Los datos de las capturas son ficticios. Revisa escritorio, móvil y vacío como
parte de la revisión cruzada; la automatización no constituye una auditoría WCAG.

## Orden de integración

Conserva los cambios locales antes de cambiar de rama. Actualiza referencias y
revisa la entrega:

```powershell
git status --short --branch
git fetch origin
git log --oneline origin/implementacion..origin/feat/ui-base
git diff --stat origin/implementacion...origin/feat/ui-base
```

Integra `feat/ui-base` en `implementacion` mediante el flujo de revisión del
equipo. Luego incorpora la base integrada en tu rama de Hospital y Odontología:

```powershell
git fetch origin
git switch feat/ui-jennifer
git merge origin/implementacion
```

Después de resolver y validar la combinación, publica tu rama y continúa su
integración hacia `implementacion`. El destino de esta entrega no es `main`.

## Conflicto comprobado con la rama de Jennifer

Se simuló la fusión contra `origin/feat/ui-jennifer` en `da065cb` con
`git merge-tree --write-tree`, sin modificar ninguna rama. Hay **un archivo en
conflicto**, `frontend/src/clinical/SpecialtyDemoPanel.jsx`, con tres bloques.
`frontend/tests/browser-smoke.mjs` se combina automáticamente, conservando las
aserciones de ambas personas. Si cambian los commits remotos, vuelve a comprobar.

Resuelve los tres bloques de la siguiente forma; elegir el archivo completo de
una sola rama perdería extensiones de la otra.

### 1. Extensiones del formulario

Conserva ambas propiedades del perfil:

```jsx
const { ResultFields, fieldControls } = institutionProfile(action.institution)
```

Mantén el bloque de Jennifer que obtiene `FieldControl = fieldControls?.[name]`
y lo presenta antes del control predeterminado. Conserva la extracción de
`ResultFields` de Pablo: ahora vive en `features/laboratorio/ResultFields.jsx` y
lo publica el perfil de Laboratorio. No restaures la antigua función local.

### 2. Extensiones del seguimiento

Conserva el resumen de Jennifer y la sección opcional de Pablo:

```jsx
const profile = institutionProfile(user.institucion)
const { FollowUpSummary } = profile
const Section = profile.SpecialtySection ?? DefaultSpecialtySection
```

Conserva también `DefaultSpecialtySection`, agregada por Pablo. Hospital y
Odontología siguen usando esa envoltura cuando no publican `SpecialtySection`.

### 3. Render del resumen y de las secciones

Después del mensaje de error, conserva las dos extensiones:

```jsx
{rows && FollowUpSummary && <FollowUpSummary rows={rows} />}
{rows && actions.map(([kind, action]) => <Section
  key={kind} kind={kind} action={action} rows={rows[kind] ?? []}>
  {/* Conservar aquí el vacío, listado y botón autorizados existentes. */}
</Section>)}
```

El comentario del ejemplo representa los hijos existentes: **no los elimines**.
El cierre debe ser `</Section>`, correspondiente a la apertura. Conserva
`Overview` en `OperationsWorkspace.jsx`, el odontograma y los perfiles de
Hospital/Odontología de tu rama.

## Validar después de resolver

```powershell
git diff --check
npm.cmd --prefix frontend test
npm.cmd --prefix frontend run build
python -m unittest discover -s ops -p test_bootstrap_professionals.py -v
```

Repite Chromium con los cambios combinados, especialmente el odontograma,
resumen hospitalario, campos variables de Laboratorio y las tres secciones
pediátricas. Conserva las aserciones nuevas de ambos cambios en `browser-smoke.mjs`.
El runner HTTP conserva los valores A5 predeterminados; las opciones para
cuentas locales, recarga, errores y capturas están documentadas en el detalle.

## Corrección local y datos del ensayo

El 403 de Laboratorio estaba causado por un profesional ausente en MongoDB,
aunque el espejo de identidad era válido. Se corrigió la preparación para
crear las referencias nativas DEMO en los dos motores documentales. No cambian
contratos, roles, permisos, contraseñas ni reglas clínicas.

Si tu entorno usa esas cuentas DEMO antiguas y presenta el mismo problema,
ejecuta primero el diagnóstico de `ops/repair_demo_professionals.py` descrito
en el detalle. `--apply` solo crea un registro ausente, con el perfil DEMO
esperado y activo; no sustituye ni reactiva registros existentes.

El entorno local conserva los pacientes ficticios `UI-PABLO-20261106A` a `H`.
Algunos intentos iniciales quedaron incompletos; no se borraron para repetir
pruebas. Usa una identificación nueva en cada ejecución. Las credenciales,
respaldos y logs privados están excluidos de Git. Los motores del runner
aislado fueron retirados por el propio runner.
