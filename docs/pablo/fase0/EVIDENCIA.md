# Evidencia local B-C0-T1

Fecha: 2026-10-20, America/Guatemala. Equipo de Pablo, Windows / PowerShell.
Base sincronizada: `e9b2efafa51ca897765d9055f39be219da5a41bb`.
Rama: `contract/pablo-c0-fase0`. PR-02 es el identificador del plan, no el número GitHub.

## Alcance entregado

- [CONTRATOS.md](CONTRATOS.md): diez operaciones, DTOs, permisos, errores,
  paginación y ocho firmas de repositorio propuestas.
- [DECISIONES.md](DECISIONES.md): D0-01..10, ADR-ORM-01, matriz de roles,
  migración de identidad como diseño y hallazgos SQL para C2.
- Ejemplos JSON sintéticos válidos/negativos por operación y seis pruebas nuevas
  de consistencia bajo `backend/apps/historiales/`.

No se cambiaron puertos, rutas activas, configuración, modelos SQL, frontend,
adaptadores NoSQL ni documentos compartidos. No se ejecutaron migraciones ni
se alteraron registros clínicos, usuarios o volúmenes.

## Verificaciones ejecutadas antes del commit y PR

Docker no figuraba en PATH del proceso restringido. Se localizó el ejecutable
de Docker Desktop y se ejecutó con acceso al servicio del host:

```powershell
$dockerProyecto = "$env:LOCALAPPDATA\Programs\DockerDesktop\resources\bin\docker.exe"
& $dockerProyecto compose config -q
& $dockerProyecto compose ps -a
& $dockerProyecto compose exec -T backend python manage.py check
& $dockerProyecto compose exec -T backend python manage.py test apps.historiales --verbosity 2
& $dockerProyecto compose exec -T frontend npm run build
curl.exe --max-time 5 -fsS http://localhost:8000/api/health/
curl.exe --max-time 10 -fsS http://localhost:8000/api/health/databases/
git diff --check
```

| Verificación | Resultado observado |
|---|---|
| Git | 2.56.0.windows.2; main actualizado antes de crear rama |
| Docker cliente / servidor | 29.8.0 / 29.8.0 |
| Docker Compose | 5.5.1 |
| compose config -q | Salida 0; sin imprimir configuración ni secretos |
| compose ps -a | Siete servicios Up; backend, PostgreSQL, MySQL, Mongo y Firestore healthy |
| .env | Existe localmente, ignorado y no versionado; no se imprimió ni modificó su contenido |
| Django check | Salida 0: System check identified no issues (0 silenced) |
| Django tests | Salida 0: Ran 7 tests, OK; no se utilizó base default |
| Build React | Salida 0: Vite 8.3.2, 19 módulos transformados |
| /api/health/ | Salida 0; status ok, service django-backend |
| /api/health/databases/ | Salida 0; connected true para hospital, pediatrico, laboratorio y odontologica |
| Ejemplos JSON | python -m json.tool, salida 0 |
| git diff --check | Sin errores; repetir sobre el índice antes de commit |

En la primera ejecución, una prueba nueva trató los mensajes de error de un
campo fecha como si fueran fechas de DTO. Se corrigió el recorrido para distinguir
`error.fields`, se repitió la suite completa y pasaron las siete pruebas.

Las seis pruebas nuevas comprueban cobertura de operaciones, relaciones del
historial, tipos de IDs/fechas y ausencia de secretos en respuestas, formato de
errores, listado/archivo e institución conocida. No llaman a endpoints propuestos
ni acreditan seguridad, transacciones, integridad SQL o contratos NoSQL.

## Gate F0: estado real

Las once casillas globales permanecen abiertas hasta comprobación en ambos
equipos y ratificación A↔B. La evidencia de este equipo no certifica el de Jennifer.

| Gate | Evidencia local / pendiente global |
|---|---|
| G0-01 | Base local sincronizada tras PR de documentación; falta SHA confirmado por Jennifer |
| G0-02 | .env local ignorado/no versionado; falta confirmación A y validación de valores seguros por cada responsable |
| G0-03 | Configuración Compose local válida; falta A |
| G0-04 | Servicios locales activos; falta A |
| G0-05 | Cuatro conexiones locales positivas; falta A |
| G0-06 | Check y siete pruebas locales pasan; falta A |
| G0-07 | Build local pasa; falta A |
| G0-08 | Propuesta D0-01..05 y ADR-ORM-01 preparada; sin ratificación explícita |
| G0-09 | Propuestas/solicitudes D0-06..10 preparadas; sin ratificación explícita |
| G0-10 | Contratos candidatos con ejemplos; pendiente revisión de A y resolución de observaciones |
| G0-11 | Documentación inicial integrada; esta rama reserva solo archivos nuevos B, siguiente pareja de tareas por confirmar |

Siguiente paso: revisión explícita A↔B de contratos y decisiones, registro del
SHA aprobado y evidencia del equipo A. Después cerrar F0 y preparar C1 auth.
No iniciar migraciones ni sustituir firmas del puerto a partir de este borrador.

## Revisión para integrar como punto de partida

Pablo solicitó integrar esta propuesta en main como base compartida. Esta
integración no ratifica contratos ni cierra F0. En la revisión se detectaron
acentos sustituidos por `?` en los ejemplos JSON, generados al pasarlos por la
codificación de la consola. Se corrigieron y se agregó una prueba de regresión
UTF-8. Resultado actualizado: **8 pruebas Django, OK**, check sin incidencias,
Compose config válido, endpoint de salud correcto y cuatro motores conectados.
El build React aprobado de la entrega inicial sigue vigente: la corrección solo
afecta los textos de ejemplos y su prueba. Sin cambios de frontend o API activa.
