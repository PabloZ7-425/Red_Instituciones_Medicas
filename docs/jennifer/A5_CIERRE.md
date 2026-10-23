# A5 cerrado — calidad, recuperación y evidencia académica A

Jennifer, 22 de octubre de 2026, America/Guatemala. **A5 de la célula A cerrado en
feature/jennifer.** A1–A4 ya estaban terminados; esta entrega completa la evidencia
NoSQL especializada, el análisis/trazabilidad y el procedimiento de integración.
No declara un merge, despliegue compartido ni aprobación académica externa.

## Criterios y evidencia

| Criterio A5 del plan | Evidencia y resultado |
|---|---|
| Integración/E2E | A4 `ababb13`: cuatro recorridos HTTP completos y tres por rol, build de producción; ocho pruebas HTTP/nativas comunes y seis especializadas. |
| Seguridad de cliente | A4: 55 pruebas cliente y recorridos por rol; sesión/CSRF, doble envío, errores, ausencia de fallback, privacidad de tutores y cancelación al logout. |
| Consistencia NoSQL | A3: 49 pruebas reales; A4: rollback del hijo/versión raíz, archivo y referencias especializadas, carreras y orden de instantes. |
| Recuperación clínica completa A3/A4 | **10 pruebas ampliadas aprobadas de nuevo, 0 omitidas**, con origen apagado, destino nuevo sin seed, igualdad y continuidad. |
| Evidencia académica | ENTREGA_FINAL_A5.md consolida operaciones, arquitectura, modelos, comparación de cuatro motores, clasificación y REQ-01..13 con límites. |
| Reproducción y paso a integración | Runner frío, scripts A5, inventario de entorno/GitHub y PASO_A_ENTORNO_COMUN.md; propuesta de PR preparada sin publicarla. |

No se suman resultados históricos como si todos se hubieran ejecutado ahora.
El código de aplicación permanece en `ababb13`: esta entrega cambia solo pruebas,
runner y documentación propia. Por ello no repite las siete navegaciones ni toda
la suite del cliente sin cambios que lo justifiquen. Los números A4 anteriores
remiten a sus SHAs/comandos en [A4_CIERRE_REAL.md](A4_CIERRE_REAL.md).

## Recuperación ampliada ejecutada en esta entrega

Se generaron dos historias por motor mediante repositorios reales, una activa y
otra archivada, con consulta/diagnóstico/tratamiento/receta y especialización antes
del archivo. Mongo incluye catálogo de examen y resultado con número, texto y
booleano; Firestore incluye procedimiento con referencias a su tratamiento y
consulta. Se conservaron además los documentos heredados tipados de la prueba.

| Motor | Estado del origen respaldado | Destino y prueba |
|---|---|---|
| MongoDB 7 | 11 colecciones, 17 documentos | Otro servidor/replica set y nueva base *_recovery_uuid; BSON, validadores e índices, también examen único y resultados, conservados |
| Firestore Emulator | 9 colecciones, 16 documentos | Origen detenido y nueva JVM con import nativo del mismo proyecto; igualdad de documentos/tipos y procedimientos |

Después de restaurar, nuevas conexiones leyeron historia **y especialización**
iguales al origen. Se mantuvieron catálogo de examen, identidad duplicada 409,
archivo idempotente y rechazo 409 de consulta/especialización del paciente
archivado con sus propias referencias. El paciente activo admitió nueva consulta
y nuevo resultado/procedimiento, sin resembrar el destino. Se verifican continuidad
y relaciones, no solo cantidades. Permanecen las pruebas de corrupción, permisos
privados, destino poblado, proyecto inválido y subcolecciones no admitidas.

El runner `a5/run_recovery.py` comprueba daemon local, nombres y cuatro puertos
libres antes de crear recursos. Rechaza carpeta Git o existente, y conserva el
servicio que ocupa un puerto. Se ensayaron esas tres negativas sin crear servicios.
Usa únicamente IDs de contenedores recién creados; valida etiqueta y montajes
anónimos antes de retirarlos. El origen Java se valida antes de preparar datos.
Los tests detienen sus orígenes y el runner retira servicios/volúmenes propios.

Reproducción con Python/SDK del backend, Docker, Java/JAR oficial y herramientas
Mongo oficiales locales, en un destino nuevo fuera del checkout:

```bash
python docs/jennifer/a5/run_recovery.py --run \
  --work /workspace/work/a5-cold-nuevo \
  --jar /ruta/cloud-firestore-emulator-v1.22.0.jar \
  --mongodump /ruta/mongodump --mongorestore /ruta/mongorestore
```

El runner termina con el código real de unittest y conserva tests.log/report.json
en la carpeta privada: SHA base y hash del archivo de prueba permiten identificar
la fuente ejecutada incluso antes del commit. El commit de esta entrega se ubica
con `git log -1 -- docs/jennifer/A5_CIERRE.md`. Los artefactos de backup de los tests
son temporales y no se versionan. Mongo Database Tools 100.19.1; mismo JAR/SDK y
drivers que la evidencia A4. No hay datos de pacientes reales.

## Qué queda fuera del cierre A5

- Preparar/validar el entorno compartido, porque no hay un stack común activo
  identificado en esta máquina. El procedimiento y las 18 comprobaciones están
  listos, pero no se etiqueta como probado un equipo al que no se accedió.
- Decisión de PR/merge a main y revisión de la punta/reglas vigentes en ese momento.
  No hay CI aprobado que atribuir: la consulta observó statuses/workflows vacíos.
- Observaciones docentes/diagramas externos de Entrega I no aportados y conciliación
  de históricos que pudieran aparecer fuera del esquema. Se documentan como
  límites de la entrega global, no como trabajo técnico A5 oculto pendiente.
- Producción Firebase, endurecimiento de motores, HA, cifrado y recuperación SQL/
  identidad, que no se certifican con esta suite NoSQL de alcance académico.

El comparativo de Pablo permanece como antecedente de su entrega B5. La versión
consolidada propia utiliza sus fuentes SQL y evidencia posterior A, sin afirmar
que Pablo haya aprobado o ejecutado lo que se realizó aquí.

Documentos finales: [entrega técnica](ENTREGA_FINAL_A5.md),
[comparativo/clasificación](COMPARATIVO_Y_CLASIFICACION_A.md),
[recuperación](A5_RECUPERACION_NOSQL.md), [paso común](PASO_A_ENTORNO_COMUN.md),
[viabilidad de merge](ESTADO_PARA_MERGE.md).
