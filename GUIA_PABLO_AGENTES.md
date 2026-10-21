# Guía operativa — Pablo y agentes de la célula B

Versión **2.0**, 2026-10-20. Rama permanente **feature/pablo**.
Fuente normativa: [PLAN_MAESTRO.md](PLAN_MAESTRO.md), contratos §5–6, propiedad §7,
calidad §8 y Git §9. Este manual sustituye ciclos y gates de aprobación anteriores.

## 1. Mandato y auditoría de partida

Responsabilidad integral: Django/DRF, dominio/puertos/casos de uso, identidad,
autorización/enrutamiento, API, PostgreSQL hospital, MySQL pediatría, transacciones,
pruebas y documentación central/backend/SQL. Diseña, implementa, corrige, prueba,
publica e integra tus módulos sin exigir revisión de Jennifer. Respeta reglas GitHub
reales y archivos exclusivamente A.

Base main `f9e9f4c`: PR #1–#9 integrados. Solo había main antes de crear las dos
ramas permanentes. Trabajo A conservado: Firestore fff235a y Mongo 1a6c669 son
ancestros integrados; no recrear esos módulos. Backend tiene salud y 12 pruebas;
ports.py solo cuatro métodos clínicos, adaptadores solo health_check; SQLite interno
sigue versionado. No hay login ni API clínica. React solo panel y mocks.
Experimentos SQL 6+7 y suites A tienen evidencia en ESTADO_INTEGRACION, no significan
que existan ya migraciones productivas, autorización o repositorios completos.

Se leyó el PDF oficial, cuatro páginas: §2 del maestro conserva matriz REQ-01..13.
Prioriza flujo clínico y comparación de motores; arquitectura es habilitadora. No
atribuir al profesor requisitos de pagos reales, HA, despliegue público o tooling.

## 2. Tus módulos completos

| Orden/módulo | Entrega | Criterio de cierre |
|---|---|---|
| B1 Contratos/núcleo | Tipos/DTOs, ocho puertos, errores/contexto, casos comunes, factory y suite compartida | Materializar maestro 1.0.0; tests sin motores/UI con dobles y suite reutilizable por cuatro adaptadores; salud conserva cuatro registros |
| B2 Identidad/acceso | ORM técnico, perfil usuario/institución/profesional, roles/sesión/CSRF y login/me/logout | Credenciales hasheadas Django, pruebas positivas/negativas, migración técnica ensayada y rechazo cross-institution/sin perfil |
| B3 Hospital PostgreSQL | Modelo corregido, consulta con fecha, ocho operaciones/catálogo y transacciones | Migración incremental conservadora, suite real, rollback, aislamiento y especialización hospitalaria necesaria |
| B4 Pediatría MySQL | Cita opcional, ocurrencias/relaciones, tutores/vacunas/crecimiento y ocho operaciones/catálogo | Integridad/rollback reales, consulta sin cita, no ramas clínicas ambiguas, suite contractual y especialización priorizada |
| B5 API/calidad central | DRF, validación/errores/permisos, integración cuatro adaptadores, evidencia y comparativo | Rutas maestro operativas, contrato HTTP, fallos seguros, matriz requisitos y flujo real con A |

Orden recomendado B1 → B2 → B3 → B4 → B5; las capas comunes y API pueden probarse
con dobles sin esperar motores. Primero entrega B1 para que A certifique sus adaptadores;
no exigir disponibilidad UI ni aprobación A para cerrar núcleo probado. Jennifer sigue
modelos/UI/semillas contra especificación, aunque tu runtime aún esté pendiente.

## 3. Archivos propios y propiedad central

Puedes modificar backend/** excepto los dos adaptadores NoSQL y test_*_nosql.py de A;
incluye config, domain, application, presentation, factory, drivers SQL, requisitos,
Dockerfile, fixtures/pruebas centrales y futura identidad. También db/postgres/**,
db/mysql/**, docs/pablo/**, esta guía, plan maestro, README, CONTRIBUTING, ESTADO,
Compose, .env.example, .gitignore, .github/CI, configuración global y arquitectura.
Eres dueño de rutas raíz nuevas no asignadas hasta que el plan asigne otro propietario.

No editar frontend/**, db/mongo/**, db/firebase/**, mongo_adapter.py,
firestore_adapter.py, pruebas NoSQL de A ni docs/jennifer. GUIA_JENNIFER_AGENTES.md
solo se reorganiza ahora como excepción documental autorizada; después vuelve a A.
No reparar incompatibilidades en archivos A por urgencia.

Si A necesita capacidad central, implementa en tu módulo con criterio técnico y
pruebas, sin otra ronda de permiso. A aporta valores/prueba esperada y continúa su
trabajo. Compose tiene un único dueño permanente: B. No cambiarlo automáticamente
por un seed NoSQL ni mover cuentas al arrancar sin plan.

## 4. Contratos y núcleo B1

Norma inicial: **CONTRACT-API-01@1.0.0** y **CONTRACT-REPO-01@1.0.0** de maestro
§5–6. Especificación vigente, todavía no implementación. Los candidatos antiguos
son antecedentes, no un gate que deba aprobar Jennifer antes de comenzar.

Consolidar cuatro métodos actuales a ocho: registrar_paciente, listar_pacientes,
obtener_historial, registrar_consulta, registrar_diagnostico, registrar_tratamiento,
registrar_receta y archivar_paciente. Firma/retornos exactos en maestro; no dejar
desactivar_paciente como única implementación del archivo. Catálogo en puerto
auxiliar MedicamentoCatalogo.listar_medicamentos, no un noveno método oculto.

DTOs como JSON sin tipos de driver; IDs string, fechas civiles YYYY-MM-DD y timestamps
UTC Z. Contexto de construcción validado con institucion/usuario_id/rol/profesional_id.
Mantener create(Institution) para salud; añadir create_clinical(contexto). Ninguna
selección de motor desde request. Un adaptador sin contexto solo comprueba salud.
Materializar errores de dominio de maestro en domain/errors.py, con mapeos seguros.

Suite compartida por fabricante de repositorio: alta/listado/árbol clínico, referencias,
duplicados, búsqueda/paginación, inexistencia/aislamiento, archivo idempotente, fallos
intermedios/rollback y carreras. El test_contract_sql existente valida ejemplos;
no anunciarlo como prueba SQL real. Publica código/runtime y prueba de uso, sin
editar los adaptadores A para que hereden clases nuevas antes de que existan.
No romper la comprobación de salud mientras amplías interfaces clínicas.

Congelar v1: no renombrar rutas/campos en sitio. Adiciones compatibles minor y
pruebas; incompatibles major/transición con v1 conservada, sin exigir revisión
humana A. Proveedor causante corrige regresión. Notificar versión pública mediante
repo/documentación; no esperar mensajes para decisiones internas.

## 5. Identidad, seguridad y configuración B2

Django ORM únicamente cuentas/perfil, roles/permisos/sesiones/admin. No pacientes,
consultas, diagnóstico ni recetas ORM de motores clínicos. Usar User estándar más
perfil institucional/profesional; evaluar consecuencias antes de cambiar AUTH_USER_MODEL.
No fuentes paralelas de credenciales desde tablas usuario heredadas ni Firebase Auth.

Base técnica PostgreSQL separada de hospital, rol con privilegios limitados. SQLite
no es un motor institucional válido para el PDF. Inventariar usuarios existentes,
respaldar, ensayar traslado/reconciliación de hashes, reversión y comandos con alias
explícito antes de activar DATABASES. No tratar una contraseña desconocida como hash
Django. Retirar SQLite del índice con --cached conservando archivo, dentro de una
entrega coherente de higiene/identidad; no borrar usuarios ni volúmenes.

Compose hoy ejecuta migrate al arrancar: separar/controlar ese paso antes del cambio
de base. Añadir configuración central reproducible en .env.example sin secretos,
no valores reales en Git. Validadores de contraseña y restricciones propias del
módulo deben quedar probados, no asumir que configuración actual vacía ya los protege.

Sesión/cookies/CSRF y vida máxima están fijados en maestro. Login también valida
CSRF; después rota sesión/secreto. /me determina institución/rol; logout invalida.
Implementar 401 sin sesión intencionalmente (DRF SessionAuthentication puede devolver
403). CSRF/rol denegado 403; recurso ajeno/ausente 404 igual. No bypass clínico para
superusuario técnico. Profesional habilitado obligatorio para escribir clínica.
Preparar cuentas DEMO por institución con mecanismo local seguro, sin publicar claves.

Replica set Mongo de un nodo es capacidad técnica a preparar en B1/B5, no HA.
Revisar estado/datos del volumen, respaldar y aplicar transición no destructiva;
documentar conexión/readiness. A mantiene su init/adapter. Hasta esa transición,
standalone no certifica transacciones multidocumento de A3, pero A puede avanzar
el resto. No imponer ese prerrequisito a todos los módulos.

## 6. SQL B3/B4: resoluciones que se conservan

PostgreSQL: consulta.fecha DATE explícita, sin usar la fecha de cita como verdad
histórica. Migrar con expansión nullable, conciliación documentada y NOT NULL solo
si todos los valores están confirmados. Sin CURRENT_DATE ficticio para rellenar.
Instalación nueva usa columna requerida; adaptador envía fecha validada.

MySQL: consulta.cita_id nullable preserva FK/UNIQUE y permite varias sin cita.
Validar cita/paciente/profesional bajo transacción. Diagnóstico externo identifica
consulta_diagnostico.id; agregar tratamiento.consulta_diagnostico_id y FK compuesta
con consulta_id. Receta.tratamiento_id conserva consulta y comprueba origen; la
proyección externa usa detalle_receta.id. Migrar vínculos previos con evidencia,
nunca elegir el primer diagnóstico/tratamiento de una consulta ambigua.

MySQL DDL tiene commit implícito: ROLLBACK de aplicación no revierte ALTER TABLE.
Separar expansión/conciliación/restricciones, respaldo/reversión ensayados. Actualizar
init.sql y migración incremental en el mismo módulo; init solo corre en volumen vacío.
Los dos verificar_diseno.sql existentes son experimentos, no scripts para base activa.

Ambos drivers: SQL parametrizado, conexiones cerradas, sin consultas clínicas en
vistas ni transaction.atomic para conexiones nativas. Escritura/archivo bloquea
paciente raíz en transacción, revalida relaciones/activo, confirma o revierte todo.
Receta cabecera/detalle es indivisible; no POST reintentado a ciegas. Probar ambos
órdenes con dos conexiones y barreras y demostrar ausencia de parciales.

## 7. API, integración y evidencia B5

Implementar diez rutas y extensiones AUTH-CSRF/AUTH-LOGOUT/CAT-01 exactamente como
§5. API valida tipos/campos desconocidos, usa casos de uso y traduce errores, no SQL.
q prefijo literal NFC/lower/trim, sin wildcard, count antes de paginar; normalizar
orden entre motores. Entregar catálogo por institución para no exigir IDs internos
a mano. Archivo conserva identidad/historial/motivo/fecha y bloquea nuevas escrituras.

Antes de repositorio real, dobles explícitos en tests prueban casos de uso/HTTP.
No entregar datos ficticios como respuesta de producción ni devolver éxito por motor
caído. Si A aún no implementa un adaptador, deja ese caso real pendiente, reporta
exactamente método/version/input y continúa SQL/API propios; no exige aprobación A.
Integración completa B5 requiere los cuatro motores y aislamiento/errores reales.

B5 mantiene comparativo central y matriz REQ. A5 produce aportes propios en
docs/jennifer; B los referencia/compila sin editar su fuente. Incluir modelado,
normalización, consistencia, seguridad, clasificación pública/confidencial/restringida
y motivos de asignación. Diagramas/observaciones de Entrega I ausentes se registran,
no se inventa haberlos incorporado.

## 8. Pruebas antes de commit y PR

```powershell
git status --short
git diff --check
docker compose config -q
docker compose exec -T backend python manage.py check
docker compose exec -T backend python manage.py test apps.historiales
node --test frontend/tests/contract-fixtures.test.js
docker compose exec -T frontend npm run build
curl.exe -f http://localhost:8000/api/health/
curl.exe -f http://localhost:8000/api/health/databases/
```

Son comandos disponibles, no resultados de tu ejecución futura. Test React desde
checkout completo, no solo mount frontend. No hay lint/pytest/Ruff/Black/Vitest/CI
de pruebas configurados. Añadir herramientas necesarias con motivo y comando real.
Probar siempre módulo afectado; ampliar a cliente/NoSQL cuando cambie contrato común.
No repetir suites sin cambios ni anunciar prueba inexistente como aprobada.

Añadir pruebas por módulo en archivos B: identidad, API, PostgreSQL/MySQL y suite
compartida. Usar destinos aislados/fixtures falsos, nunca bases ajenas ni limpieza
global. Disponible hoy: 6+7 experimentos SQL según su documento de ejecución; no
acreditan adapter/archivo concurrente. Una suite omitida sigue pendiente con causa.
Evidencia de cada PR: SHA, comando, código salida, positivo/negativo y limitaciones;
revisar secretos, diff y propiedad de rutas. No compartir .env ni trazas clínicas.

## 9. Git y publicación autónoma

```powershell
git fetch origin
git switch feature/pablo
# Primero conservar cambios pendientes propios; no resetearlos.
git merge origin/main
# Un módulo completo, comprobado antes del commit.
git add -- <rutas-propias>
git commit -m "feat(auth): implementa sesiones institucionales"
git push -u origin feature/pablo
```

Única rama B durante todo desarrollo; no nuevas ramas por tarea/documento/arreglo.
Un PR activo hacia main por módulo desde feature/pablo. No empujar otro módulo a
un PR pendiente. Conventional Commits con scope y descripción concreta, sin reescribir
historial viejo. Después del merge mantener rama y sincronizar main antes del siguiente.
Preferir merge commit para conservar ancestros; no force push/rebase destructivo.
Con trabajo pendiente, commit coherente o stash local de rutas propias antes de mezclar.

PR contiene módulo/dueño, archivos/razón, contratos, funcionalidades, comandos/resultados,
limitaciones/evidencia y datos/migraciones. Puedes integrar al pasar tus criterios y
GitHub, sin aprobación de Jennifer. Si la plataforma exige aprobación o permiso,
reportar esa restricción real; nunca saltarla mediante override administrativo.

## 10. Próxima ejecución

Comenzar B1 con los ocho métodos, errores/contexto y suite compartida; preparar B2
y capacidad Mongo central. No volver a abrir un gate global de firmas. Escalar solo
riesgo real de datos/seguridad/incumplimiento o contradicción insoluble por versión.
Este manual y maestro 2.0 reemplazan las instrucciones operativas históricas de fase0.
