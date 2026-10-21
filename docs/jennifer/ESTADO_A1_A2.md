# A1 y A2 — conservación en la rama de Jennifer

Actualizado el 20 de octubre de 2026 (America/Guatemala).

## Instrucción vigente

Todo el desarrollo de Jennifer debe permanecer en **feature/jennifer**. No abrir
ni fusionar PR ni publicar cambios sobre main sin autorización expresa de Jennifer.
Esta instrucción sustituye para esta entrega la integración autónoma de la guía.

## Trabajo preservado

| Módulo | Commit de implementación | Rutas | Documentación |
|---|---|---|---|
| A1 Firestore | 7c4d282a86e33e09821c7a2489327790ae34c418 | db/firebase/** | MODELO.md, README.md, VALIDACION.md dentro de db/firebase |
| A2 MongoDB | f13187531ee8187b73185aed5206077c8b2f0679 | db/mongo/**; mongo_adapter.py; test_mongo_nosql.py | MODELO.md, README.md, VALIDACION_A2.md dentro de db/mongo |

Ambos commits son ancestros de feature/jennifer y sus archivos están presentes.
La revisión anterior registró 26 pruebas Firestore y recuperación; A2 registró
12 pruebas del modelo y 3 de conexión. Son resultados de esas implementaciones,
no pruebas reejecutadas durante esta documentación.

## Incidente de integración A1

El PR #11 ya se fusionó mediante a044c76ea9bb4d761110f8dcc67a389a4f9ddce9.
Por tanto, A1 **también está actualmente en main**; A2 no está en main. Registrar
los trabajos en esta rama no retira por sí mismo lo previamente fusionado.

Se preparó una reversión local del merge con `git revert -m 1`, en un checkout
separado y sin rama de desarrollo nueva. No se publicó esa reversión ni se cambió
main. La comparación de árboles comprobó que restaura exactamente el primer padre
2eb7470b8d3dffef1162953ab1e44cb67dadfa18: afecta exclusivamente los once archivos
de A1 bajo db/firebase, sin alterar archivos de Pablo ni el trabajo A2.
El parche de reversión es un artefacto fuera del repositorio; no aplicar dentro de
feature/jennifer, pues allí se quiere conservar A1.

Retirar A1 de main requiere autorizar esa modificación correctiva de main, dado
que la instrucción anterior prohíbe modificarla. Hasta entonces permanece pendiente.
Antes de aplicar cualquier reversión se debe volver a consultar origin/main; si
Pablo avanzó o ya corrigió el merge, reevaluar el diff y no aplicar ciegamente.

## Precaución para una integración futura

Un revert conserva el merge original en el historial. Si posteriormente se retira
A1 de main, fusionar feature/jennifer otra vez no garantiza restaurar A1: Git ya
considerará sus commits integrados. Tampoco sincronizar main revertido en esta rama
sin preservar/restaurar A1, porque podría retirar sus archivos aquí.

Cuando se autorice integrar, preparar explícitamente la restauración de A1
(revertir la reversión, sin reset ni force push), conservar A2 y comprobar el diff
completo contra main y las pruebas afectadas. No ejecutar ese paso automáticamente.
