# Laboratorio — módulo A2 MongoDB

Modelo, validadores, índices y DEMO de laboratorio. Reutiliza las seis colecciones
y los nueve documentos originales, sin cambiar sus IDs ni su contenido. Sigue el
plan operativo 2.0 y CONTRACT-API-01 / CONTRACT-REPO-01 **1.0.0**; los anteriores
ciclos y gate F0 ya no condicionan este módulo. No implementa todavía A3 clínico.

## Modelo y límites

Ver [MODELO.md](MODELO.md) para relaciones, consultas, crecimiento y mapeo pendiente
al contrato público. `init.js` crea o actualiza validadores sin borrar documentos.
Identificación única, nombres no vacíos (máximo 100) e identificación de hasta 20;
catálogos con nombre no vacío; presentación del medicamento opcional o null.
Pacientes admiten activo/inactivo/archivado. Resultados exigen campos con nombre y
valor escalar BSON; unidad/rango son opcionales. `validate_demo.py` comprueba además
referencias, claves repetidas, fechas conscientes UTC, campos repetidos y números
finitos antes de escribir el fixture.

**Compatibilidad:** `collMod` no transforma documentos antiguos. Validadores más
estrictos pueden impedir actualizaciones de registros incompatibles. Antes de
aplicarlos sobre datos existentes, inventariar/resguardar y resolver incompatibles;
no se ejecutó ninguna migración sobre la base compartida. Un volumen ya iniciado
no vuelve a ejecutar automáticamente el entrypoint de Mongo al reiniciar Compose.

## Seed seguro y reproducible

`seed_demo.py` conserva paciente, consulta, medicamento ficticio, tres tipos de
examen y tres resultados heterogéneos (hematología, orina y química). Sin usuarios,
contraseñas ni pacientes reales. Solo admite `MONGO_DEMO_URI` local, sin credenciales,
con puerto explícito y base **laboratorio_demo**; nunca usa `MONGO_URI` del backend.

Revisa el dataset completo, los documentos existentes y las claves únicas antes de
escribir. Usa `$setOnInsert` y comprueba la lectura posterior: no sobrescribe
contenido distinto. En standalone **no hay atomicidad multidocumento**. Un fallo
de red o una colisión concurrente pueden dejar un subconjunto; repetir completa lo
ausente y los conflictos requieren revisión. El preflight no bloquea otros clientes.
Esto no demuestra archivo clínico, rollback ni autorización: corresponden a A3.

## Ejecución desde la raíz

Requisitos existentes: Python 3.10+, PyMongo del backend, Node y MongoDB 7 aislado.
`mongosh` es necesario solo para comprobar directamente el entrypoint JS.

```bash
node --check db/mongo/init.js
node --check db/mongo/schema_manifest.js
python db/mongo/seed_demo.py --validate-only
python -m unittest discover -s db/mongo/tests -v
PYTHONPATH=backend python -m unittest apps.historiales.test_mongo_nosql -v
node db/mongo/schema_manifest.js > /ruta/temporal/schema-laboratorio.json
```

Sin servidor se ejecutan cinco pruebas offline y se omiten explícitamente siete
de integración. `--validate-only` valida el dataset/BSON, no el servidor. El
manifiesto ejecuta el inicializador dos veces en sandbox y exporta su esquema real.

En una instancia **aislada y vacía**, ejecutar primero los tests y después el seed:

```bash
export MONGO_DEMO_URI=mongodb://127.0.0.1:27017/laboratorio_demo
python -m unittest discover -s db/mongo/tests -v
python db/mongo/seed_demo.py --schema /ruta/temporal/schema-laboratorio.json
python db/mongo/seed_demo.py
```

PowerShell:

```powershell
$env:MONGO_DEMO_URI='mongodb://127.0.0.1:27017/laboratorio_demo'
python -m unittest discover -s db/mongo/tests -v
$env:PYTHONPATH='backend'
python -m unittest apps.historiales.test_mongo_nosql -v
Remove-Item Env:PYTHONPATH
```

No ejecutar sobre la instancia de otro compañero. La suite exige base vacía,
aplica índices/validadores y limpia únicamente IDs que ella creó. No elimina bases
ni colecciones. `init.js` conserva su destino `laboratorio`: usar mongosh para
probarlo solamente en una instancia dedicada, nunca sobre volúmenes compartidos.
Para generar el JSON en PowerShell usar UTF-8 (en Windows PowerShell 5.1,
`node db/mongo/schema_manifest.js | Set-Content -Encoding UTF8 schema.json`).

## Conexión y continuación

El fallback del adaptador coincide con el Compose actual:
`mongodb://mongo:27017/laboratorio`. Una `MONGO_URI` explícita mantiene todas sus
opciones, incluido un futuro `replicaSet=rs0`; la prueba no conecta al servidor.
No se modificó Compose. Para transacciones clínicas A3, Pablo/B5 debe preparar el
replica set preservando datos, y B1 entregar puertos/contexto/errores/suite reales.

Evidencia de esta entrega: [VALIDACION_A2.md](VALIDACION_A2.md). Por instrucción
expresa, los cambios se conservan en `feature/jennifer`, sin integrar a main.
