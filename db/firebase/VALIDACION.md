# Evidencia Firestore — historial y módulo A1

> Las secciones iniciales conservan evidencia anterior al plan 2.0. F0 y la
> ratificación cruzada mencionados allí ya no son requisitos vigentes. La
> continuación A1 al final registra el módulo actual y sus comprobaciones.

Base: `e9b2efafa51ca897765d9055f39be219da5a41bb`. Gate F0 abierto.
Validación realizada en Codex Cloud el 2026-10-20. Dependencias instaladas en
`/tmp`, sin cambiar requisitos del backend ni la configuración del repositorio.

| Comprobación | Resultado |
|---|---|
| `python db/firebase/seed_demo.py --validate-only` | OK, siete documentos |
| `python -m unittest discover -s db/firebase/tests -v` sin destino | 4 tests OK, 3 integración omitidos explícitamente |
| Misma suite con emulador Firestore real aislado | **7 tests OK, 0 omitidos** |
| Escritura y lectura de todos los documentos | OK, valores y relaciones esperados |
| Segunda ejecución idéntica | OK, 0 creados y 7 sin cambios |
| Dataset inválido | OK, rechazado sin escrituras |
| Conflicto con documento existente al final del dataset | OK, documento preservado y ninguna escritura parcial |
| Seed CLI sobre emulador vacío | `{"created": 7, "unchanged": 0}` |
| Seed CLI repetido | `{"created": 0, "unchanged": 7}` |
| Sintaxis Python/JSON y `git diff --check` | OK |
| Export/import mediante Firebase CLI (intento inicial) | Exportación vía hub bloqueada; resuelto después por la alternativa local descrita abajo |

Herramientas de la ejecución: Python 3.12.14, Java 21.0.12.1, Node 24.19.0,
Firebase CLI 15.34.0, Firestore Emulator 1.22.0, firebase-admin 7.7.0,
google-cloud-firestore 2.34.1. No se necesitó arrancar Docker, Django ni migraciones.
Se copió configuración a un directorio temporal; emulador escuchó solo loopback.
El emulador conserva la política abierta de desarrollo de la configuración actual;
estas pruebas no acreditan seguridad de producción ni autorización clínica.

Invocación usada (rutas de herramientas temporales dependen de cada equipo):

```bash
firebase emulators:exec --only firestore --project demo-historiales \
  'python -m unittest discover -s /ruta/repo/db/firebase/tests -v'
```

Para exportación se ejecutó `firebase emulators:export` contra el mismo proyecto,
con el emulador activo y destino fuera del repositorio. Error exacto:

```text
Error: The emulator hub for demo-historiales did not respond to a status check. If this error continues try shutting down all running emulators and deleting the file /tmp/hub-demo-historiales.json
```

La CLI terminó con código 1; su consulta local fue cancelada sin respuesta HTTP.
No se borró ningún archivo del hub ni dato para resolverlo. El flujo CLI vía hub
en Docker local continúa pendiente; no confundirlo con la recuperación nativa comprobada abajo.
Este fallo del tooling local no prueba un defecto del repositorio ni un problema
de permisos GitHub. Los contratos, roles, índices clínicos y límites finales siguen
pendientes de revisión A↔B. No se implementó el adaptador clínico.

## Continuación: recuperación nativa comprobada

Se añadió `export_demo.py`, biblioteca estándar HTTP + SDK Firestore existente.
Usa el endpoint del emulador que también utiliza Firebase CLI y evita la consulta
al hub que falla en este entorno. No modifica el emulador, proxy ni autenticación.
Solo emulador loopback en el mismo filesystem, proyecto demo y dataset exacto.

- Suite ampliada con `FIRESTORE_RECOVERY_TESTS=1`: **12 pruebas OK, 0 omitidas**.
- Se verifican rechazo de destino existente/dentro del repo, hostname Docker,
  documentos adicionales y subcolecciones. Se preservan los datos rechazados.
- Emulador vacío: seed creó siete documentos; `export_demo.py --output` generó
  exportación nativa en `/tmp/cell-a-firestore-recovery-export/firestore_export`.
- El primer emulador se detuvo normalmente. Otra instancia arrancó con
  `firebase emulators:exec --import` sobre esa carpeta.
- En la instancia importada **solo** se ejecutó `export_demo.py --verify-only`:
  `{"verified": 7}`, código 0. Compara campos, relaciones y timestamps con el
  fixture original; no escribe ni ejecuta seed para recrear datos faltantes.
- Versiones de herramientas iguales a la ejecución inicial. Sin cambios de
  Compose, puertos activos de la aplicación o archivos de Pablo.

La recuperación del dataset nativo queda validada. Pendientes distintos: integración
de exportaciones en Docker local, decisiones contractuales y Gate F0 compartido.

## A1 — modelo documental conforme a API/REPO 1.0.0

Base `2eb7470b8d3dffef1162953ab1e44cb67dadfa18`, rama permanente feature/jennifer.
El plan 2.0 define los contratos; no se espera aprobación de otra célula.

### Resultados nuevos ejecutados

| Comprobación | Resultado |
|---|---|
| `python db/firebase/seed_clinical_demo.py --validate-only` | 20 documentos: 18 de fixture y 2 reservas |
| Suite completa con emulador y FIRESTORE_RECOVERY_TESTS=1 | **26 pruebas OK, 0 omitidas**, incluye las 12 anteriores |
| Campos DTO y cadena clínica | Coinciden con formas del contrato, incluidos null y un medicamento por receta |
| Dos ocurrencias con mismo CIE-10 | IDs, consultas, tratamientos y recetas independientes |
| Fecha civil vs instante UTC | Consulta 2026-10-19 conservada; cita 2026-10-20T02:30Z es día 19 Guatemala |
| Datos inválidos y relaciones cruzadas | Rechazados sin escrituras |
| Paciente previo sin reserva con misma identificación | Conflicto, contenido previo preservado |
| Conflicto en la última reserva | Transacción abortada, sin documentos parciales |
| Lectura almacenada y repetición | 20 documentos correctos, segunda ejecución 0 creados / 20 intactos |
| Coexistencia v1 + v2 | 27 documentos completos, v1 intacto |
| Recuperación en otra JVM | Exportar ambos, detener origen, importar; `--dataset both --verify-only` devuelve **verified: 27**, sin seed en destino |
| Normalización para búsqueda | NFC/lower sin perder nombre original ni eliminar acentos |
| Configuración nativa e índices | Copia del firebase.json e índices usada por el emulador; consulta por institución/versión/paciente/fecha aprobada |
| Sintaxis Python/JSON, rutas COPY y diff | Correctos; Docker build no ejecutado |

La configuración temporal copia la del repositorio y cambia solo host a loopback,
puerto aislado y UI desactivada. Herramientas: Python 3.12.14, Java 21.0.12.1,
Firebase CLI 15.34.0, emulador 1.22.0 y google-cloud-firestore 2.34.1. No se
añadieron dependencias ni se modificaron archivos B, Compose o el adaptador clínico.

### Reproducción de la ejecución

```bash
FIRESTORE_RECOVERY_TESTS=1 PYTHONDONTWRITEBYTECODE=1 firebase emulators:exec \
  --only firestore --project demo-historiales \
  'python -m unittest discover -s /ruta/repo/db/firebase/tests -v'
```

Con instancia dedicada vacía, seed histórico → 7 creados; seed clínico → 20 creados;
seed clínico repetido → 0 creados / 20 intactos. Exportación nativa con
`export_demo.py --dataset both --output /tmp/cell-a-firestore-a1-export`.
Tras detener esa instancia, otra arrancó con `--import` apuntando a su subdirectorio
firestore_export. Allí solo se ejecutó `export_demo.py --dataset both --verify-only`.

Los 26 tests validan A1, no autorización ni los métodos de A3. No se ha certificado
seguridad de producción, índices obligatorios de Firebase real, API clínica o
carreras entre archivo y escritura. El entorno Docker compartido no se arrancó
ni recibió seeds/migraciones. Los datos/exportaciones temporales se preservaron.
