# Composición final y actualización de Vite

Jennifer, 22 de octubre de 2026 (America/Guatemala).

## Cambio

Se incorporó `origin/feature/pablo` fijado en
`1bdd0c6e5507ca6718e3a28a1ef90c3bd3f65684` mediante fast-forward de
feature/jennifer desde `bb2130c`. Los cuatro commits ya contienen A1–A5 y la
preparación/integración B5; no hubo conflictos ni edición manual de fuentes B.
Main y feature/pablo no se modificaron.

Vite pasa de 8.3.2 a **8.3.5**, versión correctiva indicada por el informe B5
([aviso del fabricante](https://github.com/vitejs/vite/security/advisories/GHSA-rq7h-c2jc-7f22)).
Se añade frontend/package-lock.json para fijar las dependencias transitivas y
permitir `npm ci`. No se ejecutó audit fix --force. React y plugin-react mantienen
sus versiones. No cambia código clínico, API, contratos, esquema ni datos.

## Verificación ejecutada en Jennifer

- Instalación nueva y reinstalación mediante `npm ci`, con Node 24.19.0/npm 11.9.0.
- `npm audit --json`: **0 vulnerabilidades** reportadas para el árbol completo.
  Resultado del registro consultado en esta fecha, no garantía permanente.
- Node 22, imagen node:22-bookworm-slim, checkout completo montado de solo lectura:
  `node --test frontend/tests/*.test.js`: **55 aprobadas, 0 fallidas, 0 omitidas**.
- `VITE_CLINICAL_MODE=mock npm --prefix frontend run build`: aprobado con Vite 8.3.5;
  producción conserva HTTP, el modo mock solo puede activarse en desarrollo.
- Desarrollo local aislado, puerto 18174, modo mock y rol admin explícitos:
  `BROWSER_URL=http://127.0.0.1:18174/ npm --prefix frontend run test:browser`:
  **4 recorridos Chromium DEMO aprobados**, incluidos flujo común, especialidades,
  archivo, duplicados, doble envío y logout. No son nuevas pruebas HTTP reales.
- `git diff --check`: aprobado. Main es ancestro de la composición; no requiere
  resolver conflictos con el main observado `ead042c`.

## Evidencia integrada y decisión

El [cierre B5 publicado](../pablo/B5_CIERRE_INTEGRADO.md) documenta 230 pruebas
backend, 55 cliente, 14 HTTP/nativas, 7 recorridos reales, recuperación fría y
18 comprobaciones del entorno compartido, además de sesión en cuatro instituciones.
La suite A5 ampliada se repitió sobre `c457dcf`: 10 aprobadas, cero omitidas.
Esta ejecución revisó esa evidencia y su composición Git; no volvió a ejecutar
ni a modificar el entorno de Pablo. Los números anteriores no se suman a las
pruebas nuevas ni se atribuyen a un despliegue de este parche.

Las fuentes de aplicación backend/NoSQL, frontend/src y frontend/tests son
idénticas a bb2130c. El parche correctivo afecta a la herramienta de build;
la regresión cliente, navegador DEMO y build cubren ese cambio. No se reabren
A1–A5 ni se exige repetir mantenimiento sobre datos compartidos.

Con el parche y las comprobaciones anteriores, **es técnicamente viable proponer
la integración de feature/jennifer a main** con todo el alcance A/B acumulado.
Sigue pendiente la decisión expresa de Jennifer de abrir PR/integrar; no se abrió
PR ni se ejecutó merge a main. El PR de Pablo #16 permanece en borrador y su
indicación de mantener main aparte se conserva como contexto de su entrega.
Antes de integrar se deben refrescar ramas, checks y reglas reales de GitHub.
La ausencia de CI no equivale a CI aprobado. No se afirma validación docente,
conciliación universal de históricos ni seguridad completa de producción.
