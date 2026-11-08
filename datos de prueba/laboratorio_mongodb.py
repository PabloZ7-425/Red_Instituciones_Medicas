PERSONAS = (
    ("Camila", "Aguilar Ponce", "1992-07-18"),
    ("Julián", "Fuentes Leal", "1984-02-11"),
    ("Renata", "Molina Serrano", "1999-10-28"),
    ("Bruno", "Arias Montes", "1979-03-12"),
)


def configurar(carga):
    profesional = carga.personal(None, "Ricardo", "Lozano Ruiz")
    medicamento = carga.medicamento("Nivalis")
    pacientes, _ = carga.jornada(profesional, PERSONAS, medicamento, "Recepción de muestra",
        "Se registró la recepción y el procesamiento de la muestra.", "Revisar el informe al finalizar el procesamiento.")
    examenes = (
        ("Hemograma", "finalizado", [{"nombre": "Índice de control", "valor": 13, "unidad": "Unidades", "rango": "10–12"},
                                    {"nombre": "Control interno", "valor": True}]),
        ("Uroanálisis", "en_proceso", [{"nombre": "Aspecto", "valor": "Claro"}]),
        ("Cultivo", "pendiente", [{"nombre": "Recepción de muestra", "valor": True}]),
    )
    for indice, (nombre, estado, campos) in enumerate(examenes):
        paciente = pacientes[indice]
        tipo = carga.id("tipo_examen", ("nombre",), nombre=nombre, activo=True)
        filas = carga.clinica.listar_resultados(paciente)
        if isinstance(filas, dict):
            filas = filas["resultados"]
        carga.uno("resultado", filas, lambda fila: fila["tipo_examen"] == tipo,
                  lambda: carga.clinica.registrar_resultado(paciente, dict(tipo_examen=tipo, fecha=carga.utc(carga.anterior, 11 + indice),
                                                                            estado=estado, campos=campos)))
    carga.id("pago", ("referencia",), pacientes[0], paciente_id=pacientes[0], monto_centavos=8500, moneda="GTQ", referencia="LAB-REC-001")
