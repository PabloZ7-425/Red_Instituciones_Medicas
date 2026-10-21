# Odontología: modelo y seed DEMO preparatorio

Tarea `A-C1-T1`, PR-03 **del plan**. Fase 0 sigue abierta. Este modelo interno
provisional no define `CONTRACT-API-01` ni implementa `CONTRACT-REPO-01`.
La autorización de Jennifer permite preparar modelo, seed y pruebas independientes;
la integración clínica espera la ratificación conjunta. No modifica Compose,
autenticación, puertos ni `firestore_adapter.py`.

## Modelo documental

| Colección | Contenido y acceso | Decisión |
|---|---|---|
| `pacientes` | Identificación ficticia, nombres, fecha civil, estado y contacto DEMO | Contacto pequeño embebido; historial fuera del documento |
| `citas` | Paciente, fecha UTC, motivo y estado | Documento separado: crece por paciente |
| `consultas` | Paciente, cita, fecha y motivo | Diagnósticos breves embebidos (1–10 en esta demo) con identidad propia |
| `procedimientos` | Paciente, consulta, pieza permanente FDI, descripción y estado | Documento separado: búsqueda por consulta/paciente; no es todavía el DTO de tratamiento común |
| `recetas` | Paciente, consulta, fecha e indicaciones ficticias (1–10), con medicamento, dosis, vía, frecuencia y duración | Renglones acotados embebidos; no sustituye la receta clínica contractual |
| `pagos` | Paciente, procedimiento, fecha, GTQ, centavos enteros y estado | Registro administrativo separado; sin cobro ni pasarela |

Referencias lógicas son IDs DEMO, no objetos `DocumentReference`. Los nombres y
límites anteriores pertenecen al fixture, no son decisiones definitivas de dominio.
Los siete documentos incluyen dos pacientes sintéticos y un recorrido relacionado.
No contiene credenciales, usuarios, teléfonos reales ni prescripciones utilizables.
`seed_version` identifica el fixture escrito. Timestamps se convierten a Timestamp
Firestore mediante datetime UTC; nacimiento permanece como fecha civil en cadena.
Los IDs legibles `DEMO-*` sirven para reproducción; el formato público final depende
de D0-05, no se obliga a la API a exponer rutas o IDs de documentos.

El seed escribe por ID conocido. Consultas futuras por paciente/fecha o
procedimiento/estado requerirán comprobar índices según consultas reales; no se
declaran índices compuestos sin necesidad. El emulador no acredita las políticas,
índices ni restricciones de un servicio de producción. La validación es del script,
no una restricción de esquema del servidor Firestore ni autorización de Django.

## Ejecución sin conexión

Desde la raíz, Python 3.10+ y su biblioteca estándar:

```bash
python db/firebase/seed_demo.py --validate-only
python -m unittest discover -s db/firebase/tests -v
```

Sin `FIRESTORE_EMULATOR_HOST`, los tests de integración aparecen como **skipped**;
no cuentan como aprobados. Las pruebas unitarias verifican campos, tipos, estados,
fechas, referencias entre pacientes, dinero, duplicados y rechazo de destinos remotos.

## Emulador y SDK

Reutilizar el Firestore de Docker local existente, sin recrear volúmenes ni iniciar
el backend con migraciones como efecto secundario. Alternativamente iniciar solo
el emulador Firebase con Java 21 y Firebase CLI en un directorio temporal, copiando
`firebase.json`; ajustar allí los puertos si están ocupados. No cambiar el Compose
compartido. Instalar en un venv local el rango `firebase-admin>=7,<8` ya declarado
en `backend/requirements.txt`; incluye el SDK oficial `google-cloud-firestore`.
Para reproducir una ejecución exacta, conservar su `pip freeze` local y versiones
Java/CLI. El Dockerfile existente instala Firebase CLI sin pin: no se cambia aquí.

Desde el host (PowerShell: usar `$env:NOMBRE='valor'`):

```bash
export FIRESTORE_EMULATOR_HOST=127.0.0.1:8082
export FIREBASE_PROJECT_ID=demo-historiales
python db/firebase/seed_demo.py
python db/firebase/seed_demo.py
python -m unittest discover -s db/firebase/tests -v
```

Primera ejecución en proyecto vacío: `created=7`; repetición idéntica:
`created=0, unchanged=7`. Dentro de la red Compose el destino es `firestore:8080`.
Solo se permiten loopback o el hostname `firestore`, sin URL con esquema y con
puerto explícito, proyecto `demo-historiales` y credenciales anónimas. La ausencia
del destino aborta antes de construir el cliente; no hay fallback a Firestore real.

El seed lee todos los destinos antes de escribir y crea lo ausente en una sola
transacción. Si cualquier documento tiene contenido diferente, aborta el conjunto.
No borra ni actualiza registros existentes. Para revisar un conflicto conservar la
copia y decidir manualmente el siguiente dataset; no vaciar la base. Una repetición
exacta no modifica timestamps. Los tests usan IDs aleatorios propios y solo limpian
esos documentos, nunca colecciones ni volúmenes. Un destino configurado pero caído
produce error de integración; no se transforma en skip.

## Exportar e importar durante desarrollo

### Alternativa local comprobada sin hub

En un emulador nativo **dedicado**, en la misma máquina y filesystem que Python,
sin escritores concurrentes, el nuevo `export_demo.py` usa directamente la API de
exportación del emulador. Rechaza datasets distintos de los siete documentos
originales, subcolecciones adicionales, destinos existentes y rutas dentro del
repositorio. No restaura datos encima de una instancia existente.

```bash
export FIRESTORE_EMULATOR_HOST=127.0.0.1:8082
python db/firebase/seed_demo.py
python db/firebase/export_demo.py --output /ruta/local/nueva/export-odontologia
# Detener solo el emulador dedicado y lanzar otra instancia aislada importando:
firebase emulators:exec --only firestore --project demo-historiales \
  --import /ruta/local/nueva/export-odontologia/firestore_export \
  'python /ruta/repo/db/firebase/export_demo.py --verify-only'
```

El comando de verificación solo lee: devuelve `{"verified": 7}` si pacientes,
relaciones, fechas y todos los valores coinciden. No ejecuta seed ni recrea datos
perdidos. La carpeta exportada contiene el formato nativo Firestore que acepta
Firebase CLI con `--import`; no se inventan metadatos del hub.

No utilizar este script contra el puerto publicado de un contenedor: la ruta de
salida se interpreta en el servidor y debe compartir filesystem con Python. Para
Docker conservar el flujo CLI inferior y una ruta de exportación coordinada.
La exportación requiere detener escrituras de otros procesos: la comprobación
previa del fixture no es un bloqueo transaccional sobre otros clientes.

Para ejecutar también las pruebas de exportación en emulador nativo vacío dedicado:

```bash
export FIRESTORE_RECOVERY_TESTS=1
firebase emulators:exec --only firestore --project demo-historiales \
  'python -m unittest discover -s /ruta/repo/db/firebase/tests -v'
```

Resultado actual: **12 pruebas aprobadas, ninguna omitida**. Sin destino ni flag,
la suite ejecuta seis pruebas unitarias y omite seis de integración explícitamente.
Las pruebas de recuperación requieren instancia vacía y solo limpian los documentos
que crean. No apuntarlas al dataset de trabajo de otro compañero.

### Flujo CLI habitual

Con Firebase CLI instalada, confirmar host, puerto y proyecto de la instancia local
antes de usarla. Conservar exportaciones **fuera del repositorio**, solo datos DEMO.

```bash
firebase emulators:export /ruta/local/fuera-del-repo/export-odontologia --project demo-historiales
firebase emulators:start --only firestore --project demo-historiales --import /ruta/local/fuera-del-repo/export-odontologia
```

El segundo comando se ejecuta en un entorno de emulador **separado**, con su propia
configuración y puertos libres. El CLI debe descubrir la misma instancia que se
quiere exportar; no lanzar el comando desde otro proyecto/configuración. No copiar
estos comandos a un contenedor ya activo como si iniciaran un segundo servidor en
el mismo puerto. Los volúmenes actuales no garantizan persistencia Firestore.

Prueba de recuperación: sembrar, exportar, iniciar un emulador aislado importando
y ejecutar `export_demo.py --verify-only` para verificar los siete documentos y
sus relaciones sin recrear nada. Un test de integración exitoso no acredita
export/import: guardar evidencia separada. No se añade export-on-exit automático ni
mount de persistencia: cualquier cambio de Compose requiere acuerdo A↔B.

## Dependencias y límites

- B-C0-T1: DTOs, errores, roles, IDs públicos y límites definitivos.
- D0-06/07: decidir si diagnósticos definitivos serán documentos separados y qué
  garantías clínicas requieren transacciones; este seed no decide atomicidad clínica.
- D0-08: aprobar ubicación de exportaciones y coordinación de infraestructura.
- La receta DEMO usa indicaciones no terapéuticas; falta mapear diagnóstico,
  tratamiento y prescripción al contrato ratificado. No es un adaptador clínico.
- Ver `VALIDACION.md` para evidencia real de esta rama y pendientes.
