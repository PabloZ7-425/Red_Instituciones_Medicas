# Viabilidad de integración a main

Actualización Jennifer, 22 de octubre de 2026. Este documento informa una decisión
técnica; no autoriza ejecutar merge ni cambia protecciones reales de GitHub.

**A4 está cerrado y B5 ya está incorporado a feature/jennifer** mediante merge
`a1747cd`, con A1 preservado. Ya no existe la dependencia de incorporar B5 a esta
rama para disponer de rutas. Las especializaciones reales están implementadas y
probadas; evidencia en [A4_CIERRE_REAL.md](A4_CIERRE_REAL.md). No se ha integrado
main: falta comprobar la preparación/actualización del entorno compartido y los
checks/protecciones GitHub sobre la punta final antes de recomendarlo.

## Evidencia y dependencias concretas

| Punto | Estado |
|---|---|
| A1/A2 y reversión anterior | Preservados en Jennifer; A1 no está restaurado en main. La sincronización d656044 ya conservó explícitamente A1 en la rama propia. |
| Ocho operaciones y catálogo NoSQL | A3 probado; 49 pruebas registradas en su entrega. |
| Flujo común React con cuatro motores reales | A5: cuatro recorridos Chromium, ocho pruebas HTTP/nativas; B5 0ecf7d5 + A4 9ff890c, en copia aislada. |
| Archivo, aislamiento y permisos | Evidencia nativa A3 y HTTP A5; no son solo capturas o mocks. |
| Recuperación clínica Mongo/Firestore | Diez pruebas nuevas: origen apagado, destino nuevo sin seed, historia/tipos/metadata y continuidad comprobados. |
| Composición Git Jennifer + B5 | Incorporación real de B5 en Jennifer, sin conflictos; Pablo y main no se modificaron. |
| Especializaciones institucionales | A4 cerrado: siete recorridos HTTP de navegador, 14 pruebas HTTP/nativas y 55 cliente; contrato aditivo y proveedores reales. |
| Primer arranque/actualización del entorno común | Requiere B5/replica set y mantenimiento explícito Mongo v2, catálogos y roles. No se debe presentar un Mongo sin sus colecciones como listo: A3 devuelve 503. Seguir A3 y procedimientos B2–B5; no reaplicar DDL sobre datos sin inventario/respaldo. |
| Checks/protecciones de GitHub y punta final | Comprobar en la integración concreta; no se inventan checks aprobados ni aprobaciones de otra persona. |

Se repitió una preparación desde bases vacías con B5 `0ecf7d5` y Jennifer
`1fac230`: 15 comprobaciones de arranque, cuatro recorridos Chromium y ocho
pruebas HTTP/nativas aprobadas. Tres fallos inducidos solo en el Mongo temporal
fueron detectados por el comprobador de solo lectura. Procedimiento y diferencia
con el entorno compartido en [ARRANQUE_FLUJO_COMUN.md](ARRANQUE_FLUJO_COMUN.md).
La receta Compose fue revisada, no ejecutada en datos compartidos; esa validación
real y las protecciones de GitHub siguen pendientes para recomendar el merge.

Main observado: ead042c. B5 observado: 0ecf7d5. Las pruebas previas corresponden a los
SHAs de sus documentos. Cualquier cambio posterior que afecte esos flujos requiere
validar lo afectado antes de recomendar el merge final. El estado limpio de Git o
una conexión healthy no reemplaza esa comprobación.

No se pide revisión cruzada obligatoria ni se restaura el antiguo gate F0. La
restricción es de composición/arranque, no un permiso pendiente de Pablo. La rama
feature/pablo y su PR #16 se mantienen intactos durante el trabajo de Jennifer.

## Integración técnica y entrega académica son alcances distintos

La documentación final conciliada y cualquier migración de
históricos requerida siguen pendientes para la entrega académica completa. No se convierten
en una prohibición general de integrar módulos terminados. Un main con el flujo
común completo puede ser un incremento válido, siempre que se explicite ese alcance
y que la composición y preparación real del entorno estén verificadas.

Cuando recomiende integrar indicaré los SHAs, el alcance concreto, las pruebas y el
procedimiento de preparación/recuperación. Hasta entonces continúo publicando solo
en feature/jennifer, sin PR ni merge automático a main.
