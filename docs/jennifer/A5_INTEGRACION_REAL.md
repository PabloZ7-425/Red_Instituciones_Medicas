# A5 — primera integración real de React, sesiones y cuatro motores

Jennifer, 22 de octubre de 2026, America/Guatemala.

**Resultado:** cuatro recorridos Chromium con HTTP real y ocho casos automatizados
HTTP/persistencia/seguridad aprobados. El flujo común ya se probó de extremo a
extremo en una copia aislada. No se declara completo A4/A5 ni se integra B5 a ninguna
rama: faltan especializaciones HTTP y recuperación clínica/documentación final.

## Fuentes exactas y alcance

| Parte | SHA probado |
|---|---|
| API B5 de Pablo | `0ecf7d5fd6301abafd1801b5766934556badfdf8` |
| Adaptadores A3 y React A4 de Jennifer | `9ff890cacb4fd5a64e094a52e27ef7cec19569c0` |
| main observado, sin modificar | `ead042cf3e9042b7c7e969236ba368dd60ebb79a` |

Se extrajo B5 a work/a5-runtime y se superpusieron exclusivamente frontend,
db/firebase, db/mongo y los dos adaptadores NoSQL de Jennifer. Se comprobó que la
copia configurada mediante configure.py reproduce los mismos archivos de API,
adaptadores y formulario utilizados durante las pruebas. No hubo merge, edición
de fuentes de Pablo, sustitución de la fábrica ni dobles de repositorios.

La auditoría B5 `audit_clinical_providers --require-all` termina ahora con código 0
en esa combinación: cuatro proveedores y ningún método faltante. Esto verifica
puertos declarados; la persistencia se verifica por separado con HTTP y lecturas
nativas. La rama real de Jennifer conserva su base y el PR #16 permanece intacto.

## Entorno y preparación

PostgreSQL **16.15**, MySQL **8.4.13**, MongoDB **7.0.45**, Firestore Emulator
**1.22.0** con SDK **2.34.1**; Python **3.12.14**, Django **5.2.18**, PyMongo **4.19.0**,
Node **24.19.0**, Vite **8.3.2**, Chromium del entorno. Docker local, únicamente
puertos de loopback. No se levantó Compose ni se usaron volúmenes de compañeros.

- PostgreSQL temporal aloja hospital e identidad en bases separadas. Preparación
  usa propietario/migrator, pero el servidor recibe hospital_runtime e identidad_app,
  sin DDL, borrado clínico ni acceso a usuario clínico heredado.
- MySQL temporal contiene pediatrico y usa los grants de pediatria_runtime.
- Mongo temporal usa replica set a5 de un nodo y colecciones clínicas v2 preparadas
  con el script propio; catálogo sintético separado del legado. Esta prueba local
  **no certifica autenticación de Mongo, HA ni una migración de datos existentes**.
- Firestore se limita al proyecto emulado demo-jennifer-a5; ninguna cuenta Firebase
  real. No se interpreta esto como certificación de reglas de producción.
- Identidad real Django/PostgreSQL: 17 cuentas DEMO temporales, admin/médico/
  secretaría/enfermería por institución y laboratorista solo en laboratorio.
  No son superusuarios técnicos. Profesional 1 existe en los dos motores SQL.
- Catálogos ficticios y bases clínicas inicialmente vacías. El navegador usa la
  misma identificación en cuatro instituciones para verificar su unicidad local.

La configuración A5 añade solo a la **copia temporal** el origen 127.0.0.1:18173
a CORS/CSRF y ejecuta backend en 18005. No se cambia config/settings.py del repo.
Las contraseñas SQL se generan al preparar la copia, con archivos locales 0600;
no se imprimen ni versionan. La contraseña pública DEMO del navegador es exclusiva
del entorno desechable, no una recomendación para cuentas persistentes.

## Evidencia ejecutada

| Comprobación nueva | Resultado |
|---|---|
| Auditoría de cuatro proveedores B5 | Código 0; sin métodos ausentes |
| Chromium → React → HTTP/CSRF → fábrica → motor | **4 recorridos completos OK**, sin excepciones JS ni fallos HTTP inesperados |
| Casos HTTP/nativo, con subcasos por institución/rol | **8 pruebas OK**, cero omitidas |
| Lectura por nuevos repositorios/conexiones nativas | Igualdad exacta con el historial que dejó el navegador en los cuatro motores |
| Sintaxis de scripts, fuentes ensambladas, propiedad y git diff --check | Correctos |

Cada recorrido de navegador hace login, alta de paciente, consulta, diagnóstico,
tratamiento, elección de medicamento real del catálogo, receta y archivo; vuelve
a leer la cadena conservada y cierra sesión. Se prueba doble submit de paciente y
receta; la lectura nativa posterior demuestra que hay exactamente una consulta,
un diagnóstico, un tratamiento y una receta. El navegador exige HTTP real y no
acepta el aviso de modo DEMO. Los datos siguen siendo sintéticos, aunque el
transporte y persistencia sean reales.

Los ocho casos adicionales verifican:

1. Persistencia en los cuatro adaptadores mediante nuevas conexiones, después
   del logout del navegador; árbol y archivo completos, opcionales null.
2. Archivo idempotente; motivo distinto 409 y rechazo 409 de consulta, diagnóstico,
   tratamiento y receta posteriores, sin modificar historia.
3. Padres ajenos e inexistentes con el mismo 404 seguro: seis operaciones, cuatro
   pares de instituciones en ciclo. No se afirma haber enumerado todos los pares.
4. Alta HTTP y lectura nativa, identificación duplicada 409, campos/motor inyectados,
   fecha inválida y query repetida/desconocida/limit inválido 400.
5. Permisos reales de médico, secretaría, enfermería y laboratorista, incluidos
   archivo, lectura de historia, catálogo y prescripción según el rol.
6. CSRF previo al login inválido tras rotación, escritura sin CSRF 403,
   cookie HttpOnly y replay de sesión cerrada 401.
7. Revocación del profesional en identidad revalidada antes de intentar escribir,
   con restauración de ese atributo DEMO al finalizar cada caso.
8. Roles SQL reales sin DDL/borrado/lectura de usuarios heredados; Django usa
   identidad_app y no el propietario para atender peticiones.

Errores conservan `{error:{code,message,fields}}` y no-store. No se publican dumps,
contraseñas, cookies, cuerpos clínicos reales ni perfiles de navegador.

La preparación inicial detectó que el SDK Firestore Client no es context manager.
Se corrigió el script para cerrar el cliente mediante finally y se reanudó solo
Firestore/identidad del entorno temporal, conservando la preparación SQL/Mongo ya
terminada. El código de preparación publicado contiene esa corrección. No se
cuenta el primer intento fallido como prueba aprobada.

## Reproducción desde Linux, checkout completo y destinos nuevos

Requisitos: Git con ambos SHAs disponibles, Docker, Java compatible con el emulador,
Node compatible con Vite, Chromium y un Python con backend/requirements.txt instalado.
El JAR Firestore 1.22.0 se obtiene por el canal oficial del emulador Firebase y se
mantiene fuera de Git. Exportar A5_RUNTIME en cada terminal nueva con la misma ruta.
Ejecutar una vez sobre un stack nuevo; estas pruebas no
borran ni restablecen automáticamente una ejecución anterior.

```bash
# Desde la raíz del repositorio. El destino debe ser nuevo.
export A5_RUNTIME="$PWD/work/a5-runtime"
python docs/jennifer/a5/configure.py --runtime "$A5_RUNTIME"

docker run -d --name jennifer-a5-postgres --label codex.task=jennifer-a5 \
  --env-file "$A5_RUNTIME/postgres.env" -p 127.0.0.1:15435:5432 postgres:16
docker run -d --name jennifer-a5-mysql --label codex.task=jennifer-a5 \
  --env-file "$A5_RUNTIME/mysql.env" -p 127.0.0.1:3306:3306 mysql:8.4
docker run -d --name jennifer-a5-mongo --label codex.task=jennifer-a5 \
  -p 127.0.0.1:27039:27039 mongo:7 mongod --replSet a5 --bind_ip_all --port 27039

# Tras estar listos los servidores, iniciar el replica set dedicado.
docker exec jennifer-a5-mongo mongosh --port 27039 --quiet --eval \
  'rs.initiate({_id:"a5",members:[{_id:0,host:"127.0.0.1:27039"}]})'
```

En otra terminal iniciar el emulador vacío dedicado, sustituyendo la ruta del JAR:

```bash
java -jar /ruta/local/cloud-firestore-emulator-v1.22.0.jar \
  --host=127.0.0.1 --port=8093 --project_id=demo-jennifer-a5
```

Con Mongo PRIMARY y los demás servicios listos:

```bash
python docs/jennifer/a5/prepare.py --runtime "$A5_RUNTIME"
python docs/jennifer/a5/serve.py --runtime "$A5_RUNTIME" --audit
python docs/jennifer/a5/serve.py --runtime "$A5_RUNTIME"
```

En otra terminal, instalar dependencias solo en la copia y servir React sin mocks:

```bash
npm --cache="$PWD/work/a5-npm-cache" --prefix "$A5_RUNTIME/frontend" install --package-lock=false
VITE_CLINICAL_MODE=http VITE_API_URL=http://127.0.0.1:18005/api \
  npm --prefix "$A5_RUNTIME/frontend" run dev -- --host 127.0.0.1 --port 18173
```

Ejecutar en este orden desde la raíz real del repositorio:

```bash
A5_REAL_HTTP=1 A5_BROWSER_PASSWORD=DEMO-only-isolated-A5-2026 \
  BROWSER_URL=http://127.0.0.1:18173/ npm --prefix frontend run test:browser:real
A5_REAL_HTTP=1 python docs/jennifer/a5/test_http.py
```

Al terminar, stop.py valida etiquetas y ausencia de montajes compartidos antes
de retirar los tres contenedores/volúmenes anónimos y servidores A5 reconocibles:

```bash
python docs/jennifer/a5/stop.py --runtime "$A5_RUNTIME"
```

Fuentes y logs locales se conservan para revisar; el helper no elimina el directorio.
No usar nombres, puertos o credenciales de entornos activos para esta reproducción.

## Estado del plan tras esta evidencia

La integración del flujo **común** de A3/A4 con B5 está demostrada para esos SHAs.
No se necesita recrear modelos, operaciones ni formularios ya terminados. Para
publicar una integración estable falta la decisión correspondiente del equipo;
esta entrega no abre PR, modifica #16, fusiona main ni mueve feature/pablo.

Hospitalización/PED-01 tienen puertos de repositorio, pero B5 todavía no publica
sus rutas HTTP. También faltan flujos especializados de laboratorio/odontología.
Continúan las especializaciones cuando exista su contrato y, por A5, recuperación
clínica general, justificación comparativa/clasificación final y conciliación de
históricos si aparecieran datos fuera de los modelos versionados. Esta prueba no
certifica esos puntos, el equipo de otra persona ni un despliegue de producción.
