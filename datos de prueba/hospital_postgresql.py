from datetime import timedelta

PERSONAS = (
    ("Lucía", "Paredes Soto", "1989-04-14"),
    ("Diego", "Rivas Monroy", "1978-09-22"),
    ("Inés", "Castañeda Paz", "1995-06-03"),
    ("Andrés", "Valdés Roldán", "1981-11-18"),
)


def configurar(carga):
    medico = carga.personal("Medicina interna", "Mariana", "Santos Vela")
    medicamento = carga.medicamento("Cardiovela")
    pacientes, (consulta, _, receta) = carga.jornada(medico, PERSONAS, medicamento, "Seguimiento ambulatorio",
        "Se revisó la evolución y se acordó seguimiento ambulatorio.", "Registrar evolución y reevaluar en el próximo control.")
    paciente, segundo = pacientes[:2]
    enfermero = carga.id("enfermero", ("licencia_enfermeria",), nombre_completo="Tomás Méndez Sol", licencia_enfermeria="RIM-H-E01")
    pabellon = carga.id("pabellon_edificio", ("nombre_pabellon",), nombre_pabellon="Pabellón Los Cedros", director_responsable=medico)
    habitacion = carga.id("habitacion", ("numero_habitacion",), id_pabellon=pabellon, numero_habitacion="CED-201", tipo_atencion="Hospitalización")
    camas = [carga.id("cama", ("codigo_cama",), id_habitacion=habitacion, codigo_cama=f"CED-201-{letra}", estado_limpieza="limpia") for letra in "ABC"]
    quirofano = carga.id("quirofano", ("nombre_sala",), id_pabellon=pabellon, nombre_sala="Sala Jacaranda")

    def ingreso(pid, cama, dia):
        registros = carga.clinica.listar_ingresos(pid)
        if isinstance(registros, dict):
            registros = registros["ingresos"]
        momento = carga.utc(dia, 7)
        return carga.uno("ingreso hospitalario", registros, lambda fila: fila["tipo_ingreso"] == "Observación programada",
                         lambda: carga.clinica.ingresar_paciente(pid, dict(cama_id=cama, fecha_hora_ingreso=momento, tipo_ingreso="Observación programada")))

    anterior = carga.anterior
    fila = ingreso(paciente, camas[0], anterior)
    entrada = fila["id"]
    carga.id("emergencia", ("id_ingreso",), paciente, id_ingreso=entrada, motivo_consulta="Observación clínica", nivel_triaje="Verde")
    carga.id("signos_vitales", ("id_ingreso", "id_enfermero"), paciente, id_ingreso=entrada, id_enfermero=enfermero,
             frecuencia_cardiaca=74, oximetria=99)
    carga.id("movimiento_cama", ("id_ingreso", "motivo_traslado"), paciente, id_ingreso=entrada, id_cama=camas[1],
             fecha_hora_inicio=carga.utc(anterior, 9), motivo_traslado="Seguimiento en hospitalización")
    cirugia = carga.guardar("cirugia", ("id_ingreso", "fecha_hora_inicio"), paciente, id_ingreso=entrada, id_quirofano=quirofano,
                            fecha_hora_inicio=carga.utc(anterior, 11), fecha_hora_fin=carga.utc(anterior, 12), estado="pendiente")
    carga.id("equipo_quirurgico", ("id_cirugia", "id_medico"), paciente, id_cirugia=cirugia["id"], id_medico=medico, rol_en_cirugia="Cirujana responsable")
    carga.estado("cirugia", cirugia, "realizado")
    carga.id("diagnostico_ingreso", ("id_ingreso", "descripcion"), paciente, id_ingreso=entrada, codigo_cie10="Z09", descripcion="Seguimiento hospitalario")
    despacho = carga.id("despacho_farmacia", ("id_receta",), paciente, id_receta=receta, cantidad_entregada=1)
    carga.id("aplicacion_enfermeria", ("id_despacho", "id_enfermero"), paciente, id_despacho=despacho, id_enfermero=enfermero)
    carga.factura(paciente, consulta)
    if fila.get("fecha_hora_alta") is None:
        carga.paso = "alta hospitalaria"
        carga.clinica.dar_alta(entrada, carga.utc(anterior + timedelta(days=1), 10))
    ingreso(segundo, camas[2], carga.fecha - timedelta(days=1))
