# Historiales clínicos

Proyecto cliente-servidor para administrar historiales clínicos de cuatro instituciones. Cada institución utiliza un motor distinto y el backend mantiene la lógica de negocio separada de los detalles de persistencia.

**Estado consolidado y punto de partida:** consultar [ESTADO_INTEGRACION.md](ESTADO_INTEGRACION.md)
para ver los PR integrados, pruebas ejecutadas, alcance disponible y pendientes.
Las guías y evidencias anteriores conservan su contexto histórico.

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
│   ├── mongo/init.js
│   └── firebase/
├── docker-compose.yml
└── .env.example
```

## Primer inicio

1. Abre Docker Desktop y espera a que indique `Engine running`.
2. Abre PowerShell dentro de esta carpeta.
3. Crea el archivo local de configuración:

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
notepad .env
```

4. Valida Docker Compose:

```powershell
docker compose config -q
```

5. Construye y levanta el proyecto:

```powershell
docker compose up --build -d
```

6. Revisa los contenedores:

```powershell
docker compose ps -a
```

Los siete servicios deben aparecer en `Up`; backend y los cuatro motores deben
mostrar `healthy`. Compose no define un servicio `hc_mongo_init`: Mongo ejecuta
su inicializador al crear el volumen por primera vez. Confirmar además las cuatro
conexiones mediante `/api/health/databases/`.

## Direcciones

- React: http://localhost:5173
- API Django: http://localhost:8000/api/
- Salud del backend: http://localhost:8000/api/health/
- Estado de las cuatro bases: http://localhost:8000/api/health/databases/
- Django Admin: http://localhost:8000/admin/
- Firestore UI: http://localhost:4000
- Adminer: http://localhost:8081

## Distribución para dos personas

### Persona 1: motores relacionales

- `db/postgres/init.sql`
- `db/mysql/init.sql`
- `backend/apps/historiales/infrastructure/adapters/postgres_adapter.py`
- `backend/apps/historiales/infrastructure/adapters/mysql_adapter.py`

Rama sugerida:

```powershell
git switch -c feature/motores-relacionales
```

### Persona 2: motores documentales

- `db/mongo/init.js`
- `db/firebase/`
- `backend/apps/historiales/infrastructure/adapters/mongo_adapter.py`
- `backend/apps/historiales/infrastructure/adapters/firestore_adapter.py`

Rama sugerida:

```powershell
git switch -c feature/motores-documentales
```

Los cambios en `domain`, `application`, `docker-compose.yml` y la interfaz React deben acordarse antes de editarlos, porque son archivos compartidos.

## Subirlo por primera vez a GitHub

Una persona crea un repositorio vacío en GitHub y ejecuta:

```powershell
git init
git add .
git commit -m "Estructura inicial con Django React y cuatro bases"
git branch -M main
git remote add origin URL_DEL_REPOSITORIO
git push -u origin main
```

Después agrega a la segunda persona como colaboradora. La segunda persona clona el repositorio:

```powershell
git clone URL_DEL_REPOSITORIO
cd historiales-clinicos
Copy-Item .env.example .env
docker compose up --build -d
```

El archivo `.env` y los datos internos de Docker son locales. No deben subirse ni copiarse entre computadoras.

## Flujo diario

Antes de trabajar:

```powershell
git switch main
git pull
git switch nombre-de-tu-rama
git merge main
```

Al terminar:

```powershell
git add .
git commit -m "Descripción clara del cambio"
git push
```

Luego se crea un Pull Request hacia `main`.

## Cambios en los scripts de base de datos

Los SQL de PostgreSQL y MySQL se ejecutan únicamente cuando sus volúmenes están
vacíos. Un cambio de init.sql no actualiza volúmenes existentes. Para evolucionar
una base poblada, preparar una migración incremental con respaldo y reversión;
los experimentos de diseño se ejecutan en instancias temporales separadas.
Consultar [las pruebas SQL aisladas](docs/pablo/fase0/PRUEBAS_SQL_AISLADAS.md).
No usar `docker compose down -v` como procedimiento de actualización: elimina los
datos locales almacenados en los volúmenes del proyecto.

## Estado actual

La estructura, conectividad, contratos candidatos, fixtures React, modelos/semillas
DEMO MongoDB y Firestore, recuperación Firestore y experimentos SQL están
integrados y verificados. Login, permisos y CRUD clínico real siguen pendientes.
El detalle vigente está en [ESTADO_INTEGRACION.md](ESTADO_INTEGRACION.md).
