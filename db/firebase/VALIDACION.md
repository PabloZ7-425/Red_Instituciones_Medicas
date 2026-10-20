# Evidencia A-C1-T1 / PR-03 del plan

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
| Export/import mediante Firebase CLI | **Pendiente: exportación bloqueada; importación no ejecutada** |

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
No se borró ningún archivo del hub ni dato para resolverlo. Repetir export/import
en Docker local según README; no declarar recuperación validada con esta evidencia.
Este fallo del tooling local no prueba un defecto del repositorio ni un problema
de permisos GitHub. Los contratos, roles, índices clínicos y límites finales siguen
pendientes de revisión A↔B. No se implementó el adaptador clínico.
