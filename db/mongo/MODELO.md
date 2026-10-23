# Modelo documental de laboratorio — A2

Persistencia actual, comprobada con MongoDB 7. El modelo legado DEMO no es un DTO
del contrato público 1.0.0; A3 hará su traducción y operaciones clínicas.

| Colección | Datos y relación | Decisión e índice |
|---|---|---|
| pacientes | Identificación, nombres, nacimiento BSON, estado; contacto/tutor pequeños | Embebidos porque se leen con el paciente. Identificación única; apellidos/nombres para recorrido ordenado existente |
| consultas | paciente_id ObjectId, fecha BSON, arrays diagnósticos/recetas legados | Referencia al paciente: las consultas crecen durante la vida del paciente. Índice paciente_id/fecha descendente para consulta cronológica |
| resultados_examen | paciente_id ObjectId, tipo_examen por nombre de catálogo, timestamp BSON, estado, campos | Documento por resultado; índice paciente/fecha y por tipo_examen. No acumular todos los resultados dentro del paciente |
| tipos_examen | Nombre único del examen | Catálogo referenciado por nombre en el legado; no renombrar sin conciliación de referencias |
| medicamentos | Nombre; presentación opcional/null | Catálogo independiente reutilizable; índice nombre. Sin estado persistido, el catálogo se considera habilitado según CAT-01 |
| usuarios | Colección histórica con su validador/índice originales | No sembrar usuarios ni usarla como autenticación paralela a Django |

`campos` se embebe en cada resultado: pertenece a ese examen y permite combinar
números, texto y booleanos sin columnas SQL artificiales. Los tres ejemplos son
hemoglobina numérica, color/proteínas texto/booleano y glucosa entera. No se infiere
diagnóstico ni se validan rangos médicos; las unidades/rangos son etiquetas DEMO.
El validador del servidor limita tipos estructurales; el preflight del seed también
rechaza NaN/infinito, referencias huérfanas y nombres de campos duplicados. Mongo
no impone claves foráneas entre colecciones. Escrituras ajenas al seed no heredan
automáticamente esas comprobaciones semánticas.

No hay límite aplicativo de cantidad de resultados por paciente. Cada documento
está sujeto al límite BSON de 16 MiB. Arrays de diagnósticos/recetas existentes son
legados, no una garantía de crecimiento acotado: A3 debe usar ocurrencias con ID
propio y relaciones diagnóstico→tratamiento→receta, sin reutilizar CIE-10 como ID.
El ensayo de 30 resultados adicionales acredita que el documento paciente no
crece; no es un benchmark de carga ni certificación de escalabilidad ilimitada.

## Compatibilidad pública y trabajo A3

- `_id`/`paciente_id` BSON son internos. A3 generará IDs públicos opacos string y
  mantendrá su resolución; nunca devolver objetos BSON ni referencias del driver.
  El seed existente no pretende que un ObjectId sea el identificador contractual.
- Nacimiento del fixture es BSON a medianoche UTC usado como **fecha civil legacy**:
  para ese dato concreto se conserva su componente YYYY-MM-DD, sin desplazarlo a
  Guatemala (lo que daría el día anterior). No generalizar a datos históricos no
  inventariados. Nuevas fechas civiles se validarán según contrato, sin timestamps
  del navegador; instantes técnicos seguirán UTC con salida ISO Z.
- La consulta legacy tiene un instante (2026-10-20T15:00:00Z). Su fecha clínica en
  America/Guatemala es 2026-10-20. A3 debe distinguir ese instante de una fecha civil
  nueva; no reinterpretar todo BSON date como medianoche UTC.
- `motivo_baja/fecha_baja` son campos históricos, no los nombres públicos
  `motivo_archivo/fecha_archivo`. No se migran ni se asignan motivos ficticios.
  Activo/inactivo/archivado se preservan; autorización y exclusión de escrituras
  tras archivo no están implementadas por un simple validador de estado.
- Opcionales públicos se proyectarán como null y arrays vacíos como [], según
  contrato; presentación ausente se proyectará null en CAT-01. No exponer
  seed_version ni contraseña/hash de la colección histórica de usuarios.
- Los índices actuales no implementan por sí solos búsqueda contractual prefijo
  trim+NFC+lower ni orden/paginación públicos. A3 debe verificar esa equivalencia;
  no se promete búsqueda por regex/subcadena ni se agregan endpoints.

## Consistencia y propietarios

Seed: preflight completo, inserción solo si ausente, lectura posterior y rechazo
de conflictos; sin atomicidad de conjunto en standalone. Una colisión de catálogo
preexistente se detecta antes de crear el paciente. Carrera o fallo de red siguen
pudiendo dejar un subconjunto recuperable por repetición, sin sobrescribir.

A3: transacciones multidocumento y modificación condicional de versión del paciente
raíz en cada escritura/archivo; lectura snapshot sola no resuelve la carrera. B5
es dueño del replica set/Compose y B1 del runtime contractual y su suite. La salud
standalone probada aquí no demuestra transacciones. Continúa A4 con mocks explícitos
mientras se entregan esas capacidades; no se detiene la implementación independiente.
