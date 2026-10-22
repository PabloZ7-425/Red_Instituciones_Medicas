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
Jennifer autorizó expresamente retirar esa integración. Se publicó el commit
correctivo `d2901ae` en main mediante fast-forward, sin force push ni reescritura.
A1 ya no está en el árbol actual de main; el merge histórico #11 permanece como
antecedente. A2 nunca se publicó en main.

La reversión se preparó con `git revert -m 1` en un checkout separado y sin rama
de desarrollo nueva. Antes de publicarla se verificó que main seguía en a044c76,
que el commit correctivo tenía ese padre y que restauraba exactamente el árbol de
2eb7470b8d3dffef1162953ab1e44cb67dadfa18. Afectó exclusivamente los once archivos
de A1 bajo db/firebase, sin alterar archivos de Pablo ni el trabajo A2.
`git diff --check` no informó errores. No se reejecutaron suites de aplicación:
la verificación fue de equivalencia exacta con el estado previo a la integración.

**feature/jennifer conserva íntegramente A1 y A2.** No se fusionó main revertido
en esta rama, no se eliminó código de Jennifer y no se modificó feature/pablo.
El único cambio autorizado sobre main fue esta corrección; no autoriza futuras
integraciones automáticas de A1/A2.

## Precaución para una integración futura

Un revert conserva el merge original en el historial. Ahora que se retiró
A1 de main, fusionar feature/jennifer otra vez no garantiza restaurar A1: Git ya
considerará sus commits integrados. Tampoco sincronizar main revertido en esta rama
sin preservar/restaurar A1, porque podría retirar sus archivos aquí.

Cuando se autorice integrar, preparar explícitamente la restauración de A1
(revertir la reversión, sin reset ni force push), conservar A2 y comprobar el diff
completo contra main y las pruebas afectadas. No ejecutar ese paso automáticamente.

## Actualización 22 de octubre: sincronización segura y A3

Se incorporó main `ead042c` mediante el merge `d656044` en feature/jennifer.
Antes de confirmar se restauró explícitamente db/firebase desde la punta propia
`7bacf22`, comprobando igualdad exacta de sus archivos y de React con la rama
publicada. A1/A2 y los formularios existentes permanecen íntegros. No se restauró
A1 sobre main ni se abrió PR. El SQLite local original se conserva fuera del índice.

La rama ahora dispone del núcleo B1–B4 de Pablo. A3 implementa los ocho métodos y
catálogo de ambos motores sobre modelo v2, con evidencia y límites en
[A3_NOSQL.md](A3_NOSQL.md). Integración B5/API, históricos y E2E siguen pendientes.
Siguiente trabajo: completar A4. La instrucción de publicar únicamente en la rama
propia, sin PR ni merge a main, continúa vigente.
