> Para probar React y Django con datos persistentes, sigue la
> [guía de prueba con Docker](docs/implementacion/PRUEBA_DOCKER.md). Si ya tienes
> datos o cuentas, consulta el [traspaso para Pablo](PARA_EL_AGENTE_DE_PABLO.md)
> antes de recrear servicios.

> Ampliación en rama `implementacion`: [operación de las cuatro instituciones](docs/implementacion/README.md), catálogos, agenda y administración. Requiere mantenimiento explícito de permisos/esquema antes de desplegar en datos existentes.

> Frontend: [plan de rediseño y ramas de trabajo](docs/implementacion/PLAN_REDISENO_FRONTEND.md).

# Historiales clínicos

Proyecto cliente-servidor para administrar historiales clínicos de cuatro instituciones. Cada institución utiliza un motor distinto y el backend mantiene la lógica de negocio separada de los detalles de persistencia.

**Plan vigente:** [PLAN_MAESTRO.md](PLAN_MAESTRO.md) versión 2.0, módulos autónomos,
contratos 1.0.0 y dos ramas permanentes: feature/jennifer y feature/pablo.
Manuales: [Jennifer](GUIA_JENNIFER_AGENTES.md) y [Pablo](GUIA_PABLO_AGENTES.md).
[ESTADO_INTEGRACION.md](ESTADO_INTEGRACION.md) conserva el registro histórico de PR
y pruebas previas; no impone el antiguo gate F0 ni aprobaciones cruzadas.

| Institución | Motor | Puerto local |
|---|---|---:|
| Hospital general | PostgreSQL 16 | 5432 |
| Centro médico pediátrico | MySQL 8.4 | 3307 |
| Laboratorio clínico | MongoDB 7 | 27017 |
| Clínica odontológica | Firestore Emulator | 8082 (8080 dentro de Docker) |

## Tecnologías

- Backend: Django 5.2 LTS y Django REST Framework.
- Frontend: React 19 y Vite.
- Desarrollo local: Docker Compose.
- Arquitectura inicial: dominio, aplicación, infraestructura y presentación.

## Estructura

```text
historiales-clinicos/
├── backend/
│   ├── config/                         # Configuración de Django
│   ├── apps/identidad/                 # Cuenta, perfil, profesional y sesión técnica
│   ├── apps/historiales/
│   │   ├── domain/                     # Entidades y puertos
│   │   ├── application/                # Casos de uso
│   │   ├── infrastructure/adapters/    # PostgreSQL, MySQL, MongoDB y Firestore
│   │   └── presentation/               # API REST
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/api/                        # Comunicación con Django
│   ├── src/components/
│   ├── src/pages/
│   └── Dockerfile
├── db/
│   ├── postgres/init.sql
│   ├── mysql/init.sql
│   ├── identity/consolidated-roles.sh  # Roles para el esquema hospital.identidad
│   ├── mongo/                         # Esquemas clínicos y definiciones legadas
│   └── firebase/
├── docker-compose.yml
└── .env.example
```

## Primer inicio

La [guía de prueba con Docker](docs/implementacion/PRUEBA_DOCKER.md) cubre el
arranque desde cero, la verificación de la API y los recorridos en React.
Para actualizar una instalación existente, conserva sus respaldos y completa
el traslado de identidad antes de recrear el backend.

## Direcciones

- React: http://localhost:5173
- API Django: http://localhost:8000/api/
- Salud del backend: http://localhost:8000/api/health/
- Estado de las cuatro bases: http://localhost:8000/api/health/databases/
- Autenticación: `/api/auth/csrf/`, `/api/auth/login/`, `/api/auth/me/`, `/api/auth/logout/`
- API clínica: `/api/pacientes/`, `/api/pacientes/{id}/historial/` y las rutas
  de consulta/diagnóstico/tratamiento/receta/archivo de [B5](docs/pablo/B5_API_INTEGRACION.md).
- Catálogo institucional: `/api/medicamentos/` (sesión y rol autorizado).
- Django Admin: http://localhost:8000/admin/ (cuenta técnica; no da acceso clínico automático)
- Firestore UI: http://localhost:4000
- Adminer: http://localhost:8081

## Distribución por células autónomas

### Pablo: backend central y motores relacionales

- `db/postgres/init.sql`
- `db/mysql/init.sql`
- `backend/apps/historiales/infrastructure/adapters/postgres_adapter.py`
- `backend/apps/historiales/infrastructure/adapters/mysql_adapter.py`

Rama permanente ya preparada:

```powershell
git switch feature/pablo
```

### Jennifer: React y motores documentales

- `db/mongo/init.js`
- `db/firebase/`
- `backend/apps/historiales/infrastructure/adapters/mongo_adapter.py`
- `backend/apps/historiales/infrastructure/adapters/firestore_adapter.py`

Rama permanente ya preparada:

```powershell
git switch feature/jennifer
```

Cada ruta tiene un dueño único según el plan: backend central, contratos y Compose
son de Pablo; frontend y NoSQL son de Jennifer. Las dependencias se resuelven por
contratos y pruebas, sin aprobaciones cruzadas obligatorias. Respetar reglas GitHub.

## Clonar el repositorio existente

El proyecto ya está publicado; no reinicializar Git ni recrear sus ramas. En otro
equipo, clonar y usar la rama permanente correspondiente:

```powershell
git clone https://github.com/PabloZ7-425/Red_Instituciones_Medicas.git
cd Red_Instituciones_Medicas
git switch feature/jennifer  # Pablo: feature/pablo
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
docker compose up --build -d
```

El archivo `.env` y los datos internos de Docker son locales. No deben subirse ni copiarse entre computadoras.

## Flujo diario

Antes de trabajar:

```powershell
git fetch origin
git switch feature/pablo  # Jennifer: feature/jennifer
git merge origin/main
```

Al terminar:

```powershell
git add -- <rutas-propias>
git commit -m "feat(auth): implementa sesiones institucionales"
git push -u origin feature/pablo  # Jennifer: feature/jennifer
```

Ejecutar pruebas antes del commit. Luego crear un PR por módulo hacia main; un
solo PR activo por rama. Integrar al pasar aceptación y reglas GitHub. Conservar
las ramas permanentes y sincronizarlas desde main después de cada integración.

## Cambios en los scripts de base de datos

Los SQL de PostgreSQL y MySQL se ejecutan únicamente cuando sus volúmenes están
vacíos. Un cambio de init.sql no actualiza volúmenes existentes. Para evolucionar
una base poblada, preparar una migración incremental con respaldo y reversión;
los experimentos de diseño se ejecutan en instancias temporales separadas.
Consultar [las pruebas SQL aisladas](docs/pablo/fase0/PRUEBAS_SQL_AISLADAS.md).
No usar `docker compose down -v` como procedimiento de actualización: elimina los
datos locales almacenados en los volúmenes del proyecto.

## Estado actual

La estructura, conectividad, fixtures React, modelos/semillas
DEMO MongoDB y Firestore, recuperación Firestore y experimentos SQL están
integrados y verificados. B1 materializa los contratos y casos de uso. B2 implementa
login, sesión, CSRF, perfil institucional y permisos, con PostgreSQL técnico separado.
Su configuración, cuentas DEMO seguras, pruebas y reversión están en
[B2_IDENTIDAD.md](docs/pablo/B2_IDENTIDAD.md). B5 publica la API clínica y su
integración real con los cuatro motores y el flujo React A4 incorporado.
B3 implementa el repositorio hospitalario real,
transacciones, fecha civil y hospitalización con migración respaldada y rol limitado;
ver [B3_POSTGRESQL.md](docs/pablo/B3_POSTGRESQL.md). B4 implementa el repositorio
MySQL, las relaciones por ocurrencia, tutores, vacunas y crecimiento, con migración
respaldada y usuario limitado; ver [B4_MYSQL.md](docs/pablo/B4_MYSQL.md).
Composición A/B integrada y verificada en **feature/pablo**, sin modificar main:
230 pruebas backend, 55 cliente, 14 HTTP/nativas, 10 de recuperación fría y siete
recorridos Chromium aprobados. Los cuatro adaptadores implementan el contrato;
`python manage.py audit_clinical_providers --require-all` termina en 0.
Ensayo aislado en [ops/integration](ops/integration/README.md). El servicio
`integration-tests` anterior conserva su alcance B y puede omitir suites A que
requieren destinos dedicados; no reemplaza este ensayo completo.
Arranque común con referencias/cuentas DEMO explícitas, sin generar pacientes:
`docker compose run --rm --no-deps local-setup`, únicamente después de inventario,
respaldo y migraciones. Claves privadas en `.local/bootstrap/access.json`.
Frontend sirve el build estático, sin servidor/editor de Vite; se documenta el
hallazgo pendiente de actualizar Vite de A. Detalles en
[cierre B5](docs/pablo/B5_CIERRE_INTEGRADO.md) y
[comparativo y clasificación](docs/pablo/COMPARATIVO_MOTORES.md).
La especificación contractual inicial 1.0.0 y próximos módulos están en el plan
maestro. Documentarla no implementa los endpoints ni los adaptadores clínicos.
