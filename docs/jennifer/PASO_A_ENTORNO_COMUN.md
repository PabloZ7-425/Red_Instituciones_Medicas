# Paso controlado al entorno común

**Actualización posterior:** el cierre B5 de Pablo `1bdd0c6`, incorporado a
Jennifer, ya documenta la ejecución de las 18 comprobaciones compartidas y las
sesiones de cuatro instituciones. El procedimiento inferior conserva el estado
anterior y sirve como receta; su pendiente fue resuelto según esa evidencia
publicada. Estado de composición y parche Vite en
[CIERRE_INTEGRACION_VITE.md](CIERRE_INTEGRACION_VITE.md).

Jennifer, 22 de octubre de 2026, America/Guatemala. A1–A5 de la rama propia están
completos. Este procedimiento describe el paso de integración aún no ejecutado
sobre el equipo/volúmenes compartidos. No es una autorización de merge ni un
registro de que ese entorno ya pasó las pruebas.

## Observación disponible

El daemon local está disponible, pero al comenzar A5 `docker ps` y `docker compose
ls` no mostraron servicios ni proyectos activos. No existe aquí una instancia
compartida identificada a la que atribuir el éxito de las pruebas A5. Las pruebas
previas y la recuperación nueva usaron exclusivamente recursos propios desechables.
No se tocaron datos/configuración compartidos ni se solicitaron credenciales reales.

El build Compose del backend usa Python 3.13; la evidencia nativa A4/A5 usa Python
3.12.14 con las dependencias del backend. Se registra esa diferencia: no se declara
aprobado el build/arranque Compose de otro equipo por pasar los tests del host.

## 1. Inventario y preparación del responsable del entorno

1. Registrar SHA de la copia, proyecto Compose, servicios/volúmenes, versión de
   motores y existencia de datos. Conservar A1 y la historia de ambas ramas.
2. Aplicar los procedimientos existentes de [identidad B2](../pablo/B2_IDENTIDAD.md),
   [hospital B3](../pablo/B3_POSTGRESQL.md), [pediatría B4](../pablo/B4_MYSQL.md) y
   [infraestructura B5](../pablo/B5_API_INTEGRACION.md). Inventario/respaldo/restore
   verificado preceden a transiciones sobre datos existentes. El init de un volumen
   nuevo no sustituye una migración de un volumen ya poblado.
3. Preparar identidad PostgreSQL y activar explícitamente IDENTITY_DB_MODE=postgres
   después del procedimiento B2. Runtime debe usar identidad_app/hospital_runtime/
   pediatria_runtime con los grants publicados, no owners ni usuarios heredados.
4. Mongo debe anunciar rs0 y ser PRIMARY. El cambio desde standalone conserva el
   volumen y requiere el respaldo verificado B5; después se provisionan las ocho
   colecciones comunes con clinical_schema.py y las dos LAB-01 con specialty_schema.py,
   ambas mediante mantenimiento explícito `--apply`. Revisar errores antes de seguir;
   no alteran validadores incompatibles ni convierten datos legados automáticamente.
5. Preparar catálogos de medicamentos en cuatro motores, camas, vacunas y tipos
   de examen; perfiles/profesionales habilitados. Usar datos autorizados del
   entorno. Los fixtures de prepare.py son únicamente para el stack A5 vacío y
   no son un procedimiento de aprovisionamiento del entorno compartido.

Si aparecen fechas, vínculos o unidades históricas ambiguas, conservarlos y
conciliarlos con evidencia. No inventar un diagnóstico, padre, fecha o unidad para
pasar un constraint. No aplicar semillas A5 sobre los volúmenes compartidos.

## 2. Comprobación de solo lectura

Desde la copia combinada del repositorio y con sus servicios preparados:

```bash
git rev-parse HEAD
docker compose config --quiet
docker compose ps --all
docker compose exec -T backend python manage.py check --database default
docker compose exec -T backend python manage.py audit_clinical_providers --require-all
docker compose run --rm --no-deps \
  --volume "$PWD/docs/jennifer:/checks:ro" \
  --volume "$PWD/db/mongo:/mongo-schema:ro" \
  backend python /checks/a5/check_startup.py \
  --backend-root /app --mongo-schema /mongo-schema/clinical_schema.py
```

El comprobador no migra, siembra, crea sesiones ni escribe historia: imprime 18
booleanos y termina 0 si se cumplen. Revisa identidad/migraciones, lecturas,
catálogos, existencia de perfiles y Mongo PRIMARY con validadores/índices comunes y
LAB-01. Un éxito no prueba por sí solo grants de escritura, credenciales de cada
cuenta ni toda la semántica clínica. Confirmar también permisos efectivos según
los scripts de roles B2/B3/B4. `health` solo acredita su función de conectividad.

Abrir la interfaz de desarrollo en http://localhost:5173 para coincidir con el
origen CORS/CSRF configurado. Verificar sesión y lecturas autorizadas con una
cuenta de prueba preparada por el responsable. Las pruebas de altas/archivo se
ejecutan en una copia desechable del entorno o con fixtures y alcance expresamente
designados; los scripts browser-real/A5 no están diseñados para datos compartidos.

Guardar SHA, versiones y resultado de comandos sin cuerpos clínicos, cookies,
credenciales ni dumps. La receta anterior se revisó; todavía no fue ejecutada
sobre el entorno común. La reproducción A5 sí pasó sus 18 comprobaciones.

## 3. Estado GitHub e integración

Consulta del 22 de octubre: main `ead042c`, Pablo `0ecf7d5`, Jennifer base A5
`ababb13`; B5 ya está incorporado en Jennifer. El ensayo merge-tree con main no
reportó conflictos. No se abrió PR ni se movieron main/Pablo.

GitHub informa main `protected:false`, protección desactivada y contexts/checks
requeridos vacíos en la respuesta de rama; rulesets visibles `[]`. El endpoint
administrativo de protección respondió 403 al conector, que no tiene permiso de
administración; no se afirma haber auditado opciones que ese endpoint no permite
ver. No se necesitan nuevos permisos para continuar el trabajo de A5.

La base `ababb13` no tiene statuses ni workflows de PR devueltos por los endpoints
consultados. No existe workflow CI versionado en esta rama. Esto significa
**ausencia de evidencia CI**, no «CI aprobado». Las pruebas locales tienen su
registro separado. Volver a observar la punta final y las reglas visibles al
preparar el PR: pueden cambiar después de esta consulta.

Con entorno común verificado y decisión de integrar de Jennifer, preparar un PR
que describa todo el alcance acumulado de la rama, incluidos A1 preservado, A3,
A4, A5 y B5 incorporado. No presentarlo como un pequeño cambio documental A5.
El borrador de contenido está en PROPUESTA_INTEGRACION.md. Mantener feature/jennifer
después del eventual merge. Sin bypass, force push ni revisión cruzada ficticia.
