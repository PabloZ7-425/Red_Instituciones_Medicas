# Inventario AUC-12 en la computadora de entrega

Ejecutar en PowerShell, desde la carpeta que contiene el `docker-compose.yml`
que ya usas. El backend habitual debe estar activo. Estos comandos no hacen
checkout/pull de la aplicación, no reinician servicios y no aplican migraciones:

```powershell
git fetch origin implementacion
New-Item -ItemType Directory -Force .local/auc12 | Out-Null
git show FETCH_HEAD:ops/auc12/desktop_inventory.py | docker compose exec -T backend python -B - | Out-File -Encoding utf8 .local/auc12/inventario.json
```

Verifica que Docker no muestre errores y que `inventario.json` contenga un objeto
JSON con `read_only: true`. Comparte **solo ese reporte técnico** para continuar.
No hace falta enviar `.env`, contraseñas, dumps o datos clínicos.
Si el proyecto Compose se inició con otro nombre, usa `docker compose -p NOMBRE`
en la tercera línea, con el nombre de ese mismo proyecto.

El script se toma del commit recién descargado por Git y se envía por stdin al
backend existente; **no reemplaza sus archivos**. `python -B` evita escribir
bytecode. Lee la configuración de ese contenedor, sin imprimirla. No requiere
Python, Java ni dependencias instaladas en Windows. La carpeta `.local` está
excluida de Git.

La versión 2 añade códigos SQLSTATE/errno y diagnósticos fijos para distinguir
credenciales, permisos y tablas/columnas ausentes. No publica mensajes del driver.
Si faltan tablas de identidad, conserva el proveedor y las migraciones pendientes
y marca cada consulta fallida por separado. `status: ok` en un bloque indica que
se obtuvo su inventario, no que la institución ya esté lista para operar.

El reporte contiene proveedores, cantidades agregadas, columnas operativas,
migraciones de identidad pendientes, profesionales habilitados y movimientos
abiertos de ingresos cerrados. Incluye huellas de tres archivos de código para
reconocer qué versión está instalada. Los errores se clasifican sin publicar
mensajes del driver que puedan contener credenciales o datos.

PostgreSQL/MySQL se consultan con transacciones de solo lectura. La identidad
usa transacciones de solo lectura o `PRAGMA query_only` según su proveedor.
Mongo solo ejecuta consultas/metadata; Firestore exige el emulador explícito y
solo lee proyecciones técnicas. El acceso denegado a una tabla técnica se informa
como no disponible; no se amplían privilegios automáticamente.

## Alternativa si estos archivos ya están en tu copia

```powershell
powershell -File .\ops\auc12\inventario.ps1
```

Este envoltorio genera un archivo con nombre único en `.local/auc12/` y rechaza
la ejecución si no identifica exactamente un backend del proyecto. También
acepta `-ProjectName NOMBRE`. No levanta ni detiene contenedores.

## Después del inventario

Con el reporte se identifica si tu instalación usa identidad legacy o PostgreSQL,
qué upgrades faltan, si existen vínculos profesionales pendientes y si hay datos
históricos de camas que deban revisarse. El siguiente paso será obtener respaldos
privados de **esa** instalación y restaurarlos en destinos nuevos. Las
credenciales y respaldos se mantienen en tu computadora; el inventario no cierra
AUC-12 por sí solo ni autoriza aplicar cambios sobre los originales.

El núcleo Python se prueba en el ejecutor aislado con los cuatro motores e
identidad PostgreSQL. El envoltorio PowerShell requiere ejecución en tu Docker
Desktop: no se presenta como una sesión de Windows realizada desde el entorno remoto.
