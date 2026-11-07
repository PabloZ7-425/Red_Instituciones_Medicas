"""Create missing native DEMO professionals without changing existing eligibility."""


def ensure_native_professional(institution, read, create):
    if institution not in {"laboratorio", "odontologica"}:
        raise ValueError("Native DEMO setup only supports the two document stores")
    identifier = "DEMO-PABLO-PRO"
    expected = {
        "nombre": "Profesional DEMO local",
        "colegiado": "DEMO-PABLO-LOCAL",
        "activo": True,
        "habilitado": True,
        "schema_version": 2,
        "institucion": institution,
    }
    current = read(identifier)
    if current is None:
        create(identifier, expected)
    elif any(current.get(key) != value or type(current.get(key)) is not type(value)
             for key, value in expected.items()):
        raise RuntimeError("Profesional DEMO nativo incompatible o deshabilitado; no se sobrescribe")
    return identifier
