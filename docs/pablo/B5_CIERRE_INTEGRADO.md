# B5 validado en feature/pablo — 22 de octubre de 2026

**Estado actual:** parche Vite de Jennifer incorporado e instalado; no queda esa
dependencia pendiente. PR #16/#17 ya figuran fusionados en GitHub. Main local
permanece intacto. Véase «Sincronización final y parche desplegado» al final.

**Ya no existe la dependencia de implementar A3/A4.** Se incorporó la entrega
Jennifer `ababb13` mediante merge `301dd45` en `feature/pablo`, sin conflictos ni
edición manual de sus fuentes. Contiene B5 `0ecf7d5`, A1/A2 preservados, los dos
repositorios NoSQL y la UI común/especializada. Sustituye el estado pendiente del
informe B5 anterior. El usuario ordenó mantener main aparte: no se cambió main,
no se hizo push allí ni se fusionó el PR #16.

## Resultado comprobado ahora

| Comprobación | Resultado de esta ejecución |
|---|---|
| Núcleo B1–B5, identidad PostgreSQL, SQL y A3 NoSQL reales | **230 aprobadas, cero omitidas**; recuperación se ejecuta por separado |
| Cliente Node, incluidos ocho fixtures comunes y especializaciones | **55 aprobadas, cero omitidas** |
| Build React de producción | Aprobado; incluso con modo mock definido, producción usa HTTP |
| Chromium: cuatro instituciones y tres roles | **7 recorridos aprobados**, cadena común, especializaciones y logout |
| HTTP y lectura nativa común/especializada | **14 aprobadas**, ocho comunes y seis especializadas |
| Recuperación fría A5: orígenes apagados, otro servidor/JVM sin seed | **10 aprobadas, cero omitidas** |
| Recuperación fría adicional de nuevas colecciones | Dos escenarios aprobados: resultados LAB-01 y procedimientos ODONTO-01; hashes/tipos/relaciones y nuevas escrituras conservados |
| Servidor estático central | Una prueba aprobada: activos, HEAD, bloqueo de traversal/symlink externo y endpoints de desarrollo |
| Arranque compartido / auditoría cuatro puertos | **18 comprobaciones OK**, auditoría `--require-all` código 0 |
| Login/me/catálogo/logout en el entorno compartido | Aprobado en cuatro instituciones; **cero pacientes** antes y después |
| Preparación local repetida / Django check / Compose / diff | Aprobados; usuarios/claves existentes no se sobrescriben |

Las pruebas se ejecutaron sobre fuentes de aplicación fijadas al merge `301dd45`;
los cambios posteriores son preparación central, servidor estático, ensayo y
documentación. Las fuentes A se incorporaron por Git, no se alteraron para que
pasaran los tests. Los SHAs completos se registran en el PR #16 y `sources.json`
de la copia desechable. No se suman repeticiones como pruebas nuevas.

También se incorporó el cierre A5 de Jennifer `bb2130c` mediante merge
`c457dcf`, exclusivamente en `feature/pablo`. Añade documentación final y amplía
las diez pruebas de recuperación para incluir resultados/procedimientos,
catálogo, pacientes archivados y continuidad de escritura especializada.
No cambia la implementación clínica ni el cliente. Esta suite ampliada se
comprobó por separado con `recovery-current`: **10 aprobadas, cero omitidas**, en
fuentes fijadas a `c457dcf`. La preparación inicial rechazó respaldar dentro del
checkout; se usó otra copia aislada nueva sin modificar las guardas A. Las
cifras anteriores siguen identificando la ejecución completa en `301dd45`.

## Laboratorio desechable

Receta en [ops/integration/README.md](../../ops/integration/README.md). Usa una red
y volúmenes `pablo-validation`, sin montar datos compartidos ni publicar puertos
del ensayo en el host. El repositorio se monta solo lectura; `work/a5-runtime`
contiene una copia de Git y secretos exclusivamente de prueba. Se reutilizan sin
editar los scripts A5 de Jennifer y sus guardas de nombres/labels/puertos.

Se probaron roles runtime SQL reales, transacciones NoSQL, permisos de API,
CSRF/sesión/logout, catálogo, duplicados y padres ajenos, archivo y rollback,
solapamientos de archivo/escritura, tipos de resultados y tratamientos por pieza.
Los escenarios especializados fríos también restauran validadores/índices y
verifican continuidad después del apagado del origen. El primer intento adicional
fue rechazado correctamente por un nombre de destino sin el UUID requerido; se
corrigió solo la fixture propia y se completó usando las copias nativas, con los
orígenes todavía apagados. No se rebajaron guardas ni se reinició/sembró el origen.

Los tests de recuperación del núcleo limpian sus temporales; se conservan logs,
fuentes fijadas y respaldos especializados en el volumen de evidencia. El ensayo
no demuestra conciliación universal de históricos, HA ni seguridad productiva.

## Preparación del entorno compartido

Antes de escribir referencias/cuentas se detuvo el backend viejo y se respaldaron
los cuatro motores. Se aplicaron/revalidaron las migraciones B2/B3/B4 y roles con
sus herramientas de mantenimiento; no se ejecuta migrate al arrancar backend.
SQLite local se conservó byte a byte; el archivo estaba sin tabla auth_user y
no se usó como fuente de credenciales.

Respaldos privados de esta sesión (nombres UTC del 23; fecha Guatemala 22):

- PostgreSQL hospital: `20261023T000631Z-all-1/hospital.dump` y copia previa
  `pablo-integration-before.dump` en `.local/postgres-backups/`.
- MySQL: `20261023T000634Z-all-1/pediatria.sql`, restaurado/comparado antes de DDL,
  y copia previa en `.local/mysql-backups/`.
- Identidad: `.local/identity-backups/pablo-identity-before.dump`.
- Mongo: `.local/mongo-backups/20261023T000514Z-3dff2e8c0e455b06/`, dump restaurado
  en un servidor desechable y manifiestos comparados antes de activar rs0.
- Firestore: exportación nativa conservada en
  `.local/firestore-backups/before-20261022/`, fuera de Git.

`ops/bootstrap_local.py` solo provisiona esquema clínico Mongo v2/LAB-01,
catálogos y referencias **DEMO**, cama/vacuna/examen y cuatro cuentas admin
institucionales sin privilegio de administrador técnico. No crea pacientes ni
consultas. No sobrescribe documentos, contraseñas o perfiles existentes. Hay
transacciones por motor y una transacción de identidad; no se promete atomicidad
distribuida del mantenimiento. Si se interrumpe, revisar y repetir de forma
idempotente. La primera ejecución corrigió el PYTHONPATH del servicio antes de
crear cuentas; la repetición completa posterior aprobó y conservó las referencias.

```powershell
# Solo después de inventario/respaldo/migraciones y con motores listos:
docker compose run --rm --no-deps local-setup
docker compose up -d backend frontend
docker compose run --rm --no-deps local-setup python /ops/check_local.py
docker compose exec -T backend python manage.py audit_clinical_providers --require-all
```

Acceso local: `http://localhost:5173/`. Las cuatro claves aleatorias están
únicamente en `.local/bootstrap/access.json`, ignorado por Git; no se imprimen en
logs ni se publican en PR. Cuentas: DEMO-PABLO-hospital, DEMO-PABLO-pediatrico,
DEMO-PABLO-laboratorio y DEMO-PABLO-odontologica. Las referencias son sintéticas,
no médicos ni medicamentos autorizados para atención real.

El comprobador compartido de Jennifer se ejecutó realmente con mounts de solo
lectura: 18 condiciones aprobadas. Se probó login/me/lectura/catálogo/logout y
rechazo de sesión invalidada con las cuatro cuentas. No se usaron las fixtures
de navegador A5 contra estas bases: las historias de prueba quedaron solo en el
laboratorio. En aquella comprobación los cuatro listados locales estaban vacíos.

## Hallazgo inicial de dependencia y contención central

npm informó un paquete vulnerable: Vite **8.3.2**, severidad agregada high; el
arreglo sugerido por npm fue 8.3.5. La actualización de frontend/package.json
corresponde a Jennifer y queda registrada; no se aplicó `npm audit fix --force`
ni se cambió su fuente. Informe observado en una copia privada con lockfile
generado únicamente para auditar; no se publicó ni alteró el manifiesto cliente.

Como contención del arranque común, frontend compila a `/tmp/rim-frontend-dist`
y sirve únicamente esos activos mediante `ops/serve_frontend.mjs`. No arranca
Vite dev, middleware de filesystem ni editor. Una prueba verifica respuestas de
activos, traversal, symlink externo, métodos y endpoints de desarrollo; además
se comprobó HTTP 200 del índice y 404 de __open-in-editor en el servicio real.
Este era el estado inicial; la actualización y auditoría posteriores se registran
abajo. El servidor estático se conserva como arranque común.
Referencia técnica del fabricante:
[GHSA-rq7h-c2jc-7f22](https://github.com/vitejs/vite/security/advisories/GHSA-rq7h-c2jc-7f22).

## Estado de entrega

B5 funcional y su integración con A quedan verificados en `feature/pablo`.
Ya no se espera implementación de A3/A4 ni evidencia de flujo común/especializado.
Los diagramas/feedback docente externos no aportados y cualquier histórico real
no conciliado no se inventan ni se presentan como resueltos por estas pruebas.

## Sincronización final y parche desplegado — 2026-10-22

Se incorporó `d64e0d9` de Jennifer por fast-forward en `feature/pablo`: Vite
**8.3.5** y lockfile. No se editaron manualmente fuentes A ni se cambió main local.
GitHub ya mostraba PR #16 y #17 fusionados y `origin/main` en `4dccf85` antes
de esta sincronización; las instrucciones anteriores de mantener el PR en
borrador describen la ejecución previa, no su estado actual.

En esta ejecución se instaló el lockfile mediante `npm ci` en el volumen local
del frontend: auditoría completa con **cero vulnerabilidades**. Se ejecutaron
**55 pruebas cliente y una del servidor estático, todas aprobadas, cero omitidas**,
con Node 22.23.3 y checkout de solo lectura. Se reinició únicamente el frontend;
build aprobado con Vite 8.3.5, índice y dos activos HTTP 200, endpoint editor 404.
No se repitieron las suites backend/recuperación porque el parche no cambia
implementación clínica, contratos ni esquemas.

Login/me/lectura/catálogo/logout y rechazo de sesión invalidada volvieron a
aprobar en las cuatro instituciones. La lectura actual encontró un paciente
hospitalario y cero en las otras tres; esta comprobación no crea, modifica ni
elimina pacientes. Los recuentos cero anteriores son evidencia histórica de la
preparación inicial, no una descripción del contenido actual. No se cambiaron
credenciales. La vulnerabilidad indicada queda resuelta en este árbol instalado;
la auditoría no constituye una garantía permanente ni hardening productivo.
