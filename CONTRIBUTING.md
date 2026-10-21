# Contribución por módulos

Flujo vigente: [PLAN_MAESTRO.md](PLAN_MAESTRO.md) versión 2.0.
Manuales: [Jennifer](GUIA_JENNIFER_AGENTES.md) y [Pablo](GUIA_PABLO_AGENTES.md).

## Ramas y propiedad

Solo main, feature/jennifer y feature/pablo. Cada célula trabaja siempre en su
rama permanente y solo en los archivos asignados en el maestro. No ramas por
tarea/arreglo/documento, ni código directo en main. Un módulo coherente y un PR
activo por rama. No exigir aprobación de la otra célula; respetar los checks y
revisiones que GitHub realmente requiera, sin bypass administrativo.

```powershell
git fetch origin
git switch feature/pablo  # O feature/jennifer, según responsable
# Preservar primero trabajo local pendiente en rutas propias.
git merge origin/main
# Implementar y probar módulo.
git diff --check
git add -- <rutas-propias>
git commit -m "feat(auth): implementa sesiones institucionales"
git push -u origin feature/pablo
```

Después de integrar, no borrar las ramas permanentes; actualizar desde main antes
del módulo siguiente. Preferir merge commit, sin force push, reset destructivo ni
rebase que pierda trabajo. No añadir cambios de otro módulo a un PR ya abierto.

## Calidad y contratos

Commits Conventional Commits: tipo(scope): descripción concreta. feat, fix, test,
docs, chore o refactor. No mensajes «varios», «final» ni «fix» sin descripción.
Las interfaces públicas siguen CONTRACT-API-01@1.0.0 y CONTRACT-REPO-01@1.0.0
documentados en el maestro. B publica especificación/pruebas; cada consumidor la
implementa sin aprobación humana entre células. Incompatibles requieren major y
transición preservando v1; no renombrar campos/rutas en sitio.

Antes de commit/PR: revisar diff, rutas propias, secretos y pruebas del módulo.
Antes de merge: sincronizar main y validar lo afectado. Baseline disponible:

```powershell
docker compose config -q
docker compose exec -T backend python manage.py check
docker compose exec -T backend python manage.py test apps.historiales
node --test frontend/tests/contract-fixtures.test.js
docker compose exec -T frontend npm run build
```

NoSQL/SQL requieren destinos aislados y comandos de sus READMEs. Test cliente
desde checkout completo, no solo el mount frontend. No anunciar lint u otros
runners inexistentes; registrar aprobadas/fallidas/omitidas por separado.
PR incluye módulo/dueño, versión contratos, archivos, alcance, comandos/resultados,
evidencia y límites. No integrar con criterios obligatorios fallidos o sin verificar.

## Datos y coordinación técnica

No subir .env, contraseñas, tokens, bases SQLite, dumps con datos reales,
node_modules ni volúmenes. Usar DEMO. No borrar volúmenes para actualizar esquemas;
migraciones con respaldo/reversión y pruebas aisladas. Las capacidades centrales
necesarias se describen al dueño del archivo con prueba esperada; se continúa
trabajo independiente. Escalar solo seguridad, pérdida de datos, incumplimiento
académico o contradicción no resoluble mediante contratos/versiones.
