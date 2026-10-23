# Cierre de los cuatro bloqueos prioritarios

Seguimiento de la auditoría de la rama `implementacion`. Este cierre comprende
**AUC-01, AUC-02, AUC-03 y AUC-04**; **AUC-05..12 siguen abiertos**. No certifica
el 100% del alcance de las cuatro instituciones ni autoriza un merge o despliegue.

## Correcciones

| Hallazgo | Comportamiento corregido | Evidencia dirigida |
|---|---|---|
| AUC-01 | Una cama ocupada rechaza el traslado con conflicto de dominio, sin error interno. Solo un traslado concurrente puede ocupar el mismo destino. | Regresión aislada; PostgreSQL real con cama ocupada y dos traslados simultáneos. |
| AUC-02 | El alta cierra el ingreso y sus movimientos abiertos en la misma transacción. Rechaza fechas anteriores a sus movimientos; repetir la misma alta es idempotente. | PostgreSQL real: traslado→alta, cronología, repetición y fallo inyectado que revierte ambos cambios. |
| AUC-03 | Diagnósticos y tratamientos pueden proceder de consulta o de ingreso abierto. Prescripciones permite alta desde operaciones para admin/médico y conduce a despacho; se conserva el control clínico de profesional, paciente y medicamento. | PostgreSQL real: diagnóstico de ingreso→tratamiento→receta→despacho, descuento de stock, filtro por paciente y rechazo de receta posterior al alta. Chromium: recorrido completo sin consulta ficticia. |
| AUC-04 | Autorización y factura deben corresponder a la misma consulta y póliza. Las reclamaciones activas reservan saldo acumulado de factura y autorización, incluso entre facturas. La edición excluye su propio importe; una reclamación rechazada/anulada libera su reserva. | MySQL real: consultas incompatibles, dos reclamos simultáneos, edición sin doble conteo, autorización compartida entre facturas y liberación de reserva. |

Las cuatro pruebas aisladas se ejecutaron antes de corregir el código y fallaron
reproduciendo los defectos. Ahora pasan. Los escenarios SQL se ejecutan únicamente
en `hospital_auc` y `pediatrico_auc`, bases nuevas del ejecutor desechable, para no
contaminar los escenarios anteriores ni tocar destinos compartidos.

## Verificación

Fuente de aplicación y pruebas: `a65fabd0be60ee0146865348e8918c7b0ed79318`. Las ejecuciones se
realizaron sobre el árbol de trabajo luego guardado en ese commit. La ejecución
HTTP precedió únicamente a la ampliación de las aserciones de saldo entre facturas
y al ajuste mínimo de permisos del runtime base; la suite nativa de 68 se repitió
después de ambos cambios y aprobó. La aplicación React/API comprobada por navegador
no cambió entre ambas ejecuciones.


- Backend: **68 aprobadas, 0 fallidas, 0 omitidas**, en PostgreSQL 16, MySQL 8.4,
  MongoDB 7 y emulador Firestore. Incluye cuatro regresiones aisladas y cuatro
  escenarios SQL nuevos, además de las 60 pruebas anteriores.
- Cliente en Node 22: **58 aprobadas, 0 fallidas, 0 omitidas**.
- Chromium con React/API/motores reales: **11 recorridos aprobados** (4 operativos,
  4 clínicos, 3 de permisos). El operativo hospitalario ahora incluye el recorrido
  de ingreso hasta prescripción, despacho y alta.
- Build de producción aprobado.
- Regresión backend sin activar destinos dedicados: **231 descubiertas,
  111 aprobadas y 120 omitidas**. Las omitidas no cuentan como aprobadas y estas
  cifras no se suman a las 68 como si todas fueran pruebas diferentes.

Reproducción con dependencias backend, Docker, Chromium y emulador disponibles:

```bash
python docs/implementacion/verify_native.py --run --browser \
  --work /ruta/nueva/fuera/del/repositorio --jar /ruta/firestore.jar
cd frontend
npm test
```

El ejecutor crea y elimina solo sus contenedores, bases y procesos locales.
Los registros privados y credenciales efímeras no forman parte del repositorio.
No se ejecutó CI remoto ni una actualización de datos compartidos.

## Matriz y límites de este cierre

La matriz conserva sus 95 destinos declarados. Tras retirar exclusivamente estos
cuatro hallazgos: **40 B, 38 P y 17 T**. B sigue significando función base con la
evidencia indicada; no equivale a aceptación total ni porcentaje de terminación.
El dictamen y el JSON de la auditoría original se conservan como antecedente.

El alta corrige las nuevas operaciones; no repara retroactivamente movimientos
abiertos de ingresos que ya estaban cerrados antes de esta versión. Esa revisión
de datos históricos debe ensayarse con el inventario y copia de AUC-12. No se
crean consultas ficticias ni se modifica el DTO común del historial para simular
atenciones ambulatorias: el seguimiento de hospitalización se consulta desde
operaciones con el contexto del paciente.

En instalaciones con permisos anteriores, el runtime hospitalario necesita
SELECT y UPDATE sobre `movimiento_cama`. La concesión está incluida en
`db/postgres/runtime_role.sql`; `operations_runtime.sql` ya la incluía. Aplicarla
forma parte de la preparación del entorno, pendiente de AUC-12; la aplicación
no ejecuta DDL ni concede permisos al atender peticiones.

Siguiente bloque: cronología y estados/facturación (AUC-05..07), coherencia de
profesionales (AUC-10), luego cobertura de permisos y flujo guiado (AUC-08..09),
medición de eficiencia (AUC-11) y ensayo de actualización existente (AUC-12).
