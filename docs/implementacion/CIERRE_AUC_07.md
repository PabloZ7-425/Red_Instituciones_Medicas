# AUC-07: transiciones clínicas y administrativas

> Seguimiento AUC-08: los recorridos de navegador y permisos ya fueron verificados; ver [cierre AUC-08](CIERRE_AUC_08.md). Los resultados y pendientes de este documento describen su ejecución original.


Implementación en `implementacion`, conservando las rutas clínicas anteriores.
La edición operativa valida una máquina de estados explícita dentro de la
transacción, después de leer el registro y comprobar su versión. No se permite
reabrir registros clínicos finalizados ni modificar su contenido desde operaciones.

## Estados y condiciones

| Recurso | Transiciones | Condiciones |
|---|---|---|
| Cirugía hospitalaria | pendiente → realizado/cancelado | Alta en pendiente. Completar exige ingreso abierto, fin transcurrido y equipo quirúrgico. Realizado/cancelado son terminales; no se añade equipo después. Cancelar libera la reserva del quirófano. |
| Examen pediátrico | pendiente → en_proceso/anulado; en_proceso → finalizado/anulado | Finalizar requiere un resultado finalizado. Los resultados pendientes se anulan antes de cancelar el examen. Finalizado/anulado son terminales. |
| Resultado pediátrico | pendiente → en_proceso/anulado; en_proceso → finalizado/anulado | Se puede registrar directamente un resultado final completo; después es inmutable. Hay un solo resultado no anulado por examen. Guardar un resultado pendiente/en proceso coloca el examen en proceso; finalizar resultado y examen es atómico. La fecha final no puede ser futura. |
| Autorización y reclamación | pendiente → aprobado/rechazado/anulado; aprobado → anulado | Nuevas solicitudes empiezan pendientes. Aprobar exige importe positivo; se conserva el límite reclamado/autorizado. La fecha de resolución se deriva si falta y debe respetar la cronología. Las aprobaciones solo admiten anulación, preservando importes/datos. Rechazado/anulado son terminales. |
| Plan y cobertura | activo ↔ inactivo | Se conservan los registros. Una referencia desactivada no impide desactivar su cobertura; reactivarla exige padres habilitados. |
| Resultado de laboratorio | pendiente → en_proceso/anulado; en_proceso → finalizado/anulado | PATCH solo de estado, con rol clínico y vínculo profesional. Finalizar vuelve a validar campos y fecha del resultado existente. Finalizado/anulado son terminales. |
| Procedimiento odontológico | pendiente → realizado/anulado | PATCH solo de estado, con rol clínico y vínculo profesional. Realizar valida tratamiento, pieza y descripción existentes. Realizado/anulado son terminales. Un procedimiento con pagos vigentes no se anula; los nuevos pagos requieren un procedimiento realizado. |

No se crea otro resultado o procedimiento para cambiar el estado del anterior.
Los endpoints clínicos de alta documental conservan la posibilidad de registrar
un resultado final o procedimiento realizado con todos sus datos válidos.

La revocación de una autorización aprobada exige cancelar/rechazar antes sus
reclamaciones activas. Se mantienen las reglas AUC-06: los cobros del seguro se
revierten antes de reducir la aprobación que los respalda. Las cancelaciones no
borran registros ni importes históricos. Referencias desactivadas permiten cerrar
o desactivar una tarea existente, pero no reactivarla por esa excepción.

## Interfaz, API y protección clínica

El manifiesto operativo incorpora `state_transitions`, `initial_states` y
`transition_only_states`. El editor muestra los pasos permitidos y limita una
aprobación a su anulación. Los registros terminales abren Ver detalle.
Resultados/procedimientos documentales tienen ahora edición de estado desde
Atención y seguimiento; su alta sigue en el expediente clínico.

```text
PATCH /api/operaciones/{recurso}/{id}/
{"values":{"estado":"..."},"version":"..."}
```

Una transición incompatible o versión obsoleta devuelve 409; requisitos de
contenido, fecha, equipo, aprobación o dependencias devuelven 400. Sin rol/vínculo
profesional documental se rechaza antes de leer el cuerpo o construir el proveedor.
El manifiesto tampoco ofrece esa edición a una cuenta sin vínculo profesional.

En MongoDB/Firestore se conserva el documento clínico y se toca la versión raíz
del paciente. Los campos fuera de la definición operativa, como campos del
resultado, tratamiento, pieza o autor, no se pierden ni se pueden sobrescribir
desde este PATCH. El token devuelto incluye el estado real completo del documento;
una segunda edición válida no falla por omitir metadatos del token anterior.
Las transiciones compiten transaccionalmente entre sí y con el archivo del paciente.

El modelo de validación/exportación Firestore acepta ahora procedimientos anulados.
Debe actualizarse junto con el backend para validar/restaurar esos documentos.
No se amplían estados de los fixtures v1 legados ni se transforman documentos viejos.
No se necesita DDL adicional por AUC-07; la preparación PostgreSQL de AUC-06 sigue
siendo requisito. Estados antiguos desconocidos quedan en lectura y requieren
conciliación explícita en AUC-12, sin normalizarlos silenciosamente.

## Reproducción y límites

Verificación final sobre el árbol de trabajo posterior a `d38e44f`:

- Backend: **54 aprobadas, 0 fallidas, 0 omitidas**, incluyendo pruebas dirigidas
  en los cuatro motores, concurrencia de transiciones documentales, rollback,
  controles de permisos/API y regresiones AUC-01..06.
- Cliente Node: **62 aprobadas, 0 fallidas, 0 omitidas**; build Vite aprobado.
- Modelo Firestore: **10 aprobadas y 5 omitidas**; las omitidas pertenecen al
  recorrido de recuperación que exige su configuración dedicada. No se cuentan
  como aprobadas ni se suman a los escenarios nativos como pruebas distintas.
- Informe y logs privados finales: `.local/validation/auc07-2b9008945066/`.

El primer ensayo tuvo un error en la preparación de un quirófano sin pabellón;
se corrigió el dato de prueba y la ejecución final de 54 pasó completa. Los
resultados previos de 51/52 no reemplazan ni se suman a la verificación final.

El ejecutor de AUC-06 admite `--transitions`: añade MongoDB con replica set y un
emulador Firestore nuevos en la misma red temporal, sin puertos publicados ni
volúmenes compartidos. Usa un JAR local y las imágenes existentes del proyecto.

```powershell
python docs/implementacion/verify_finance.py --transitions --docker "$env:LOCALAPPDATA/Programs/DockerDesktop/resources/bin/docker.exe"
node --test frontend/tests/*.test.js
npm.cmd --prefix frontend run build
python -m unittest discover -s db/firebase/tests -p test_clinical.py
```

La verificación no representa un despliegue ni una actualización sobre una copia
poblada del entorno compartido. El recorrido completo de las nuevas ediciones en
navegador y la matriz exhaustiva de roles siguen en AUC-08. Por ese motivo las
filas relacionadas siguen P en la matriz, aunque tengan pruebas nativas dirigidas.

La siguiente tarea solicitada es AUC-08; AUC-09 conserva los cambios de navegación.
