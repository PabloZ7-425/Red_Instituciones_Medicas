from datetime import timedelta

PERSONAS = (
    ("Sofía", "Herrera Luna", "2018-03-20"),
    ("Mateo", "Navarro Gil", "2016-08-09"),
    ("Valentina", "Rosales Coto", "2020-01-25"),
    ("Gabriel", "Flores Ochoa", "2017-10-06"),
)


def configurar(carga):
    medico = carga.personal("Pediatría general", "Elisa", "Cruz Mena")
    medicamento = carga.medicamento("Luminex infantil")
    pacientes, (consulta, _, _) = carga.jornada(medico, PERSONAS, medicamento, "Control pediátrico",
        "Se revisaron los registros de crecimiento y el esquema de vacunación.", "Continuar seguimiento con el tutor.")
    paciente = pacientes[0]
    tutor = carga.id("tutor", ("dpi",), nombres="Natalia", apellidos="Herrera Luna", dpi="RIM-P-T01", correo="natalia.herrera@example.invalid")
    carga.id("paciente_tutor", ("paciente_id", "tutor_id"), paciente, paciente_id=paciente, tutor_id=tutor, parentesco="madre")
    vacuna = carga.id("vacuna", ("nombre",), nombre="Esquema infantil Aurora", numero_dosis=2, activo_operativo=True)
    tipo = carga.id("tipo_examen", ("nombre",), nombre="Control pediátrico básico", area="Laboratorio")
    anterior = carga.anterior
    for numero, dias in enumerate((90, 45, 0), 1):
        fecha = (anterior - timedelta(days=dias)).isoformat()
        controles = carga.clinica.obtener_seguimiento(paciente)["crecimiento"]
        nota = f"Control trimestral {numero}"
        carga.uno("control de crecimiento", controles, lambda fila: fila.get("observaciones") == nota,
                   lambda: carga.clinica.registrar_crecimiento(paciente, dict(fecha=fecha, peso_kg=f"{23+numero}.20",
                                                                            talla_cm=f"{119+numero}.00", observaciones=nota)))
    vacunas = carga.clinica.obtener_seguimiento(paciente)["vacunas"]
    carga.uno("aplicación de vacuna", vacunas, lambda fila: fila.get("lote") == "AUR-26-01",
              lambda: carga.clinica.registrar_vacuna(paciente, dict(vacuna_id=vacuna, fecha=anterior.isoformat(), dosis=1, lote="AUR-26-01")))
    carga.id("antecedente_medico", ("paciente_id", "descripcion"), paciente, paciente_id=paciente, tipo="Seguimiento",
             descripcion="Control periódico documentado por la persona responsable")
    carga.id("signos_vitales", ("consulta_id",), paciente, consulta_id=consulta, temperatura="36.5", frecuencia_cardiaca=82, saturacion_oxigeno="99.00")
    examen = carga.guardar("examen", ("consulta_id", "tipo_examen_id"), paciente, consulta_id=consulta, tipo_examen_id=tipo, estado="pendiente")
    if examen["values"]["estado"] == "pendiente":
        carga.estado("examen", examen, "en_proceso")
    carga.id("resultado_examen", ("examen_id", "valor"), paciente, examen_id=examen["id"], valor="Informe disponible", estado="finalizado")
    servicio = carga.id("servicio_medico", ("codigo",), codigo="PED-CONTROL", nombre="Consulta de seguimiento pediátrico", precio_base="150.00", estado="activo")
    aseguradora = carga.id("aseguradora", ("nombre",), nombre="Horizonte Salud", estado="activo")
    plan = carga.id("plan_seguro", ("aseguradora_id", "nombre"), aseguradora_id=aseguradora, nombre="Plan Familiar Horizonte",
                    deducible="0.00", limite_anual="10000.00", estado="activo")
    carga.id("cobertura_servicio", ("plan_seguro_id", "servicio_id"), plan_seguro_id=plan, servicio_id=servicio,
             porcentaje_cobertura="40.00", copago="0.00", estado="activo")
    poliza = carga.id("poliza_paciente", ("numero_poliza",), paciente, paciente_id=paciente, plan_seguro_id=plan,
                     numero_poliza="HZ-FAM-001", estado="activo")
    autorizacion = carga.guardar("autorizacion_seguro", ("numero_autorizacion",), paciente, poliza_paciente_id=poliza, consulta_id=consulta,
                                 numero_autorizacion="HZ-AUT-001", estado="pendiente")
    autorizacion = carga.estado("autorizacion_seguro", autorizacion, "aprobado", monto_autorizado="60.00")
    metodo = carga.id("metodo_pago", ("nombre",), nombre="Efectivo en recepción", estado="activo")
    carga.factura(paciente, consulta, servicio, metodo, poliza, autorizacion["id"])
