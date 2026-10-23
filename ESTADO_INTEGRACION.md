# Estado consolidado del proyecto

> Registro histórico de la integración anterior. El flujo vigente está en
> [PLAN_MAESTRO.md](PLAN_MAESTRO.md) versión 2.0: dos ramas de desarrollo permanentes,
> módulos autónomos y contratos 1.0.0. Las referencias a F0 o revisión cruzada de
> este informe describen el método anterior y no son requisitos operativos actuales.

## Actualización B1–B5 — 2026-10-21

**Estado vigente, 2026-10-22:** Jennifer ababb13 y B5 compuestos en feature/pablo
mediante merge 301dd45. No se modificó main. Ya existen los dos puertos NoSQL y
la interfaz común/especializada: auditoría código 0, arranque compartido 18 OK,
230 backend, 55 cliente, 14 HTTP/nativas y 10 recuperación fría aprobadas sin skips,
siete recorridos Chromium y dos escenarios adicionales de recuperación especializada.
Entorno local con cuatro cuentas DEMO, catálogos y cero pacientes. La preparación
es explícita, respaldada e idempotente. PR #16 permanece sin merge por instrucción
del usuario. Vite pendiente de actualización por A; servidor de desarrollo retirado
del arranque común. [Cierre actualizado](docs/pablo/B5_CIERRE_INTEGRADO.md).

El siguiente párrafo conserva el primer avance histórico de B5:

B1–B4 integrados mediante PRs #12–#15. B5 implementa la API clínica central,
integración HTTP con SQL y Mongo rs0 con conversión respaldada/restaurada.
172 pruebas B1–B5 aprobadas sin omisiones, ocho del contrato cliente y build/check
correctos. Cuatro conexiones saludables no significan cuatro repositorios clínicos.
MongoAdapter y FirestoreAdapter siguen siendo solo salud; gate
`audit_clinical_providers --require-all` falla con código 1 y sus operaciones HTTP
devuelven 503. **B5 no está cerrado:** integración clínica NoSQL/React pendiente A.
El avance se publica como borrador sin merge hasta cumplir ese cierre.
[Procedimiento/evidencia B5](docs/pablo/B5_API_INTEGRACION.md) y
[comparativo/clasificación](docs/pablo/COMPARATIVO_MOTORES.md).

El resto de este documento conserva el informe histórico del 2026-10-20.

Fecha: **2026-10-20**, America/Guatemala. Coordinación de integración: Pablo.
Solicitud: integrar todos los trabajos publicados de forma gradual, validar main
y dejar el avance documentado. Esta solicitud autoriza reunir también los trabajos
preparatorios que seguían en borrador; no convierte propuestas en funciones activas.

**Base de código consolidada y validada:**
`9eae5783007d70da6d1cd225bb246db0d4baac23`.
La integración posterior de este documento añade únicamente documentación.
Para obtener el SHA actual, ejecutar `git rev-parse HEAD` después de sincronizar main.

## Integraciones realizadas

Los PR se integraron individualmente con commits de merge, conservando la historia
de sus ramas. Se actualizaron los archivos locales y se comprobaron las pruebas
basales después de cada integración. No hubo conflictos de Git ni resoluciones
manuales que reemplazaran contenido de otra célula.

| Orden | PR GitHub | Contenido | Commit de integración |
|---|---|---|---|
| Antecedente | [#1](https://github.com/PabloZ7-425/Red_Instituciones_Medicas/pull/1) | Plan maestro y guías | e9b2efa |
| Antecedente | [#2](https://github.com/PabloZ7-425/Red_Instituciones_Medicas/pull/2) | Contratos candidatos, decisiones, ejemplos y pruebas UTF-8 | f35207d |
| Antecedente | [#5](https://github.com/PabloZ7-425/Red_Instituciones_Medicas/pull/5) | Salud respeta False; revisión aprobada por Jennifer | f671245 |
| 1 | [#6](https://github.com/PabloZ7-425/Red_Instituciones_Medicas/pull/6) | Resoluciones SQL y propuestas de permisos, búsqueda y catálogo | 610d86c |
| 2 | [#8](https://github.com/PabloZ7-425/Red_Instituciones_Medicas/pull/8) | Experimentos SQL con trece casos reales | 4a44ab6 |
| 3 | [#7](https://github.com/PabloZ7-425/Red_Instituciones_Medicas/pull/7) | Fixtures React, escenarios y revisión A | 63dfc23 |
| 4 | [#3](https://github.com/PabloZ7-425/Red_Instituciones_Medicas/pull/3) | Modelo/seed/exportación Firestore y pruebas | bc7ce90 |
| 5 | [#4](https://github.com/PabloZ7-425/Red_Instituciones_Medicas/pull/4) | Validadores MongoDB, dataset y pruebas | 9eae578 |

Los números GitHub difieren de los identificadores PR-XX del plan. Las notas de
cada rama que dicen «borrador» o «no fusionado» son antecedentes del momento en
que se escribieron; esta tabla registra su estado de integración actual.

## Qué está hecho y dónde está

| Área | Entregado | Referencia |
|---|---|---|
| Infraestructura | Compose con siete servicios y conexión a cuatro motores | docker-compose.yml; /api/health/databases/ |
| Backend basal | Endpoints de salud y manejo correcto de False/excepción por motor | backend/apps/historiales/application/database_health.py |
| Contratos | Diez operaciones candidatas, ocho firmas de repositorio y ejemplos sintéticos | [CONTRATOS.md](docs/pablo/fase0/CONTRATOS.md) |
| Decisiones | ORM solo para identidad; drivers nativos para SQL clínico; roles y sesiones propuestos | [DECISIONES.md](docs/pablo/fase0/DECISIONES.md) |
| Precisiones B | Fecha PostgreSQL, cita opcional y ocurrencia diagnóstica MySQL; archivo concurrente; prefijo q y CAT-01 propuestos | [RESOLUCIONES.md](docs/pablo/fase0/RESOLUCIONES.md) |
| SQL | Scripts experimentales sobre copia de esquemas, con restricciones y rollback | [PRUEBAS_SQL_AISLADAS.md](docs/pablo/fase0/PRUEBAS_SQL_AISLADAS.md) |
| React | Copia exacta de diez fixtures, aislamiento entre consumidores, escenarios vacío/archivo/errores | [Mocks y uso](frontend/src/mocks/README.md) |
| Revisión A | Visto bueno técnico y observaciones contractuales | [REVISION_A_C0.md](frontend/src/mocks/REVISION_A_C0.md) |
| Firestore | Siete documentos DEMO, validación, seed transaccional idempotente y exportación protegida | [Firestore](db/firebase/README.md) |
| MongoDB | Seis colecciones, validadores/índices, nueve documentos DEMO, seed sin sobrescritura | [MongoDB](db/mongo/README.md) |

La interfaz de producción sigue siendo el panel de conectividad. Los mocks no
simulan endpoints disponibles al usuario; los adaptadores actuales solo comprueban
salud. Los modelos DEMO NoSQL no se presentan como implementaciones del puerto clínico.

## Validación ejecutada sobre la integración

No se suman repeticiones del baseline entre merges. Resultados distintos:
**39 pruebas automatizadas aprobadas**, más **13 casos SQL aprobados**, build
React y recuperación Firestore verificados. Ninguna prueba NoSQL quedó omitida.

| Comprobación | Resultado |
|---|---|
| Django después de cada uno de los cinco merges | 12 pruebas OK por ejecución |
| Django check | Sin incidencias |
| React fixtures | 8 pruebas OK; comparación byte a byte con el JSON B |
| Build React | Vite 8.3.2; salida 0 |
| Firestore | 12 pruebas OK, cero omitidas; emulador v1.22.0 |
| Recuperación Firestore adicional | Exportación nativa e importación en otra JVM, puerto interno 8083; verify-only devuelve verified: 7 sin seed en destino |
| MongoDB | 7 pruebas OK, cero omitidas; servidor 7.0.43 aislado |
| Inicializador MongoDB | init.js ejecutado dos veces con mongosh; ambos códigos 0 |
| PostgreSQL | 6 casos OK, servidor 16.15 |
| MySQL | 7 casos OK, servidor 8.4.11 |
| Compose y salud | Configuración válida, servicios activos y cuatro connected: true |
| Git | diff --check sin errores; todas las ramas remotas revisadas contenidas en main |

SQL probó rechazo de fechas desconocidas, fecha independiente de cita, consulta
sin cita, UNIQUE/FK, relaciones cruzadas y rollback. También probó que el mismo
diagnóstico de catálogo en dos consultas conserva ocurrencias independientes:
el ID diagnóstico externo MySQL propuesto es consulta_diagnostico.id.

### Detalles del entorno de verificación

- Windows/PowerShell, Docker Desktop local. El ejecutable Docker no estaba en PATH
  de la sesión: se usó `$env:LOCALAPPDATA\Programs\DockerDesktop\resources\bin\docker.exe`.
- Django se ejecutó en el contenedor backend. React fixtures se ejecutó desde el
  repositorio completo con Node 25.9.0; build en frontend con Node 22.23.3.
- La ejecución inicial de test:contract en el contenedor frontend falló por ENOENT:
  ese contenedor solo monta frontend y no tiene el fixture backend requerido para
  comparar ambas copias. La misma suite desde el checkout completo aprobó las
  ocho pruebas. Esto no se ocultó como prueba aprobada en Docker ni exigió cambiar
  código/Compose. Los comandos reproducibles aparecen abajo.
- Para NoSQL se construyó una imagen temporal usando las dos imágenes locales
  existentes: Firestore como base y /usr/local del backend para Python y sus
  dependencias. Conservó Java y Node; no instaló nuevas dependencias del proyecto.
- Firestore y Mongo se ejecutaron en contenedores temporales con network none,
  sin puertos publicados ni volúmenes del proyecto. El cliente Mongo compartió
  únicamente el namespace de red de esa instancia temporal para acceder por loopback.
- Se reutilizó una copia del JAR Firestore ya descargado por el contenedor de
  desarrollo. Código de pruebas y exportaciones vivieron en el filesystem temporal;
  servidor y Python compartieron ese filesystem para probar exportación nativa.
- SQL usó instancias nuevas, network none y copias íntegras de init.sql. No se
  ejecutó DDL experimental en hospital/pediatrico ni se reaplicaron validadores a
  laboratorio activo. Los servicios existentes siguieron funcionando.
- Se retiraron los contenedores e imagen temporales creados para esta validación,
  verificando nombres/etiquetas, además de la copia local del JAR y dist generado.
  No se eliminaron volúmenes ni datos del proyecto.

### Comandos basales para repetir

Desde la raíz, con Docker disponible en PATH:

```powershell
git status --short
git diff --check
docker compose config -q
docker compose ps -a
docker compose exec -T backend python manage.py check
docker compose exec -T backend python manage.py test apps.historiales --verbosity 2
node --test frontend/tests/contract-fixtures.test.js
docker compose exec -T frontend npm run build
curl.exe -f http://localhost:8000/api/health/
curl.exe -f http://localhost:8000/api/health/databases/
git branch -r --no-merged main
```

La última orden debe quedar sin resultados para las ramas publicadas revisadas.
No significa que sus punteros se movieran a main: sus commits ya están contenidos.
Los nombres de rama se conservaron; no hubo force push ni reemplazo de ramas ajenas.
No se garantiza ausencia de conflictos en cambios futuros: actualizar y validar
la base antes de cada nuevo PR.

Las pruebas SQL se reproducen con los comandos de su documento enlazado. Para
repetir las suites NoSQL, seguir los READMEs respectivos con destinos aislados:

```text
python -m unittest discover -s db/firebase/tests -v
  FIRESTORE_EMULATOR_HOST=127.0.0.1:<puerto-aislado>
  FIRESTORE_RECOVERY_TESTS=1
  FIREBASE_PROJECT_ID=demo-historiales
  GOOGLE_CLOUD_PROJECT=demo-historiales

python -m unittest discover -s db/mongo/tests -v
  MONGO_DEMO_URI=mongodb://127.0.0.1:<puerto-aislado>/laboratorio_demo
```

Son variables del proceso que ejecuta cada suite, no líneas para sustituir .env.
Firestore export requiere mismo filesystem que el servidor y dataset dedicado;
Mongo requiere base DEMO vacía y Node para generar su manifiesto. No apuntar las
pruebas a una instancia de un compañero.

## Qué continúa pendiente

La integración por solicitud de Pablo **no declara F0 cerrado** ni ratifica por
sí sola todos los contratos. Se conserva el trabajo de ambos equipos sin atribuir
aprobaciones adicionales a Jennifer.

1. Registrar ratificación final A↔B de decisiones y contratos: ocurrencia diagnóstica,
   semántica de q, extensión CAT-01 y suministro de catálogo. Actualizar fixtures
   y puerto al SHA aprobado cuando corresponda.
2. Acordar y reservar el PR de infraestructura para replica set Mongo si se mantiene
   el modelo de documentos separados. No está configurado aún en Compose.
3. Completar las once evidencias globales G0 de ambos equipos y asignar las tareas
   siguientes. El estado detallado histórico está en las guías; integración no
   equivale a evidencia de funcionamiento en otra máquina.
4. C1 / Pablo: login, CSRF, sesión/logout, perfil institucional, roles y enrutamiento.
   Decidir y ejecutar de forma planificada el almacén técnico PostgreSQL para
   identidad; hoy Django continúa con SQLite interno. El SQLite sigue versionado,
   aunque ignorado; su retiro del índice requiere la limpieza separada prevista.
5. C2 / Pablo: migraciones incrementales SQL con conciliación histórica, respaldo
   y reversión. init.sql clínico no recibió los DDL de los experimentos.
6. C3/C4 / ambos equipos: ocho métodos de repositorio, relaciones clínicas completas,
   aislamiento, autorización y pruebas reales de concurrencia con archivo.
7. API clínica, integración UI real, especializaciones y evidencia final según el plan.

No se probaron aún esos endpoints o garantías inexistentes. Esta base sí reúne
todo el trabajo publicado hasta la revisión y las comprobaciones registradas arriba.
