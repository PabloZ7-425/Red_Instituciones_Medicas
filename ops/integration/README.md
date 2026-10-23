# Ensayo aislado de la composición A/B

Ejecutar desde la raíz, en feature/pablo. No monta volúmenes clínicos compartidos
ni publica puertos del laboratorio. El repositorio se monta solo lectura y los
datos se crean en volúmenes del proyecto Docker `pablo-validation`. El socket
Docker se usa para las guardas y parada de los servicios desechables que exigen
las pruebas publicadas de Jennifer; no se usa para administrar el stack común.

Requiere imágenes locales `red_instituciones_medicas-backend:latest` y
`red_instituciones_medicas-firestore:latest`, construidas con el Compose raíz.
Copiar el JAR oficial del emulador existente a `.local/validation/firestore.jar`.
Crear `.local/validation/database.env` con dos claves aleatorias de prueba:
`PABLO_TEST_POSTGRES_PASSWORD` y `PABLO_TEST_MYSQL_PASSWORD`. No usar claves del
entorno compartido. Crear el directorio vacío `work` para el montaje anidado.

```powershell
docker compose --env-file .local/validation/database.env -p pablo-validation -f ops/integration/compose.yml build runner
docker compose --env-file .local/validation/database.env -p pablo-validation -f ops/integration/compose.yml up -d runner postgres mysql mongo mongo-a3 mongo-rs0
docker compose --env-file .local/validation/database.env -p pablo-validation -f ops/integration/compose.yml exec -T runner python ops/integration/run.py configure
docker compose --env-file .local/validation/database.env -p pablo-validation -f ops/integration/compose.yml exec -T runner python ops/integration/run.py validate
```

configure exige destino nuevo `work/a5-runtime`, fija los dos refs a HEAD y usa
los scripts A5 sin editarlos. No sobrescribe una ejecución anterior. validate
prepara bases vacías, ejecuta los contratos/HTTP SQL y NoSQL con los flags reales,
pruebas cliente, build, cuatro instituciones en Chromium y tres recorridos por
rol, más HTTP/nativo común y especializado. La recuperación fría se ejecuta
separada: no se cuenta como aprobada mediante skips de la suite principal.

```powershell
docker compose --env-file .local/validation/database.env -p pablo-validation -f ops/integration/compose.yml stop mongo
docker compose --env-file .local/validation/database.env -p pablo-validation -f ops/integration/compose.yml --profile recovery up -d recovery-source recovery-target
docker compose --env-file .local/validation/database.env -p pablo-validation -f ops/integration/compose.yml exec -T runner python ops/integration/run.py recovery
```

La suite de recuperación detiene sus orígenes dedicados, restaura en otro servidor
y JVM y verifica sin seed. El ensayo adicional incluye las nuevas colecciones de
resultados/procedimientos, tipos numérico/booleano/texto, relaciones y escrituras
posteriores a restauración. Nunca ejecutar estas guardas cambiando sus nombres
para hacerlas coincidir con un servicio compartido.

Para validar únicamente la suite A5 ampliada de `bb2130c` desde el checkout
actual, usar `python ops/integration/run.py recovery-current` en el runner,
con `recovery-source` y `recovery-target` activos y el Mongo A5 detenido. Fija
HEAD en otra copia nueva `work/a5-final-<UUID>/work/a5-runtime` mediante el configurador A5;
sus respaldos quedan fuera de esa copia para cumplir las guardas originales.
No modifica la copia fijada de la ejecución completa ni sus respaldos adicionales.

Al finalizar, detener este proyecto con el mismo `-p` y archivo; conservar los
volúmenes/logs como evidencia hasta revisarlos. No usar `down -v` sobre el Compose
raíz. Los nombres `jennifer-a5-*` y `jennifer-recovery-*` corresponden a guardas
existentes de las fixtures; deben estar libres antes del ensayo y todos los
contenedores creados pertenecen a `pablo-validation`.
