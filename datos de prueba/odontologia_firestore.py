PERSONAS = (
    ("Paula", "Reyes Ibarra", "1994-05-16"),
    ("Nicolás", "Estrada Vides", "1987-06-21"),
    ("Julia", "Barrios Lima", "2015-12-12"),
    ("Emilia", "Vargas Díaz", "2000-11-14"),
)


def configurar(carga):
    profesional = carga.personal(None, "Adriana", "Villalta Robles")
    medicamento = carga.medicamento("Dentiva")
    pacientes, (_, tratamiento, _) = carga.jornada(profesional, PERSONAS, medicamento, "Revisión dental",
        "Se registraron las piezas evaluadas y se explicó el plan de seguimiento.", "Revisar el odontograma en la siguiente visita.")
    paciente = pacientes[0]
    filas = carga.clinica.listar_procedimientos(paciente)
    if isinstance(filas, dict):
        filas = filas["procedimientos"]
    registros = []
    for pieza, estado, descripcion in (("16", "realizado", "Restauración"), ("26", "pendiente", "Revisión de restauración"),
                                      ("36", "pendiente", "Control de pieza posterior")):
        registros.append(carga.uno("procedimiento", filas, lambda fila: fila["pieza"] == pieza and fila["tratamiento_id"] == tratamiento,
            lambda: carga.clinica.registrar_procedimiento(paciente, dict(tratamiento_id=tratamiento, pieza=pieza, descripcion=descripcion, estado=estado))))
    carga.id("pago", ("referencia",), paciente, paciente_id=paciente, procedimiento_id=registros[0]["id"],
             monto_centavos=17500, moneda="GTQ", referencia="ODO-REC-001")
