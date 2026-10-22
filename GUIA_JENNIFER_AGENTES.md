# Guía operativa — Jennifer y agentes de la célula A

Versión **2.0**, 2026-10-20. Rama permanente **feature/jennifer**.
Fuente normativa: [PLAN_MAESTRO.md](PLAN_MAESTRO.md), especialmente contratos §5–6,
propiedad §7, pruebas §8 y Git §9. Este manual sustituye el flujo anterior por ciclos.

## Estado actual — 22 de octubre de 2026

La entrega permanece en **feature/jennifer**, sin PR ni integración a main salvo
instrucción expresa de Jennifer. Esto sustituye las indicaciones de integración
autónoma de las secciones históricas inferiores. El núcleo B1–B4 se incorporó con
`d656044`, preservando A1/A2 y React. A3 ya implementa ocho operaciones y catálogo
contra Mongo/Firestore v2; evidencia, preparación y límites en
[docs/jennifer/A3_NOSQL.md](docs/jennifer/A3_NOSQL.md).

A4 ya tiene sesión, pacientes, lectura, consulta, diagnóstico, tratamiento,
catálogo/receta y archivo. Evidencia: [A4_FLUJO_CLINICO.md](docs/jennifer/A4_FLUJO_CLINICO.md).
El flujo común ya pasó React → B5 → cuatro motores en copia aislada; evidencia
y SHAs en [A5_INTEGRACION_REAL.md](docs/jennifer/A5_INTEGRACION_REAL.md).
Sigue con especializaciones cuando exista contrato HTTP y el resto de A5; esta
prueba no incorpora B5 a la rama ni autoriza integrar main. Los párrafos siguientes conservan el punto de partida del
plan 2.0; no usar sus menciones a «solo health_check» o «B1 aún ausente» como estado
actual. A1/A2 siguen preservados y no necesitan recrearse.

## 1. Mandato y punto de partida

Eres responsable integral de frontend React/Vite, MongoDB laboratorio, Firestore
odontología, adaptadores NoSQL, pruebas y documentación de esos módulos. Diseña,
implementa, corrige, prueba, publica e integra tu entrega sin esperar aprobación de
Pablo. Respeta los checks/protecciones reales de GitHub y la propiedad exclusiva.

main auditado `f9e9f4c`: tu trabajo Firestore `fff235a` y Mongo `1a6c669` está
integrado y preservado; no lo recrees. Ya hay modelos/semillas, exportación Firestore,
tests NoSQL y fixtures React. Evidencia histórica consolidada: 12 pruebas Firestore,
7 Mongo y 8 cliente, más build y recuperación; no son una ejecución nueva de tu agente.
Los adaptadores actuales solo tienen health_check; la UI activa sigue siendo salud.
No confundir semillas o mocks con un módulo clínico funcional.

El PDF del profesor tiene cuatro páginas: p. 1 contexto; p. 2 análisis/ER/normalización
y clasificación; p. 3 aplicación/asignación; p. 4 operaciones equivalentes, documental,
interfaz, archivo/enrutamiento y comparativo. La matriz REQ-01..13 del maestro indica
qué entregar. No agregar facturación real, Firebase Auth ni infraestructura empresarial.

## 2. Módulos completos y prioridad

| Módulo | Tu entrega | Cuándo está terminado |
|---|---|---|
| A1 Firestore | Modelo odontológico con referencias/embebidos justificados, documentos DEMO, validación, seed y recuperación | Reutiliza db/firebase; seed idempotente/conflicto sin parciales, fecha civil/ocurrencias documentadas y lectura igual tras importación sin seed |
| A2 MongoDB | Laboratorio con consultas/exámenes/resultados variables, validadores, índices, DEMO y consistencia | Reutiliza db/mongo; pruebas servidor, duplicados/estado/resultados, crecimiento e índices justificados; fallback URI coherente con topología disponible |
| A3 Adaptadores NoSQL | Ocho métodos de historial y catálogo, traducción de errores/IDs y transacciones | Suite común contra ambos motores, aislamiento, archivo concurrente y rollback; sin excepciones de drivers fuera del puerto |
| A4 React | UI completa login/pacientes/historia/consulta/diagnóstico/tratamiento/receta/archivo, especializaciones y estados | Mismos componentes cuatro instituciones, contrato consumido, carga/vacío/error, permisos reflejados, build y flujo final con API real |
| A5 Calidad y documentación A | Integración/E2E, seguridad cliente, consistencia/recuperación y evidencia académica | REQ aplicables con pruebas ejecutadas; modelo documental, clasificación y sección comparativa propia en docs/jennifer |

Primero conserva/cierra lo existente de A1/A2. Después elige A3 o A4 según capacidad
disponible; puedes construir A4 con mocks sin API. Trabaja un módulo publicable por
vez para no introducir otro módulo en el mismo PR desde tu única rama. A5 consolida
evidencia, sin posponer los flujos obligatorios por extras.

Dependencias concretas: B1 debe publicar runtime/suite para certificar A3; replica
set habilita transacciones Mongo; B2/B5 habilitan integración final UI. Mientras
faltan, continúa modelos, seeds, componentes, mocks y pruebas propias. No es un
permiso pendiente ni impide terminar entregas independientes.

## 3. Tus archivos y límites

Puedes modificar exclusivamente:

- frontend/**: código, package/dependencias, configuración, Dockerfile, tests, mocks y docs.
- db/mongo/** y db/firebase/**: modelos, scripts, índices, seeds, pruebas y docs.
- backend/apps/historiales/infrastructure/adapters/mongo_adapter.py y firestore_adapter.py.
- backend/apps/historiales/test_*_nosql.py, docs/jennifer/** y esta guía.

No modificar backend/config, domain, application, presentation, factory, drivers
SQL, db/postgres, db/mysql, backend/requirements ni pruebas/fixtures centrales de
Pablo. Compose, .env.example, README raíz, .github/CI, contratos y plan central son
de Pablo. El resto de backend es B salvo tus excepciones indicadas arriba.
No usar edición de un archivo B como workaround de integración.

Capacidad de configuración necesaria: describe valores, propósito, compatibilidad
y prueba en tu doc/issue. El dueño central la implementa; tú continúas lo independiente.
No pedir autorización para decisiones internas NoSQL/UI, ni exigir que Pablo revise
tu PR. No tocar Compose para habilitar replica set: B es su dueño permanente.
Las carpetas propias permiten scripts locales aislados, sin cambiar el arranque común.

## 4. Contratos que debes implementar/consumir

Versión fija inicial: **CONTRACT-API-01@1.0.0** y **CONTRACT-REPO-01@1.0.0** del
maestro. Los candidatos históricos de docs/pablo/fase0 no vuelven a imponer gate F0.
La especificación está definida; el código central de ocho métodos aún es B1.

Resumen para trabajar sin inventar:

- Diez operaciones API-01..10 conservadas; extensiones explícitas AUTH-CSRF,
  AUTH-LOGOUT y CAT-01. Rutas, campos, códigos y respuestas exactos en maestro §5.
- IDs externos opacos string; ObjectId, DocumentReference y Timestamp permanecen
  internos. Fecha civil YYYY-MM-DD; timestamp UTC Z. Conservar null opcional y [] vacío.
- Diagnóstico público identifica una ocurrencia de consulta/paciente, no un código
  reutilizable. Tu modelo necesita IDs propios para diagnóstico/tratamiento/receta.
- q es prefijo literal con trim + NFC + lower, sin eliminar acentos ni comodines;
  campos paciente por OR; count antes de paginar, limit 20/1..100 y offset 0/>=0.
  Asegurar mismo orden externo aunque el motor use índices/colaciones diferentes.
- Consulta obtiene profesional del contexto backend, no de un campo médico arbitrario
  del formulario. Laboratorista puede registrar atención, no prescribir; matriz §5.3.
- API-09 selecciona medicamento desde CAT-01 por ID devuelto. No pedir escribir IDs
  internos a mano ni suponer que DEMO-M-1 existe en una base sin resolver el seed.
- API clínica exige sesión; React usa credentials: include, obtiene csrfToken por
  AUTH-CSRF y envía X-CSRFToken en POST/PATCH, incluido login. Repetir AUTH-CSRF después
  de login porque se rota el secreto. Logout invalida; no guardar tokens en localStorage.
- Usuario/institución autorizados vienen de /me; no selector de motor ni login Mongo/
  Firebase paralelo. Ocultar botones no sustituye autorización backend.
- Error uniforme {error:{code,message,fields}}; fields siempre objeto. Distinguir
  400/401/403/404/409/415/405/500/503; no convertir error de red en lista vacía exitosa.

Los ocho métodos: registrar_paciente, listar_pacientes, obtener_historial,
registrar_consulta, registrar_diagnostico, registrar_tratamiento, registrar_receta,
archivar_paciente. Constructor/contexto y firmas exactas en §6; catálogo es puerto
auxiliar listar_medicamentos. Sin contexto válido solo salud, nunca acceso clínico.
No editar ports.py ni declarar que ya existen excepciones que B1 aún no materializa.

### Atomicidad y archivo

Archivo conserva historia/motivo/fecha; repetir mismo motivo no cambia fecha,
otro motivo es CONFLICT. No escritura clínica posterior al commit de archivo.
Mongo: transacción multidocumento sobre replica set, comprobar activo y modificar
versión raíz; lectura snapshot sola o lock en memoria no bastan. Firestore: leer
paciente dentro de transacción de hijos; reintentos vuelven a comprobar activo.
Pruebas con dos operaciones y barreras: archivo gana, escritor gana y rollback.
Un seed idempotente no acredita ninguna de esas garantías clínicas.

## 5. Mocks e incompatibilidades sin bloquear toda la célula

Reutiliza frontend/src/mocks y los ejemplos B. Modo mock explícito en desarrollo,
separado del servicio HTTP productivo; no fallback silencioso cuando falla la API.
Actualiza tu copia a la versión publicada del contrato y verifica equivalencia con
fixtures B; no cambies el fixture central para pasar un test. Extensiones de catálogo/
CSRF tienen ejemplos en maestro y B1 ampliará fixtures; no inventar nuevas rutas.

Si falta endpoint/runtime ajeno, registra exactamente versión, operación, dato DEMO,
esperado y prueba pendiente; usa un doble en tests/UI y continúa el módulo propio.
Si tu adaptador rompe contrato, corrígelo tú; si B rompe su proveedor, publica la
reproducción y mantén el contrato vigente. No esperar un «aprobado» para arreglar tu
código. Cambios públicos incompatibles necesitan major/transición, no sobrescritura.
Solo escalar contradicción irresoluble por contrato, seguridad, pérdida de datos o
incumplimiento académico. Una dependencia real no se presenta como función terminada.

## 6. Pruebas y evidencia

Desde checkout completo, disponibles hoy:

```powershell
git status --short
git diff --check
node --test frontend/tests/contract-fixtures.test.js
docker compose exec -T frontend npm run build
docker compose exec -T backend python manage.py check
docker compose exec -T backend python manage.py test apps.historiales
curl.exe -f http://localhost:8000/api/health/databases/
```

También `npm --prefix frontend run test:contract` desde el host con Node compatible.
No ejecutar esa comparación solo en Docker frontend: no monta el fixture backend.
Hoy no hay lint/Vitest/ESLint configurados. Añadir herramienta necesaria dentro de
tu módulo con script reproducible, sin pedir aprobación por preferencia interna.

NoSQL, con Python/SDK oficiales y Node para Mongo, cada suite en proceso separado:

```powershell
python -m unittest discover -s db/firebase/tests -v
python -m unittest discover -s db/mongo/tests -v
```

READMEs detallan variables/destinos. Mongo exige MONGO_DEMO_URI de laboratorio_demo
vacía y aislada. Firestore integración usa FIRESTORE_EMULATOR_HOST local y proyecto
demo-historiales; export tests requieren FIRESTORE_RECOVERY_TESTS=1 y mismo filesystem
del servidor. Sin esas condiciones hay skips explícitos, no integración aprobada.
No apuntar a datos de un compañero. Solo limpiar documentos DEMO creados por el test.

A3 debe ejecutar suite compartida real en ambos motores y test de errores/archivo,
aislamiento y fallo intermedio. A4/A5 deben probar cuatro instituciones con API real
antes de declarar integración completa. Registrar comando, SHA, versiones, aprobado/
fallido/omitido y causa. No publicar screenshots ni dumps con datos/credenciales reales.

## 7. Rama permanente y PR de módulo

```powershell
git fetch origin
git switch feature/jennifer
# Preservar primero cualquier cambio propio pendiente.
git merge origin/main
# Implementar módulo; revisar diff y correr pruebas antes de commit.
git add -- <rutas-propias>
git commit -m "feat(firestore): completa persistencia odontológica"
git push -u origin feature/jennifer
```

No crear ramas por tarea ni reabrir ramas antiguas. Un único PR de módulo activo
desde feature/jennifer a main. No empujar otro módulo mientras ese PR esté abierto.
Commits pequeños Conventional Commits: feat/fix/test/docs/chore/refactor(scope):
descripción concreta. Nada de «varios», «final» o «fix» sin contexto.

PR incluye módulo, dueño, archivos, contratos/versiones, funciones, comandos y
resultados, límites/evidencia y tratamiento de datos. Integra cuando tu aceptación
y GitHub lo permitan, sin aprobación obligatoria de Pablo. No usar bypass de reglas
GitHub; si la plataforma requiere revisión, informar ese requisito real. Conservar
feature/jennifer después del merge y actualizarla desde main antes de otro módulo.
Preferir merge commit; no force push, reset destructivo ni perder trabajo sin publicar.

## 8. Próxima ejecución

Sin programar de nuevo lo terminado: revisar A1/A2 contra especificación 1.0.0,
completar sus decisiones/documentos y pruebas faltantes; elegir entrega funcional
NoSQL o UI. Mantener dependencias técnicas registradas y continuar lo independiente.
La propiedad de esta guía vuelve a Jennifer al integrar la reorganización inicial.
