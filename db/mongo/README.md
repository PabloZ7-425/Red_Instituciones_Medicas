# Laboratorio: preparación A-C2-T1 / PR-05 del plan

Trabajo independiente, provisional y separado del PR-03 Firestore. Base
`e9b2efafa51ca897765d9055f39be219da5a41bb`. F0 abierto: no implementa puerto clínico,
no cambia autenticación ni `mongo_adapter.py`, no habilita replica set ni toca Compose.

## Cambios de modelo

Se preservan las seis colecciones y sus índices originales. Se tipan identificación,
nombres y fecha BSON del paciente, contacto/tutor opcionales; consultas requieren
paciente ObjectId y fecha BSON; resultados necesitan al menos un campo con nombre y
valor de tipo admitido. Unidad y rango son opcionales. Los detalles definitivos de
diagnóstico, tratamiento y receta esperan `CONTRACT-REPO-01`; el esquema preparatorio
no obliga a inventar DTOs. Datos pequeños de contacto se embeben, consultas y
resultados crecientes se referencian por paciente. ObjectId permanece interno.

Índices: identificación única y apellidos/nombres para pacientes; paciente/fecha
para consultas/resultados; tipo de examen para resultados; nombres para catálogos.
No se presume búsqueda libre equivalente a índices por prefijo. Los seis contenedores
de datos se conservan; no se crea un login alternativo en `usuarios`.

**Compatibilidad:** reforzar un validador puede impedir la actualización de documentos
antiguos incompatibles. `collMod` no los transforma. Inventariar y respaldar antes de
aplicar en un entorno poblado; esta rama no ejecuta migraciones sobre `laboratorio`.
El inicializador ahora aborta si Mongo rechaza `collMod`, en lugar de ignorar `ok: 0`.

## Fixture y seed

`seed_demo.py` produce nueve documentos deterministas: paciente, consulta, medicamento
ficticio, tres tipos de examen y tres resultados heterogéneos (hematología, orina y
química). No crea usuarios ni contraseñas. Resultados son académicos, sin pacientes
reales. Dinámica de transacciones clínicas queda para D0-07.

Solo admite `MONGO_DEMO_URI` local con puerto explícito y base **laboratorio_demo**;
no utiliza `MONGO_URI` del backend ni escribe en `laboratorio`. Las fechas son BSON
UTC y el cliente requiere `tz_aware=True` para comparación estable. El seed revisa
conflictos antes de escribir y usa `$setOnInsert`: no sobrescribe documentos. En
standalone no existe garantía atómica para el conjunto; un fallo de red puede dejar
un subconjunto. Repetir completa lo ausente sin alterar lo existente; un conflicto
se informa y requiere revisión. No se declara atomicidad multidocumento.

## Comandos desde la raíz

Requisitos: Python 3.10+, PyMongo del rango ya declarado en el backend, Node para
exportar el inicializador existente. No agrega dependencias del proyecto.

```bash
node --check db/mongo/init.js
node --check db/mongo/schema_manifest.js
python db/mongo/seed_demo.py --validate-only
python -m unittest discover -s db/mongo/tests -v
node db/mongo/schema_manifest.js > /ruta/temporal/schema-laboratorio.json
```

`--validate-only` solo construye BSON; no equivale a validación de MongoDB. El
manifiesto ejecuta `init.js` dos veces en un sandbox sin conexión y exporta sus
validadores/índices reales. No acredita por sí solo el comportamiento del servidor.

En una instancia MongoDB 7 **aislada**, antes de sembrar (los tests exigen base vacía):

```bash
export MONGO_DEMO_URI=mongodb://127.0.0.1:27017/laboratorio_demo
python -m unittest discover -s db/mongo/tests -v
python db/mongo/seed_demo.py --schema /ruta/temporal/schema-laboratorio.json
python db/mongo/seed_demo.py
```

PowerShell: `$env:MONGO_DEMO_URI='mongodb://127.0.0.1:27017/laboratorio_demo'`.
No ejecutar la suite sobre la instancia de otro compañero. La suite comprueba que
la base no contenga documentos antes de escribir, crea índices/validadores con
PyMongo y limpia solo IDs del fixture escrito; no elimina bases ni colecciones.
La carga de `init.js` en mongosh/Docker conserva su destino original `laboratorio`:
no usarla como comando de prueba de esta demo. Aquí se aplican los mismos esquemas
exportados a la base separada mediante `--schema`.

## Evidencia y pendientes

Codex Cloud, 2026-10-20, Python 3.12.14, Node 24.19.0 y PyMongo 4.19.0:

- 3 pruebas sin servidor **OK**: repetición del inicializador en sandbox, fixture
  determinista con referencias y rechazo de URI remota/credenciales/base incorrecta.
- 4 pruebas de integración **omitidas**, no aprobadas: repetición/lectura e índices,
  rechazo servidor de documentos inválidos, unicidad y preservación ante conflicto.
- Sintaxis JS/Python y `git diff --check`: **OK**.
- No había servidor MongoDB local activo. Un intento de descargar MongoDB 7.0.28 a
  un directorio temporal terminó con `curl: (28) Operation timed out after 60001
  milliseconds`; no se inició ni modificó una instancia existente. Esto es una
  limitación del entorno, no un defecto demostrado del repositorio.

Pendientes de cierre: ejecutar integración en MongoDB 7 aislado, ratificar modelos
y límites D0-06, alinear receta/diagnóstico/tratamiento al contrato y acordar
atomicidad D0-07. La suite prueba esquemas mediante PyMongo; probar además el
entrypoint mongosh cuando se valide Docker local. Sin adaptador clínico definitivo.
