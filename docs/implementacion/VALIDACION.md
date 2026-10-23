# Verificación de la rama implementacion

> **Actualización:** AUC-01 a AUC-04 corregidos; ver [cierre y pruebas](CIERRE_AUC_01_04.md). El alcance completo sigue pendiente: AUC-05 a AUC-12. Consultar [auditoría](AUDITORIA_COBERTURA.md) y [matriz actualizada](MATRIZ_COBERTURA.md).

Fuente de aplicación fijada: `7679e3c1452f95930eaa3c930476e65a8db71900`, descendiente de main `4dccf85`.
La evidencia corresponde a esa fuente sin cambios de aplicación pendientes. Este
registro documental posterior no cambia el runtime ni vuelve a contar las pruebas.

| Comprobación ejecutada | Resultado |
|---|---|
| Suite operaciones + contrato NoSQL en motores reales | **60 aprobadas, 0 fallidas, 0 omitidas** |
| Cliente, Node 22 oficial | **58 aprobadas, 0 fallidas, 0 omitidas** |
| Chromium HTTP: operación de catálogos en cuatro instituciones | **4 recorridos aprobados** |
| Chromium HTTP: flujo clínico/especialización completo en cuatro instituciones | **4 recorridos aprobados** |
| Chromium HTTP: secretaria, enfermero, laboratorista | **3 recorridos aprobados** |
| Build de producción Vite 8.3.5 | Aprobado |
| npm audit | 0 vulnerabilidades reportadas en la consulta |
| Regresión backend con test_settings, sin activar destinos dedicados anteriores | 223 descubiertas: **107 aprobadas, 116 omitidas** |
| git diff --check | Aprobado |

No sumar las 107 a las 60 como si fueran todas pruebas diferentes. La suite de 60
incluye 11 pruebas operativas/de permisos y 49 del contrato NoSQL; el servidor
real se prueba después desde Chromium. Los once recorridos HTTP no son mocks.
Una ejecución separada de los cuatro recorridos DEMO también pasó; no se presenta
como persistencia real ni como cuatro nuevas instituciones.

Reproducción: `verify_native.py --run --browser`, según README. Ejecución final
privada en `/workspace/work/ops-certified-03`; tests.log, browser.log,
clinical-admin.log y logs por rol, más report.json. Estos archivos y su identidad
SQLite sintética están fuera de Git. El runner retiró sus contenedores/JVM y
servidores dedicados; no montó volúmenes compartidos.

Los recorridos operativos prueban navegación, búsqueda, alta/edición de catálogo,
editor único, fecha automática y vínculo de profesional de una cuenta existente.
Los escenarios nativos cubren hospitalización/traslado, signos, cirugía/equipo,
stock/administración, paciente/tutor, vacunas/crecimiento, exámenes/resultados,
pólizas/cobertura/autorización/reclamación y factura/detalle/pago. También rechazo
de referencias de otro paciente, duplicados, stock insuficiente, pago mayor al
saldo, carrera entre dos pagos y rollback de concepto/totales.

La identidad de este ensayo es desechable; no se vuelve a certificar aquí el
cutover B2 PostgreSQL ni un despliegue productivo. El mantenimiento de esquema y
permisos del entorno compartido no fue ejecutado. La cobertura de tablas técnicas,
legado y límites administrativos está descrita en COBERTURA.md. No se afirma una
calificación docente ni una garantía universal de reglas clínicas/aseguradoras.
