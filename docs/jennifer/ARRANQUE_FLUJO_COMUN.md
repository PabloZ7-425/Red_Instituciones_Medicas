# Preparación y comprobación del flujo común

Jennifer, 22 de octubre de 2026. Alcance: A3/A4 con B5, sin especializaciones.

## Resultado comprobado

Se preparó de cero una nueva copia aislada con B5 `0ecf7d5` y Jennifer `1fac230`.
Las tres puntas remotas seguían en main `ead042c`, Pablo `0ecf7d5` y Jennifer
`1fac230` al comenzar. No se modificaron fuentes centrales, ramas de Pablo/main,
PR #16 ni datos compartidos. La reproducción empleó los scripts A5 publicados,
bases nuevas, cuentas/catálogos sintéticos y roles SQL limitados. No hubo que
modificar el backend de Pablo para ejecutar el flujo común.

La nueva comprobación `a5/check_startup.py` terminó con **15 comprobaciones OK**:
identidad PostgreSQL y migraciones aplicadas; lectura clínica, catálogo no vacío y
perfil clínico con profesional habilitado por institución; Mongo PRIMARY en
replica set y ocho colecciones v2 con validadores e índices esperados.

Se provocaron y restauraron tres fallos en el Mongo desechable: ausencia de
`clinico_citas`, `validationAction=warn` y catálogo vacío. Cada uno produjo código
1 y las comprobaciones negativas correspondientes. El estado correcto volvió a
producir código 0. El comprobador solo lee: las alteraciones fueron fixtures del
ensayo aislado, no acciones de reparación del comprobador.

Después se repitieron los cuatro recorridos Chromium reales y las ocho pruebas
HTTP/nativas de A5, todos aprobados. Incluyen autenticación/CSRF, cadena clínica,
archivo, duplicados, roles, aislamiento y lectura nativa de la historia.

## Diferencia entre capacidad de infraestructura y preparación clínica

El Compose B5 convierte/inicia Mongo como `rs0`, espera PRIMARY y aporta la base
técnica de identidad. Eso no crea automáticamente las colecciones `clinico_*`
de A3 ni carga medicamentos o cuentas clínicas. `audit_clinical_providers`
comprueba las interfaces de los adaptadores; no sustituye estas verificaciones.

Antes de publicar una combinación común, ejecutar los procedimientos centrales
B2/B3/B4/B5 para inventario, respaldo, roles, migraciones y activación explícita
de `IDENTITY_DB_MODE=postgres`. No ejecutar migraciones ni semillas sobre datos
existentes sin seguir esos procedimientos. En particular:

1. Combinar las fuentes de B5 y Jennifer conservando Firestore A1. Jennifer sola
   sobre main carece de las rutas clínicas B5.
2. Preparar los motores con sus procedimientos y permisos runtime. En un volumen
   Mongo existente, el respaldo verificado precede al cambio de topología.
3. Provisionar explícitamente Mongo v2 con `db/mongo/clinical_schema.py --apply`
   y `MONGO_CLINICAL_SETUP_URI` al destino elegido. Es una acción de mantenimiento,
   no una función del comprobador. Rechaza validadores incompatibles; puede haber
   preparación parcial si falla, por lo que hay que revisar el resultado. No
   migra históricos ni carga el catálogo.
4. Preparar medicamentos autorizados en los cuatro motores, perfiles y vínculos
   profesionales mediante los procedimientos correspondientes. Los datos A5 son
   exclusivos de las bases desechables; no son una semilla para el entorno común.
5. Ejecutar auditoría de puertos, comprobación de arranque y validación HTTP/UI
   sobre la combinación final. Revisar los checks/protecciones reales de GitHub.

No se aplicaron estos pasos al entorno compartido durante este trabajo. La
preparación real de ese entorno sigue siendo condición para recomendar su merge.

## Ejecutar el comprobador sin modificar datos

En una copia A5 preparada, con el Python de las dependencias del backend:

```bash
python docs/jennifer/a5/check_startup.py --runtime /ruta/work/a5-runtime
```

Para una futura combinación B5 + Jennifer servida mediante Compose, desde su raíz:

```bash
docker compose run --rm --no-deps \
  --volume "$PWD/docs/jennifer:/checks:ro" \
  --volume "$PWD/db/mongo:/mongo-schema:ro" \
  backend python /checks/a5/check_startup.py \
  --backend-root /app --mongo-schema /mongo-schema/clinical_schema.py
```

El comando usa las variables/red del servicio backend, monta los archivos propios
como solo lectura y no inicia dependencias. Requiere servicios ya preparados y
accesibles. El comprobador termina con código **0** si sus condiciones se cumplen
y **1** si alguna falta. Imprime únicamente nombres de comprobaciones y booleanos;
no muestra pacientes, medicamentos, perfiles, excepciones de drivers o secretos.

El comando A5 fue ejecutado; la receta Compose se revisó contra su configuración,
pero no se lanzó sobre el stack compartido. No confundir esa revisión con una
certificación del arranque de Compose.

## Límites

Un resultado favorable no prueba permisos de escritura, transacciones concurrentes,
login real, que todas las cuentas estén bien vinculadas, ni que cada medicamento
sea clínicamente correcto. La consulta de perfiles solo comprueba que existe al
menos una cuenta activa admin/médico con profesional habilitado de su institución;
no revela la cuenta ni valida sus credenciales. Las pruebas HTTP/A3 y el ensayo
del navegador aportan evidencia separada. No se crean sesiones ni se escribe
historia durante el comprobador. No certifica especializaciones, producción,
Firebase real, disponibilidad continua ni recuperación de identidad SQL.

La comparación con el documento maestro debe leer sus filas de estado como
históricas: la evidencia posterior A3/A4/A5 demuestra avances que esas filas aún
no reflejan. El cierre académico todavía necesita especializaciones y conciliación
de documentación central.
