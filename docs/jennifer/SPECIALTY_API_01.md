# SPECIALTY-API-01@1.0.0 — extensiones institucionales

Publicado en feature/jennifer para cerrar A4, 22 de octubre de 2026. Es una
extensión aditiva: CONTRACT-API-01/REPO-01@1.0.0 mantienen campos y rutas.
Implementación: application/specialties.py, presentation/specialties.py y puertos
LAB-01/ODONTO-01 en domain/specialties.py; se reutilizan HOSPITAL-01 y PED-01.
La entrega se identifica con `git log -1 -- docs/jennifer/SPECIALTY_API_01.md`.

Identidad/institución/rol/profesional proceden exclusivamente de B2. Sesión,
cookies, rotación CSRF, errores uniformes y no-store son los de la API común.
Toda escritura requiere JSON y CSRF. Campos desconocidos, null en opcionales,
queries desconocidas/repetidas y duplicados JSON son 400. Rol e institución se
comprueban antes de resolver padres, leer DTOs o crear repositorios. El rol
laboratorista solo es válido en laboratorio. OPTIONS sigue la política de sesión
y CORS existente; HEAD de lecturas aplica los mismos permisos que GET.

## Rutas

Todas las rutas de la tabla llevan prefijo `/api/`. Las lecturas no paginadas
rechazan queries. Los tres catálogos aceptan q/limit/offset con la semántica común:
prefijo literal trim+NFC+lower, count previo a paginar, orden nombre normalizado/ID.

| Institución | Método/ruta | Entrada o salida | Permiso |
|---|---|---|---|
| hospital | GET pacientes/{id}/ingresos/ | `{paciente_id,ingresos:[]}` | admin/médico/enfermero |
| hospital | POST pacientes/{id}/ingresos/nuevo/ | IngresoCreate → 201 IngresoRead | admin/médico con profesional |
| hospital | POST ingresos/{id}/alta/ | `{fecha_hora_alta}` → 200 IngresoRead | admin/médico con profesional |
| hospital | GET camas/ | página `{count,limit,offset,results:[{id,nombre}]}` | admin/médico/enfermero |
| pediatrico | GET pacientes/{id}/seguimiento/ | PED-01: `{paciente_id,tutores:[],vacunas:[],crecimiento:[]}` | admin/médico/enfermero |
| pediatrico | GET pacientes/{id}/tutores/ | `{paciente_id,tutores:[]}`, sin historia/vacunas/crecimiento | admin/médico/secretaría |
| pediatrico | POST pacientes/{id}/tutores/nuevo/ | TutorCreate → 201 vínculo/tutor | admin/médico/secretaría |
| pediatrico | POST pacientes/{id}/vacunas/ | AplicacionCreate → 201 aplicación | admin/médico con profesional |
| pediatrico | POST pacientes/{id}/crecimiento/ | ControlCreate → 201 control | admin/médico con profesional |
| pediatrico | GET vacunas/ | página de `{id,nombre}` | admin/médico/enfermero |
| laboratorio | GET tipos-examen/ | página de `{id,nombre}` | admin/médico/enfermero/laboratorista |
| laboratorio | GET pacientes/{id}/resultados/ | `{paciente_id,resultados:[]}` | admin/médico/enfermero/laboratorista |
| laboratorio | POST pacientes/{id}/resultados/nuevo/ | ResultadoCreate → 201 ResultadoRead | admin/médico/laboratorista con profesional |
| odontologica | GET pacientes/{id}/procedimientos/ | `{paciente_id,procedimientos:[]}` | admin/médico/enfermero |
| odontologica | POST pacientes/{id}/procedimientos/nuevo/ | ProcedimientoCreate → 201 ProcedimientoRead | admin/médico con profesional |

Rutas separadas `/nuevo/` evitan alterar los métodos de rutas de lectura ya
definidas en esta extensión. No se añaden operaciones de borrado. Los IDs públicos
son strings opacos: no se reconstruyen a partir de códigos o números de catálogos.
Padre ausente/ajeno devuelve el mismo 404; institución incorrecta o rol insuficiente
devuelve 403 antes de su búsqueda. Persistencia ausente/incompleta produce 503.

## DTOs

- IngresoCreate: `{cama_id,fecha_hora_ingreso,tipo_ingreso}`. Tipo string 1..50;
  timestamp UTC no futuro. IngresoRead añade id, paciente_id y fecha_hora_alta null
  hasta alta. El catálogo devuelve código de cama como nombre, sin inventar una
  reserva. La transacción/índice de exclusividad resuelve cama ocupada como 409.
  Alta no anterior al ingreso. Misma alta es idempotente mientras paciente activo;
  otra alta es 409. Archivo impide también repetir esa escritura.
- TutorCreate: `{nombres,apellidos,parentesco,telefono?,correo?,dpi?}`. Textos
  requeridos no vacíos, máximo 100 salvo correo 150; opcionales omitidos al crear,
  null al leer. Respuesta incluye id del vínculo, tutor_id y paciente_id. Cada
  alta crea tutor y vínculo, sin fusionar personas por nombre o DPI. Parentesco
  histórico sin confirmar permanece separado en parentesco_legacy.
- AplicacionCreate: `{vacuna_id,fecha,dosis,lote?,observaciones?}`. Fecha civil no
  futura; dosis entero 1..2147483647, lote 100, observaciones 5000. Vacuna de catálogo
  existente. Lectura añade id/paciente_id y opcionales null. La dosis representa
  número de aplicación; no calcula una pauta médica.
- ControlCreate: `{fecha,peso_kg,talla_cm,observaciones?}`. Fecha civil no futura,
  medidas como strings decimales positivos <=9999.99 y máximo dos decimales;
  lectura devuelve dos decimales y mantiene mediciones_legacy separadas. No se
  atribuyen unidades ni percentiles a los históricos.
- ResultadoCreate: `{tipo_examen,fecha,estado,campos}`. tipo_examen es ID opaco del
  catálogo LAB-01. Fecha es instante UTC no futuro; estado pendiente/en_proceso/
  finalizado/anulado. campos contiene 1..50 objetos `{nombre,valor,unidad?,rango?}`:
  nombre único dentro del resultado (1..100), valor string no vacío (hasta 5000),
  número finito interoperable (valor absoluto <=9007199254740991) o booleano;
  unidad/rango textos opcionales 1..100. No se recibe `tipo` del editor UI: se
  envía valor JSON ya tipado. ResultadoRead añade id y paciente_id; profesional,
  versiones y BSON permanecen internos. Orden por instante real/ID, incluyendo
  fracciones de segundo; no por orden lexicográfico de timestamps.
- ProcedimientoCreate: `{tratamiento_id,pieza,descripcion,estado}`. pieza FDI
  permanente 11..18/21..28/31..38/41..48 o temporal 51..55/61..65/71..75/81..85;
  descripción 1..5000, estado pendiente/realizado. Tratamiento, diagnóstico y
  consulta deben pertenecer a ese paciente. ProcedimientoRead añade id,
  paciente_id y consulta_id derivada del tratamiento, nunca escogida arbitrariamente.

Todos los textos se recortan salvo IDs opacos. Fechas civiles no se convierten a
UTC. Instantes aceptan ISO UTC con Z y hasta seis decimales; el editor actual
valida segundos o milisegundos. Lecturas hospitalarias conservan todos los ingresos;
seguimiento/resultados/procedimientos no se truncan silenciosamente.

## Persistencia y archivo

PostgreSQL/MySQL reutilizan sus transacciones y bloqueo de paciente B3/B4. Se
añadieron lecturas nativas de camas y tutores sin ampliar grants ni migraciones
SQL. Laboratorio utiliza `clinico_tipos_examen` y `clinico_resultados` nuevos,
schema_version=2 e institución laboratorio. Se preparan explícitamente mediante
db/mongo/specialty_schema.py: valida definiciones existentes antes de crear,
añade índices, no hace collMod ni reemplaza datos. No se convierte el legado A2
de ObjectIds/nombres en nuevos IDs por inferencia. Mongo necesita replica set.

Firestore reutiliza procedimientos A1/v2 y añade escritos con IDs opacos. Comprueba
toda la cadena de padres y el paciente antes de encolar escrituras. Mongo y
Firestore modifican la versión raíz dentro de la misma transacción del hijo;
archivo compite sobre esa raíz. No hay escrituras especializadas posteriores al
commit de archivo. El rechazo conserva las lecturas anteriores.

No hay autenticación Firebase paralela, pagos, API de catálogos mutables ni
interpretación clínica de resultados. El entorno verificado usa datos sintéticos,
roles SQL limitados y Firestore Emulator, no Firebase productivo.
