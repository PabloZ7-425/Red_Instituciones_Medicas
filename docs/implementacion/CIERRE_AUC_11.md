# AUC-11: medición de eficiencia operativa

23 de octubre de 2026, America/Guatemala. Rama `implementacion`.

Se ejecutaron los seis recorridos acordados con Chromium, React, API y motores
reales locales. Cada uno se guardó y se verificó por API en dos modos de la misma
versión: **manual controlado** y **asistido**. En el control se vacían los
autocompletados observados y se vuelven a introducir; el modo asistido los conserva.

**Esta comparación no representa la interfaz histórica ni mide productividad
o tiempo humano.** Mide acciones lógicas automatizadas y campos ajustados por
el guion, con límites iguales en ambos modos. No se publican porcentajes de velocidad.

| Recorrido | Acciones manual / asistido | Campos manuales / asistido |
|---|---:|---:|
| Atención | 4 / 3 | 2 / 1 |
| Vacuna | 6 / 5 | 3 / 2 |
| Ingreso | 6 / 5 | 3 / 2 |
| Traslado | 9 / 8 | 4 / 3 |
| Resultado | 8 / 7 | 5 / 4 |
| Pago | 10 / 7 | 5 / 2 |
| **Total** | **43 / 35** | **22 / 14** |

Se completaron **12 ejecuciones persistidas**, con cero errores visibles al guardar
y cero retrocesos en los guiones. El tiempo se registra como `null`: no se midió.
Estos ceros describen los recorridos automatizados exitosos; no son tasas de error
de usuarios reales ni ensayos de recuperación.

## Límite y reproducción

La medición empieza con paciente y prerrequisitos disponibles. Incluye abrir la
tarea, ajustar campos y guardar. Excluye login, búsqueda/alta inicial del paciente,
catálogos, preparación de factura/ingreso y peticiones de verificación. Una acción
es pulsar un botón/tarea o ajustar un campo; no equivale a una tecla ni a un clic
físico humano. Los valores generados/fechas corresponden al contexto de cada
ejecución; la tarea y los datos clínicos sintéticos tienen las mismas condiciones.

Las mejoras observadas proceden de fecha/hora precargadas y, en pago, referencia
generada y saldo sugerido. No se contabiliza como ahorro una supuesta eliminación
de cálculos manuales que esta comparación no ejecutó. Las decisiones clínicas
se introducen en ambos modos.

`frontend/tests/browser-efficiency.mjs` conserva los eventos por recorrido y
comprueba tanto el guardado real como la reducción de campos/acciones. El
ejecutor común activa la medición con `--browser --efficiency`; combinar
`--upgrade` la ejecuta sobre las copias restauradas.

[Datos y eventos medidos](AUC_11_MEDICION.json). La medición solicitada queda
documentada bajo este método controlado; la aceptación y el tiempo con usuarios
reales siguen siendo una evaluación distinta.
