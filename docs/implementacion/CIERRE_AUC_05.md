# AUC-05: cronología en ediciones parciales

La edición operativa valida los intervalos después de combinar el PATCH con el
registro leído y comprobar su versión, dentro de la transacción y antes de las
escrituras. Se conserva la validación de campos de entrada y permisos.

Los intervalos cubiertos son inicio/fin, solicitud/respuesta, envío/resolución y
fecha-hora de inicio/fin, en los recursos que declaran esos campos. Cambiar un
solo extremo no permite invertir el intervalo existente. Se permiten extremos
iguales y fechas opcionales nulas. Las fechas con hora se comparan como instantes,
incluyendo zona horaria y fracciones de segundo; las fechas civiles como fechas.

## Verificación

`apps.operaciones.test_chronology`: **6 pruebas aprobadas, 0 fallidas**. Incluyen
todos los intervalos declarados, alta inválida, PATCH de un extremo o ambos,
extremos iguales, valores opcionales nulos, fechas inválidas, diferencias de zona
horaria y precisión, valores SQL serializados y rechazo de una versión obsoleta.
Los PATCH inválidos no alcanzan ninguna escritura; los válidos conservan el
extremo no editado y pasan por la actualización del repositorio.

Ejecución local en un entorno Python aislado, con la configuración de bases
reemplazada en memoria por SQLite `:memory:` solo para el proceso de pruebas.
No se crean bases para esta suite ni se conectan motores clínicos. No se afirma
haber ejecutado integración PostgreSQL/MySQL/MongoDB/Firestore ni despliegue.

Reproducción desde la raíz con las dependencias backend instaladas:

```powershell
python backend/manage.py test apps.operaciones.test_chronology --verbosity 2
```

La sonda histórica `auditoria_comprobaciones.py` se actualiza para observar la
validación del estado combinado. Los JSON de ejecuciones anteriores se conservan
como evidencia histórica. La fila de pólizas permanece parcial por AUC-08.

AUC-05 queda corregida con regresión aislada. AUC-06 a AUC-09 son el siguiente
bloque solicitado; AUC-10 a AUC-12 permanecen fuera de este cierre.
