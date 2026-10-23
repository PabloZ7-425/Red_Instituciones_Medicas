# Contenido preparado para una futura integración

No es un PR publicado ni una autorización de merge. Actualizar SHAs/reglas y
resultado del entorno común antes de utilizarlo. La rama acumula módulos porque
Jennifer indicó continuar en su rama sin PR/merge automáticos; describir ese
alcance completo en lugar de presentarlo como un único parche A5.

## Título propuesto

feat(clinical): integra flujo y especializaciones reales en cuatro motores

## Problema y resultado

Main observado `ead042c` contiene identidad/contratos y proveedores SQL, pero no
la integración clínica NoSQL/React completa. La rama feature/jennifer incorpora
B5 y entrega el mismo flujo autenticado de paciente → consulta → diagnóstico →
tratamiento → receta → archivo para las cuatro instituciones, con persistencia
real y especializaciones hospitalaria, pediátrica, de laboratorio y odontológica.
Archivo conserva el expediente y rechaza atenciones posteriores.

## Módulos, responsable y alcance

- Jennifer, rama permanente feature/jennifer; A1/A2 preservados, A3/A4/A5 completos.
- B5 `0ecf7d5` incorporado mediante merge `a1747cd`, conservando autoría/historia.
- CONTRACT-API-01/REPO-01@1.0.0 conservados; SPECIALTY-API-01@1.0.0 aditivo.
- A4 incluyó una excepción autorizada por Jennifer para rutas/casos de uso centrales
  y lecturas SQL necesarias, solo en su rama. No se movió feature/pablo ni su PR #16.
- Evidencia final en docs/jennifer/A4_CIERRE_REAL.md y A5_CIERRE.md. main no se
  actualizó durante la preparación; el PR final debe listar su punta exacta.

## Validación disponible

- [x] 55 pruebas de cliente, build de producción, cuatro recorridos HTTP completos
  y tres por rol sobre servicios desechables reales; evidencia A4 `ababb13`.
- [x] Ocho pruebas HTTP/nativas comunes y seis especializadas aprobadas.
- [x] 49 pruebas de contrato/consistencia NoSQL aprobadas.
- [x] Backend A4: 99 aprobadas y 113 omitidas de 212 descubiertas; las omisiones
  son suites que requieren destinos/activación. No se cuentan como aprobadas.
- [x] Diez pruebas de recuperación fría ampliadas a resultados/procedimientos,
  sin seed en destino, igualdad, restricciones y continuidad comprobadas en A5.
- [x] Preparación reproducible A5: auditoría de proveedores 0 y 18 comprobaciones
  de arranque. No es certificación de otro equipo o de su Compose.
- [x] Documentación técnica, clasificación, modelos, REQ-01..13 y límites aportados.
- [ ] Build y arranque Compose del entorno común verificados y registrados.
- [ ] Configuración/grants/catálogos compartidos comprobados con el procedimiento.
- [ ] Punta final y reglas/checks GitHub reconsultados al preparar el PR.
- [ ] Decisión expresa de Jennifer de integrar a main.

No hay «CI aprobado» que marcar por ausencia de workflows/statuses. La receta
PASO_A_ENTORNO_COMUN.md está lista para la validación aún no ejecutada allí.

## Datos, preparación y reversión

Mongo requiere replica set, ocho colecciones comunes v2 y dos LAB-01; el
aprovisionamiento es explícito y no reescribe el legado A2. Firestore conserva A1
y opera v2; no convierte subcolecciones o referencias antiguas por inferencia.
Los catálogos/perfiles del stack de prueba son sintéticos, no una semilla común.
PostgreSQL/MySQL reutilizan B3/B4; las lecturas nuevas de camas/tutores no amplían
grants ni hacen DDL clínico. Identidad requiere la transición explícita B2.

Ante datos existentes, inventariar, detener escritores y respaldar/restaurar en
un destino nuevo verificado antes de una transición. Un rollback de código no
revierte datos nuevos: conservar el estado reciente y elegir el procedimiento de
cutover con el responsable. Los helpers NoSQL no restauran sobre destinos poblados
ni usan --drop contra datos compartidos. No borrar volúmenes para facilitar el merge.

No se versionaron secretos, .env, dumps, exportaciones, node_modules o dist. No se
certifican Firebase productivo, TLS, HA, rendimiento ni feedback docente ausente.
