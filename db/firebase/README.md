# A1 — Persistencia documental odontológica

Módulo A1 de Jennifer según PLAN_MAESTRO.md 2.0. Contratos API/REPO **1.0.0**.
Modelo, validación, seed, proyección de DTOs y recuperación independientes del
runtime B1. El adaptador clínico, autorización y concurrencia de archivo pertenecen
al módulo A3; esta entrega no anuncia endpoints o autenticación implementados.

## Dos versiones, sin sobrescribir la anterior

| Versión | Archivos/comando | Documentos |
|---|---|---|
| Histórica | demo.json + seed_demo.py | 7, conservados sin modificación |
| Clínica A1 | clinical_demo.json + seed_clinical_demo.py | 18 clínicos/administrativos + 2 reservas = 20 |
| Coexistencia | Ambos seeds | 27, todos recuperables juntos |

Los IDs nuevos usan DEMO-A1-* y las identificaciones son distintas. El seed nuevo
no migra ni reescribe documentos viejos. Si un destino existe con contenido distinto,
una identificación ya pertenece a otro paciente o su reserva es incompatible,
aborta la transacción completa. Repetir sin diferencias crea cero documentos.
No hay opción force/reset ni borrado de datos. Un conflicto se revisa conservando
los registros, no vaciando la base.

Consultar [MODELO.md](MODELO.md) para campos, referencias, fechas civiles, índices,
límites, reservas de identificación y correspondencia con DTOs. Los datos son
sintéticos: no crean cuentas, credenciales, profesionales reales ni tratamientos
utilizables. El identificador profesional del fixture solo permite verificar vínculos.

## Validar sin servicios

Desde la raíz, Python 3.10+ (biblioteca estándar; tzdata del sistema):

```bash
python db/firebase/seed_demo.py --validate-only
python db/firebase/seed_clinical_demo.py --validate-only
python -m unittest discover -s db/firebase/tests -v
```

Sin emulador, las pruebas de integración aparecen omitidas explícitamente. El seed
nuevo usa fechas civiles para nacimiento/consulta/archivo y timestamps UTC solo
para citas/pagos. No determina fecha de consulta a partir de la cita o medianoche UTC.

## Escribir y leer en emulador

Usar el SDK Firestore incluido por firebase-admin del backend en un entorno Python
local; no hay nuevas dependencias del proyecto. Conservar versiones en pip freeze
local si se requiere reproducir exactamente una ejecución. Para host Docker el
puerto existente es 8082; dentro de Compose es firestore:8080. No modificar Compose.

```bash
export FIRESTORE_EMULATOR_HOST=127.0.0.1:8082
export FIREBASE_PROJECT_ID=demo-historiales
python db/firebase/seed_clinical_demo.py
python db/firebase/seed_clinical_demo.py
python db/firebase/export_demo.py --dataset clinical --verify-only
```

Resultados sobre instancia vacía: created=20 y después unchanged=20; verificación
verified=20. Si ya existe el dataset histórico completo, usar --dataset both para
verificar 27. PowerShell usa `$env:FIRESTORE_EMULATOR_HOST='127.0.0.1:8082'` y
`$env:FIREBASE_PROJECT_ID='demo-historiales'`. Los destinos permitidos son loopback
(o servicio firestore para seed), con puerto y proyecto demo explícitos; no hay
fallback a Google Cloud ni credenciales de producción.

## Suite completa

Solo emulador **dedicado, vacío y aislado**, misma máquina/filesystem que Python:

```bash
export FIRESTORE_RECOVERY_TESTS=1
firebase emulators:exec --only firestore --project demo-historiales   'python -m unittest discover -s /ruta/repo/db/firebase/tests -v'
```

Ejecutar desde configuración temporal copiada de db/firebase/firebase.json e índices;
para aislamiento ajustar únicamente esa copia a host 127.0.0.1 y puertos libres,
con UI desactivada. En Windows puede ejecutarse sin el salto de línea del ejemplo.
No iniciar backend ni migraciones para probar A1. Las pruebas limpian solo los
IDs que crean; no borran colecciones ni volúmenes. Las pruebas de coexistencia y
exportación requieren instancia vacía; las demás usan IDs únicos por ejecución.

La validación del script no es un esquema impuesto por el servidor Firestore;
un cliente que omita el script puede escribir datos distintos. B2/B5 controlarán
acceso a API y A3 validará cada operación del repositorio. Las reglas abiertas del
emulador no acreditan seguridad productiva.

## Exportar y recuperar sin hub

Solo emulador nativo dedicado en el mismo filesystem, sin escritores concurrentes.
La comprobación previa no bloquea a otros clientes. No usar export_demo.py contra
un puerto Docker que no comparta filesystem con Python. No sobrescribir exports:
el destino debe ser nuevo y estar fuera del repositorio.

```bash
python db/firebase/export_demo.py --dataset both --output /ruta/local/nueva/export-a1
# Detener solo la instancia dedicada; iniciar otra que importe la exportación:
firebase emulators:exec --only firestore --project demo-historiales   --import /ruta/local/nueva/export-a1/firestore_export   'python /ruta/repo/db/firebase/export_demo.py --dataset both --verify-only'
```

Se usa la API local de exportación del emulador, también empleada por la CLI.
La verificación compara todos los campos/relaciones, fechas y reservas; no ejecuta
seed ni reconstruye datos faltantes. --dataset legacy conserva el comportamiento
anterior (7); clinical exige exactamente 20; both exige los 27. Documentos o
subcolecciones adicionales causan rechazo, nunca borrado o exportación silenciosa.

El flujo CLI habitual sigue disponible en Docker local mediante
`firebase emulators:export <destino> --project demo-historiales`, con hub y ruta
persistente coordinados con Pablo. La persistencia automática de Compose no se
presupone y pertenece a su configuración central.

## Evidencia y continuidad

Resultados nuevos y comandos están en [VALIDACION.md](VALIDACION.md). Los registros
PR-03.md y primeras secciones de validación describen el método anterior; F0 y
aprobación cruzada dejaron de ser requisitos con el plan 2.0.

A1 deja almacenamiento/modelo reproducibles. A3 implementará las ocho operaciones y
catálogo con contexto validado, errores de dominio, lectura transaccional de raíz y
carreras de archivo. Es una dependencia técnica de runtime B1, no una aprobación
pendiente para este módulo. No se modifican archivos de Pablo ni firestore_adapter.py.
