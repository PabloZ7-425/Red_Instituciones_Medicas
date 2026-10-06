# Forma de trabajo

1. No programar directamente sobre `main`.
2. Crear una rama por cambio: `feature/nombre`, `fix/nombre` o `docs/nombre`.
3. Ejecutar `git pull` antes de iniciar.
4. No subir `.env`, credenciales, `node_modules`, `db.sqlite3` ni datos de Docker.
5. Hacer commits pequeños y con mensajes claros.
6. Crear un Pull Request y pedir revisión a la otra persona.
7. Probar `docker compose up --build -d` antes de integrar cambios grandes.

## Archivos compartidos

Los siguientes archivos requieren coordinación previa:

- `docker-compose.yml`
- `.env.example`
- `backend/apps/historiales/domain/`
- `backend/apps/historiales/application/`
- `frontend/src/App.jsx`

## Mensajes de commit

Ejemplos:

```text
Agrega conexión de PostgreSQL
Implementa consulta de pacientes en MongoDB
Corrige validación de historial pediátrico
Documenta variables de entorno
```
