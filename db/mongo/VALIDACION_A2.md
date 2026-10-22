# Evidencia A2 — MongoDB

Ejecución en Codex Cloud, 2026-10-21 UTC, base de trabajo main
`a044c76ea9bb4d761110f8dcc67a389a4f9ddce9`. Evidencia correspondiente al commit
que incorpora este documento en feature/jennifer, identificable con
`git log -1 -- db/mongo/VALIDACION_A2.md`.

Herramientas temporales fuera del repositorio: Python 3.12.14, PyMongo 4.19.0,
MongoDB 7.0.28, mongosh 2.13.0, Node 24.19.0. No dependencias nuevas del proyecto.
Servidor nativo dedicado en 127.0.0.1:27029, datos
`/tmp/cell-a-mongo-a2-data`, sin volúmenes Docker ni base compartida. Inicialmente
laboratorio y laboratorio_demo estaban vacías. Las pruebas eliminaron únicamente
sus documentos; las nueve muestras de la comprobación CLI posterior se conservan.

| Verificación ejecutada | Resultado |
|---|---|
| `MONGO_DEMO_URI=mongodb://127.0.0.1:27029/laboratorio_demo python -m unittest discover -s db/mongo/tests -v` | 12 pruebas OK: 5 offline + 7 integración, cero omitidas |
| `PYTHONPATH=backend python -m unittest apps.historiales.test_mongo_nosql -v` | 3 OK: fallback standalone, override replica set, cierre ante error |
| `node --check db/mongo/init.js` y `schema_manifest.js` | OK |
| `python -m py_compile` sobre los cinco archivos Python afectados | OK |
| `python db/mongo/seed_demo.py --validate-only` | Dataset de 9 válido, sin afirmar validación servidor por este comando |
| `mongosh mongodb://127.0.0.1:27029/laboratorio --quiet --file db/mongo/init.js`, dos veces | Ambos código 0; destino dedicado, nunca compartido |
| Manifiesto Node + CLI seed con `--schema`, y repetición sin `--schema` | Primera created=9/unchanged=0; segunda created=0/unchanged=9 |
| `MongoAdapter().health_check()` con MONGO_URI del servidor dedicado | True; conexión real standalone |
| `git diff --check` | OK |

Se reutilizaron las siete pruebas originales y se ampliaron a doce: referencias
huérfanas/catálogos, datos no BSON/no finitos, estados/valores opcionales, colisión
única previa a toda escritura y crecimiento fuera del paciente. El test de índice
usa hint para comprobar que existe y sirve a la consulta paciente/fecha; no afirma
que el optimizador lo elija sin hint ni mide rendimiento.

## Límites y siguiente módulo

No se ejecutó Compose, migración ni transacción clínica. No se certifican los ocho
métodos, permisos, aislamiento institucional, archivo concurrente, rollback o E2E;
pertenecen a A3/B1/B2/B5. El seed standalone puede quedar parcial ante un fallo de
red/carrera: preflight y repetición no equivalen a atomicidad multidocumento.
Datos preexistentes incompatibles requieren inventario antes de aplicar validadores.
No se probaron aquí PostgreSQL/MySQL/Firestore ni interfaz React: no fueron afectados.

Dependencias: B1 publica contexto/errores/puertos y suite; B5 configura replica set
preservando datos. Puede continuar A4 con mocks explícitos del contrato 1.0.0.
Por instrucción de Jennifer esta entrega permanece en feature/jennifer: sin PR nuevo
ni merge a main durante esta actividad.
