# CONTRACT-API-01 y CONTRACT-REPO-01 — candidato 1.0

**Propuesta B-C0-T1, no ratificada ni implementada.** Referencias:
[decisiones pendientes](DECISIONES.md), [plan maestro §5](../../../PLAN_MAESTRO.md).
Los ejemplos ejecutables están en `backend/apps/historiales/fixtures/contrato_v1.json`.
Son datos sintéticos de diseño; no son respuestas obtenidas de una API activa.

## Convenciones y DTOs propuestos

JSON UTF-8. IDs opacos no vacíos de tipo string; identificación nunca numérica.
Slugs: hospital, pediatrico, laboratorio, odontologica. Fechas ISO YYYY-MM-DD;
timestamps, cuando existan, UTC con Z. No devolver motor, credenciales, SQL ni
tipos del driver. Rechazar campos desconocidos en cuerpos, especialmente motor,
institucion, usuario_id, medico_id e IDs generados por el servidor.

Textos se recortan antes de validar; obligatorios no admiten vacío ni null.
Campos opcionales se omiten o usan su valor predeterminado; null se rechaza.
IDs de ruta son opacos: formato inválido para el adaptador devuelve NOT_FOUND,
sin exigir dígitos a un ObjectId. Todas las relaciones se resuelven dentro del
repositorio de la institución autenticada, incluso referencias a medicamentos.

| DTO | Campos de creación | Lectura adicional |
|---|---|---|
| Paciente | identificacion: string 1..20; nombres/apellidos: string 1..100; fecha_nacimiento: fecha válida no futura | id, estado (activo/inactivo/archivado), motivo_archivo y fecha_archivo (null hasta archivo) |
| Consulta | fecha: fecha no futura; notas_evolucion: string 1..5000; cita_id: string opcional | id, paciente_id; cita_id null si no existe |
| Diagnostico | codigo_cie10: string 1..20; descripcion: string 1..5000 | id, consulta_id |
| Tratamiento | indicaciones_generales: string 1..5000 | id, diagnostico_id |
| Receta | medicamento_id: string; dosis/frecuencia: string 1..100; via_administracion: string 1..100 opcional | id, tratamiento_id; via_administracion null si se omite |
| Archivo | estado: literal archivado; motivo: string 1..200 | Paciente con estado/motivo/fecha de archivo |
| Login | username y password: strings no vacíos; sin recortar/modificar password | usuario {id, username, rol, institucion}; password nunca se devuelve |

La API genera fecha de archivo en la zona clínica America/Guatemala. La cadena
no lleva hora porque los esquemas actuales almacenan DATE. La consulta toma el
profesional desde el principal; no permite atribuirla a un médico arbitrario.
El catálogo farmacológico se prepara con fixtures por institución: su CRUD y
un endpoint de búsqueda no pertenecen a estas diez operaciones. UI debe acordar
su suministro con B; no suponer un catálogo común entre instituciones.

## Operaciones propuestas

| ID | Método y ruta | Éxito | Caso inválido del ejemplo |
|---|---|---|---|
| API-01 | POST /api/auth/login/ | 200 {usuario}, cookie de sesión; CSRF obligatorio | 401 UNAUTHORIZED: credenciales incorrectas |
| API-02 | GET /api/auth/me/ | 200 {usuario} | 401 UNAUTHORIZED: sin sesión |
| API-03 | GET /api/pacientes/?q=&limit=20&offset=0 | 200 {count,limit,offset,results} | 400 VALIDATION_ERROR: limit=0 |
| API-04 | POST /api/pacientes/ | 201 Paciente | 400 VALIDATION_ERROR: identificación vacía |
| API-05 | GET /api/pacientes/{id}/historial/ | 200 Historial | 404 NOT_FOUND: paciente inexistente o ajeno |
| API-06 | POST /api/pacientes/{id}/consultas/ | 201 Consulta | 400 VALIDATION_ERROR: fecha inválida |
| API-07 | POST /api/consultas/{id}/diagnosticos/ | 201 Diagnostico | 400 VALIDATION_ERROR: descripción vacía |
| API-08 | POST /api/diagnosticos/{id}/tratamientos/ | 201 Tratamiento | 400 VALIDATION_ERROR: indicaciones vacías |
| API-09 | POST /api/tratamientos/{id}/recetas/ | 201 Receta | 400 VALIDATION_ERROR: dosis vacía |
| API-10 | PATCH /api/pacientes/{id}/estado/ | 200 Paciente archivado | 400 VALIDATION_ERROR: motivo vacío |

API-03: q hasta 100 caracteres; limit entero 1..100, offset entero >=0;
valores predeterminados 20 y 0; parámetros desconocidos/repetidos se rechazan.
Buscar por identificación, nombres o apellidos, sin distinguir mayúsculas;
sin prometer equivalencia de acentos entre motores. Orden por identificacion
ascendente y luego id para desempate; count cuenta todas las coincidencias antes
de paginar. Incluye archivados/inactivos para consultar historial conservado.
No interpolar filtros en SQL. La paginación offset no garantiza snapshot entre
solicitudes concurrentes.

Historial: `{paciente, consultas}`; cada consulta agrega `diagnosticos`, cada
diagnóstico `tratamientos`, y cada tratamiento `recetas`. Colecciones vacías son
`[]`. Orden de consultas por fecha e id ascendente; colecciones hijas por id
ascendente como cadena. No mezclar objetos de otro paciente o institución.
Se limita este primer contrato a historias DEMO; paginar historias grandes
requiere una extensión acordada, sin truncado silencioso.

API-04 devuelve 409 si identificación ya existe en esa institución. La misma
identificación puede existir en otra. API-06..09 requieren paciente activo;
devuelven 409 si está archivado/inactivo. Referencia a cita/medicamento ausente o
ajena: 404; cita de otro paciente o ya consumida: 409. Archivo conserva hijos;
repetir mismo motivo en paciente archivado devuelve el estado original sin
cambiar fecha, distinto motivo devuelve 409. No hay reactivación en este contrato.

API-02..10 requieren sesión, perfil activo e institución válida. Permisos en
[D0-03](DECISIONES.md). Sin sesión: 401; rol insuficiente: 403, antes de buscar
el recurso. Recurso ajeno/ausente: 404 con el mismo mensaje. No aceptar
institución del navegador, aunque coincida con la sesión.

## Formato de error y excepciones de dominio propuestas

```json
{"error":{"code":"VALIDATION_ERROR","message":"Datos inválidos","fields":{"identificacion":["Este campo es obligatorio"]}}}
```

`fields` siempre es un objeto, vacío para errores generales. JSON malformado o
estructura incorrecta: 400; contenido no JSON: 415; método no permitido: 405.
No exponer existencia de usuarios ni detalles de persistencia.

| Excepción propuesta | HTTP / code | Regla |
|---|---|---|
| DatosInvalidos | 400 VALIDATION_ERROR | Campos seguros para el cliente |
| NoAutenticado | 401 UNAUTHORIZED | Sesión ausente/expirada o login inválido |
| AccesoDenegado | 403 FORBIDDEN | Rol insuficiente o CSRF inválido |
| RecursoNoEncontrado | 404 NOT_FOUND | Ausente o fuera de institución |
| Conflicto | 409 CONFLICT | Duplicado, estado o relación incompatible |
| ErrorInterno | 500 INTERNAL_ERROR | Error no esperado, mensaje genérico |
| PersistenciaNoDisponible | 503 SERVICE_UNAVAILABLE | Conexión/timeout, sin detalles del servidor |
| TipoContenidoNoSoportado | 415 UNSUPPORTED_MEDIA_TYPE | El cuerpo requiere JSON |
| MetodoNoPermitido | 405 METHOD_NOT_ALLOWED | Método fuera del contrato |

Estos nombres describen el contrato; aún no se crean clases de excepción.
No traducir indiscriminadamente cualquier error SQL a conflicto. Fallos de
conexión y errores inesperados tienen categorías diferentes.

## CONTRACT-REPO-01 — firmas candidatas

`JsonMap = Mapping[str, Any]`; entradas validadas por aplicación; el repositorio
verifica relaciones, unicidad, estado y errores de persistencia. Los resultados
son los DTOs JSON anteriores, independientes de drivers. Factory conserva los
cuatro registros; API clínica la invocará solo con Institution validada del principal.

```python
def registrar_paciente(self, paciente: JsonMap) -> JsonMap: ...
def listar_pacientes(self, *, q: str = "", limit: int = 20, offset: int = 0) -> JsonMap: ...
def obtener_historial(self, paciente_id: str) -> JsonMap: ...
def registrar_consulta(self, paciente_id: str, consulta: JsonMap) -> JsonMap: ...
def registrar_diagnostico(self, consulta_id: str, diagnostico: JsonMap) -> JsonMap: ...
def registrar_tratamiento(self, diagnostico_id: str, tratamiento: JsonMap) -> JsonMap: ...
def registrar_receta(self, tratamiento_id: str, receta: JsonMap) -> JsonMap: ...
def archivar_paciente(self, paciente_id: str, motivo: str) -> JsonMap: ...
```

Cada escritura debe terminar completa o sin cambios. Para receta MySQL, cabecera
y detalle son una única operación. Comprobar estado y escribir dentro del mismo
límite atómico para impedir escritura concurrente posterior al archivo.
El contexto del repositorio incluye identidad/profesional validado para consulta;
no alterar la firma del plan para recibir medico_id desde el navegador.
La implementación concreta del contexto se revisará en C1 antes de adaptadores.

Compatibilidad: el puerto actual tiene registrar_paciente, obtener_historial,
registrar_consulta y desactivar_paciente sin tipos. Se proponen cuatro métodos
nuevos y reemplazar desactivar_paciente por archivar_paciente. Este último es
un cambio de interfaz explícito; necesita revisión de A. Ninguno de los cuatro
adaptadores implementa aún ese puerto clínico; solo DatabaseAdapter.health_check.
No modificar ports.py hasta aprobación para evitar aparentar ratificación.

## Aceptación y revisión

Cada motor deberá probar flujo completo DEMO, IDs string, relaciones, duplicados,
archivo, ausencia, aislamiento y rollback donde aplique. Las pruebas de ejemplos
de C0 verifican consistencia del diseño y no acreditan persistencia, seguridad
de endpoints ni transacciones. Antes de C3/C4 deberá existir suite de contrato
ejecutada contra bases de prueba aisladas.

- [ ] Jennifer confirma DTOs, relaciones y manejo de IDs/fechas.
- [ ] Ambos aprueban decisiones D0, códigos adicionales y extensiones auth.
- [ ] Resolver precondiciones SQL de cita y relación tratamiento/receta en C2.
- [ ] Registrar SHA y aprobación explícita «aprobado para implementar».
- [ ] Solo entonces consolidar puerto, tipos y excepciones de dominio en otro cambio revisable.
