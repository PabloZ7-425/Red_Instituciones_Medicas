# B1 — Contratos y núcleo clínico

Responsable: Pablo. Rama: `feature/pablo`. Fecha: 2026-10-21.
Base de implementación: `d2901ae` (main sincronizado, sin cambios locales previos).
Norma: PLAN_MAESTRO §§5–6, CONTRACT-API-01 y CONTRACT-REPO-01 **1.0.0**.

## Entrega y límites

Se materializan los ocho métodos de `HistorialRepository`, el puerto separado
`MedicamentoCatalogo`, DTOs JSON tipados, contexto inmutable, seis errores de dominio,
validación y casos de uso sin imports de Django/drivers. Las fechas son civiles,
la búsqueda usa trim/NFC/lower y prefijo literal; no se transforma un ID opaco.
`HistorialService` autoriza antes de acceder al repositorio. El repositorio debe
comprobar relaciones, estado y unicidad dentro de su propia transacción.

`AdapterFactory.create(Institution)` conserva los cuatro registros de salud.
Las importaciones de drivers son diferidas. `create_clinical(contexto)` exige
ambos puertos y construye `Adapter(contexto=contexto)`; un adaptador de solo salud
produce `PersistenciaNoDisponible`, sin usar el doble de pruebas como sustituto.
Los cuatro adaptadores actuales siguen siendo de salud: su implementación clínica
corresponde a A3/B3/B4. No se cambiaron fuentes de Jennifer.

`ContextoClinico(institucion, usuario_id, rol, profesional_id=None)` se construye
exclusivamente desde una identidad comprobada. B2 debe verificar sesión activa,
perfil y profesional habilitado; este objeto valida su forma y permisos, no consulta
cuentas. El vínculo profesional se exige incluso a admin para escribir atención,
diagnóstico, tratamiento y receta. Laboratorista se limita a laboratorio.

`presentation/errors.py:error_response` devuelve `(status, envelope)` seguro; las
excepciones inesperadas se traducen a INTERNAL_ERROR sin su texto. B5 conectará este
traductor a DRF, con registro seguro. No se agregaron endpoints ni éxitos ficticios.
Los adaptadores deben traducir sus errores de driver a errores de dominio.

## Uso por proveedores

```python
contexto = ContextoClinico("hospital", usuario_id, "medico", profesional_id)
repo = AdapterFactory.create_clinical(contexto)
service = HistorialService(contexto, repo, repo)
page = service.listar_pacientes(q="Paciente", limit=20, offset=0)
```

Ese ejemplo requiere un adaptador clínico real implementado; hoy falla de forma
explícita. No recibir `contexto` desde JSON clínico. Cada implementación hereda
`HistorialRepository` y `MedicamentoCatalogo`, recibe `contexto=` y mantiene
`health_check` utilizable sin contexto. No ejecutar operaciones clínicas sin contexto.

`validar_dto` rechaza objetos incompletos, null, tipos incorrectos, campos desconocidos,
identidad/motor enviados por el cliente, fechas inválidas/futuras y límites de texto.
`validar_query` recibe pares preservando repeticiones; B5 no debe convertir primero
QueryDict a dict. `validar_paginacion` trabaja con enteros ya parseados y rechaza bool.
Archivo HTTP valida `validar_dto("archivo", body)` antes de pasar motivo al servicio.
Login/password/CSRF y cookies se implementan en B2, sin aplicar trim al password.

## Suite reutilizable

`testing/repository_contract.py:RepositoryContract` es un mixin unittest. Uso:

```python
class HospitalContractTests(RepositoryContract, TestCase):
    institutions = ("hospital", "pediatrico")

    def make_harness(self):
        return IsolatedSQLHarness()  # implementación del proveedor B3/B4
```

El harness debe proporcionar:

| Método | Obligación |
|---|---|
| `repo(contexto)` | Cliente independiente, limitado a esa institución; implementa los dos puertos |
| `close()` | Limpieza solo del destino/fixtures aislados creados por el harness |
| `inactive(repo, paciente_id)` | Preparar fixture de estado heredado inactivo |
| `fail_next(repo)` | Inyectar fallo después de una mutación y antes del commit; para receta entre sus partes persistidas |
| `gate_next(repo, entered, release)` | En la siguiente transacción, después de bloquear/validar raíz y antes de mutar, señalar entered y esperar release con timeout |

El destino debe ser nuevo/aislado y explícito, con catálogo sintético habilitado no
vacío. El segundo contexto requiere un espacio institucional aislado distinto:
el proveedor prepara ambos destinos; no usar instituciones/bases activas. Cada llamada
a `repo` debe devolver una conexión/cliente independiente. Los hooks viven en el
harness de pruebas, no en endpoints productivos. No omitir casos de transacciones
para anunciar cierre real de un proveedor.

La suite cubre cadena clínica, DTOs JSON, duplicados institucionales, prefijo literal
incluyendo `%/_`, NFC/acentos, count/paginación/orden, padres ajenos/ausentes,
referencias inexistentes, ocurrencias diagnósticas independientes, archivo idempotente,
historia preservada, estado inactivo, rollback en cada escritura y ambas carreras.
La sincronización usa eventos entre dos clientes; no sleeps. Un proveedor real debe
añadir casos de sus modelos: cita consumida/otro paciente/profesional, medicamentos
ajenos/deshabilitados, detalles MySQL y recuperación persistente, entre otros.

`testing/memory.py` es un doble explícito de pruebas, con lock y snapshots para
ejercitar la suite. Nunca se registra en la factory productiva. Pasar esta suite con
el doble acredita el núcleo y el arnés, **no** atomicidad, aislamiento ni persistencia
de PostgreSQL, MySQL, MongoDB o Firestore. La fecha de archivo del doble es sintética.

## Fixtures y compatibilidad con A

`backend/apps/historiales/fixtures/contrato_v1_runtime.json` publica versión vigente
1.0.0: diez pares originales sin cambio de formas y extensiones AUTH-CSRF,
AUTH-LOGOUT y CAT-01. Son ejemplos sintéticos, no respuestas HTTP comprobadas.

El anterior `contrato_v1.json` se conserva como fixture histórico de compatibilidad:
la suite de A exige identidad byte por byte con su copia y metadatos candidatos.
Cambiarlo unilateralmente rompería al consumidor. A4 puede migrar al nuevo fixture
normativo en sus propios archivos; el estado candidato del archivo antiguo no vuelve
a imponer gates ni modifica el plan vigente. Los DTOs clínicos de los diez ejemplos
son idénticos y se comprueba esa compatibilidad automáticamente.

## Verificación de esta entrega

Entorno: Windows/PowerShell, Python 3.12 de MSYS2 y Node disponibles. Sin Django,
pip ni Docker disponibles en PATH; Docker tampoco se encontró en la ruta habitual.
No se instalaron dependencias globales ni se tocaron datos/volúmenes/SQLite/credenciales.

Comandos ejecutados y resultados se registran en el PR junto al SHA del commit.
Para repetir las pruebas del núcleo desde `backend`:

```powershell
python -m unittest apps.historiales.test_clinical_core apps.historiales.test_repository_contract -v
```

Desde raíz:

```powershell
node --test frontend/tests/contract-fixtures.test.js
git diff --check
```

Pendientes de entorno: Django `manage.py check` y suite histórica completa, Compose,
build Vite y endpoints de salud en servicios activos. Pendientes de otros módulos:
suite contra motores reales, sesión/CSRF y API clínica. No se presentan como aprobados.
La capacidad replica set Mongo queda para infraestructura/B5 con inventario y respaldo;
no es prerrequisito para probar el núcleo B1.

### Verificación posterior antes de B2

Se localizó Docker Desktop en instalación por usuario y se completó la verificación
en el mismo código `cd4c3b1`. Se respaldó SQLite fuera del repositorio antes de iniciar
servicios: inventario de `auth_user` = **0** usuarios. No se eliminaron volúmenes.

- `python manage.py check`: sin incidencias, tanto entorno temporal como imagen Docker.
- `python manage.py test apps.historiales`: **45 pruebas aprobadas**, local y Docker.
- `docker compose config -q`: salida 0.
- `docker compose run --rm --no-deps frontend npm run build`: Vite correcto, salida 0.
- `/api/health/`: HTTP 200; `/api/health/databases/`: HTTP 200 y cuatro connected=true.

La CLI utilizada está en `%LOCALAPPDATA%/Programs/DockerDesktop/resources/bin/docker.exe`.
Para backend se usó `compose run --rm --no-deps backend` con los comandos indicados.
El artefacto `frontend/dist` generado se movió a Temp, sin modificar fuentes A.
Esto completa las comprobaciones de compatibilidad pendientes de B1; las pruebas
clínicas contra motores reales siguen perteneciendo a A3/B3/B4.
