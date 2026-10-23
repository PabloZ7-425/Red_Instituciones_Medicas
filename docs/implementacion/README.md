# Operación de las cuatro instituciones

> **Actualización:** AUC-01 a AUC-04 corregidos; ver [cierre y pruebas](CIERRE_AUC_01_04.md). AUC-05 corregida con [regresión aislada](CIERRE_AUC_05.md). AUC-06 implementada con [SQL real validado](CIERRE_AUC_06.md). AUC-07 implementada con [transiciones verificadas en cuatro motores](CIERRE_AUC_07.md). Los recorridos completos en navegador siguen en AUC-08; AUC-08 a AUC-12 continúan pendientes. Consultar [auditoría](AUDITORIA_COBERTURA.md) y [matriz actualizada](MATRIZ_COBERTURA.md).

Rama `implementacion`, creada desde main `4dccf8509265d1d6af44654c7629a9eb43a77aa6`.
Esta ampliación no modifica las ramas Jennifer/Pablo ni integra main.

## Uso

Al iniciar sesión se abre **Inicio y operaciones**. El menú muestra únicamente
las áreas de la institución y las funciones autorizadas por rol:

- Agenda: registrar, reprogramar, cancelar y atender una cita. Atender abre el
  paciente y la consulta vinculada; el servidor valida profesional/paciente y
  marca la cita atendida junto con la consulta.
- Catálogos: búsqueda paginada, alta, edición con control de versión y
  desactivación donde existe estado. No se eliminan referencias históricas.
- Atención y seguimiento: expedientes comunes y funciones propias por institución.
- Hospitalización: ingresos, traslados, emergencias, signos, cirugías y equipo.
- Farmacia hospitalaria: despacho con descuento de stock y registro de aplicación.
- Caja y seguros: factura, conceptos, pagos, pólizas, coberturas, autorizaciones
  y reclamaciones según las tablas de cada institución.
- Usuarios y permisos: altas, activación/desactivación y vinculación profesional
  de cuentas existentes, sin privilegios técnicos
  Django ni credenciales paralelas en las tablas antiguas.

**Pacientes y expedientes** conserva el flujo clínico anterior. El expediente se
separa en Consultas y tratamientos / Seguimiento institucional. Cada tarea abre
un único editor modal; Escape o Cancelar lo cierra cuando no se está guardando.
Al volver a operaciones, el paciente seleccionado filtra los registros relacionados.
Los catálogos generales siguen disponibles. La selección se conserva al actualizar
el historial; no se vuelve al inicio después de cada registro.

## Autocompletado y eficiencia

- Fecha civil y hora precargadas con reloj America/Guatemala; instantes enviados
  en UTC, sin pedir al usuario escribir el sufijo Z. Edad calculada.
- Paciente y profesional sugeridos por contexto; relaciones mediante nombres y
  búsqueda paginada, sin introducir claves internas.
- Número de factura/referencia sugeridos, cantidad inicial 1 y descuentos/impuestos
  iniciales 0. Precio sugerido desde servicio; saldo sugerido desde factura.
- Subtotales, participación del paciente, totales y estado de pago derivados en
  el servidor. Un clic repetido no dispara otro envío desde el mismo formulario.
- Un registro guardado ofrece el siguiente paso cuando hay una relación directa:
  especialidad→médico, pabellón→habitación→cama, aseguradora→plan→cobertura,
  factura→conceptos→pago, examen→resultado, cirugía→equipo, tutor→vínculo y
  diagnóstico de ingreso→tratamiento→prescripción→despacho.

La mejora demostrada es funcional: precarga de datos, selectores y cálculos que
antes exigían entrada manual o mantenimiento fuera de la interfaz. Los tests
comprueban esos comportamientos. No se publican porcentajes de ahorro de tiempo,
benchmarks ni productividad clínica que no se hayan medido con usuarios reales.

## API y reglas

API `OPERACIONES-01@2.0.0`, documentada por `/api/operaciones/`. La facturación
SQL requiere emitir el borrador antes de cobrar; las tareas explícitas de emisión,
anulación y reversión están en el [cierre AUC-06](CIERRE_AUC_06.md), junto con la
preparación del CHECK PostgreSQL antes de usar esta versión.
Los estados operativos siguen las [transiciones AUC-07](CIERRE_AUC_07.md);
las autorizaciones/reclamaciones nuevas empiezan pendientes y se resuelven por
edición. Los estados clínicos terminales son de solo lectura.
GET `/api/operaciones/{recurso}/` admite q, limit 1..100, offset, patient y lookup=1.
POST crea; PATCH `/{id}/` exige `{values,version}`. La versión es una huella del
registro leído: una edición obsoleta devuelve 409. Los campos calculados y los
campos fuera de la definición se rechazan. El PATCH de seguimiento solo admite
los campos declarados para ese recurso. No hay DELETE.

La allowlist estática resources.json aporta tablas, columnas, relaciones, grupos,
permisos y campos. No se ejecutan identificadores SQL suministrados por el cliente.
Se comparten sesión institucional, CSRF, parser JSON estricto, errores y no-store.
El rol se comprueba antes de construir el proveedor y leer cuerpos de escrituras.
lookup devuelve únicamente etiquetas de identificación y sugerencias necesarias,
no notas clínicas completas a los roles administrativos.

Los padres se verifican dentro de la transacción. Todas las referencias clínicas
comparten paciente y se bloquea/toca la raíz frente al archivo. SQL usa sus roles
runtime, sin DDL ni acceso a contraseñas heredadas. Citas se serializan por médico;
NoSQL modifica también la versión del profesional. Traslados actualizan cama y
cierran el movimiento previo. Quirófanos rechazan solapamientos con reserva final
explícita. Farmacia rechaza stock insuficiente. Pagos bloquean factura y no exceden
su saldo; conceptos y totales se guardan o revierten juntos. No se reintentan POST
por fallos de red desde el navegador.

## Habilitar en un entorno existente

Esto requiere mantenimiento explícito; no basta con actualizar el frontend.
Inventariar versión/datos, detener escritores y conservar respaldos restaurables
según B2–B5. No borrar volúmenes ni volver a ejecutar init.sql en bases pobladas.

1. Con propietario de PostgreSQL: aplicar db/postgres/operations_upgrade.sql
   (flags aditivos idempotentes) y operations_runtime.sql.
2. Con propietario de MySQL: inventariar information_schema.COLUMNS para las
   cuatro columnas activo_operativo listadas en db/mysql/operations_upgrade.sql;
   aplicar **solo ALTER de columnas ausentes**, una vez. Después aplicar
   operations_runtime.sql. Se conservan los grants B4 sobre pediatria_schema_version.
3. Mongo: replica set ya preparado, esquemas clínico y especializado existentes;
   ejecutar operations_schema.py --apply con MONGO_CLINICAL_SETUP_URI del
   mantenimiento. Solo crea colecciones operativas nuevas y sus índices; rechaza
   validadores incompatibles. No importa ni modifica colecciones antiguas.
4. Firestore: mismo proyecto/emulador configurado por B5. Los nuevos documentos
   usan institucion/schema_version=2; no se transforman documentos v1.
5. Instalar frontend con npm ci y compilar; reconstruir backend con el nuevo módulo.
   Verificar manifiesto, permisos, catálogos, sesión y recorrido en datos designados.
   La ampliación conserva la autenticación central existente.

Las nuevas instalaciones ya incluyen flags en init.sql. Los grants operativos
son explícitos y deben aplicarse también en instalaciones nuevas. El rollback de
código no revierte nuevos registros ni cobros; conservar datos y respaldo, pausar
escritores y elegir la recuperación con el responsable del entorno.

## Verificación reproducible

Con dependencias backend, Docker, Java/Chromium y JAR oficial del emulador:

```bash
python docs/implementacion/verify_native.py --run --browser \
  --work /ruta/fuera-del-repo/ensayo-nuevo \
  --jar /ruta/firestore.jar
node --test frontend/tests/*.test.js
npm --prefix frontend run build
```

El runner requiere destino nuevo y puertos propios libres. Crea tres motores y
un JVM nuevos, sin montar datos compartidos; identifica contenedores por ID/label
y retira exclusivamente sus recursos. Usa roles SQL limitados y datos DEMO. La
identidad de navegador es SQLite desechable: acredita los endpoints/permisos de la
ampliación, no repite el cutover PostgreSQL B2 validado anteriormente. Los logs y
credenciales sintéticas quedan fuera de Git con directorio privado. No usar las
cuentas/semillas del ensayo como cuentas de atención real.

[Resultados de la verificación final](VALIDACION.md).

Cobertura física y tratamiento de tablas técnicas: [COBERTURA.md](COBERTURA.md).
