# Historiales clínicos

Proyecto cliente-servidor para administrar historiales clínicos de cuatro instituciones. Cada institución utiliza un motor distinto y el backend mantiene la lógica de negocio separada de los detalles de persistencia.

| Institución | Motor | Puerto local |
|---|---|---:|
| Hospital general | PostgreSQL 16 | 5432 |
| Centro médico pediátrico | MySQL 8.4 | 3307 |
| Laboratorio clínico | MongoDB 7 | 27017 |
| Clínica odontológica | Firestore Emulator | 8080 |

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
Copy-Item .env.example .env
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

`hc_mongo_init` debe terminar como `Exited (0)`. Los demás servicios principales deben aparecer en `Up` o `healthy`.

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

Los SQL de PostgreSQL y MySQL se ejecutan únicamente cuando sus volúmenes están vacíos. Durante el desarrollo, si cambia la estructura y necesitan reconstruirla:

```powershell
docker compose down -v
docker compose up --build -d
```

El comando `down -v` elimina todos los datos locales. No debe utilizarse cuando haya información que necesiten conservar.

## Estado actual

La estructura, los contenedores y las comprobaciones de conexión están preparados. El CRUD de pacientes, consultas, diagnósticos, tratamientos y recetas se implementará posteriormente mediante casos de uso comunes y un adaptador por motor.
