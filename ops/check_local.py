"""Read-only clinical smoke; login/logout only mutate technical sessions."""
import json
from pathlib import Path

import requests


accounts = json.loads(Path("/private/access.json").read_text())
for institution, credentials in accounts.items():
    with requests.Session() as session:
        base = "http://backend:8000/api"
        token = session.get(base + "/auth/csrf/", timeout=10).json()["csrfToken"]
        response = session.post(base + "/auth/login/", json=credentials,
                                headers={"X-CSRFToken": token}, timeout=10)
        if response.status_code != 200:
            raise RuntimeError(f"Login local {institution} no disponible: {response.status_code}")
        assert session.get(base + "/auth/me/", timeout=10).json()["usuario"]["institucion"] == institution
        page = session.get(base + "/pacientes/?limit=1", timeout=10)
        catalog = session.get(base + "/medicamentos/?limit=1", timeout=10)
        assert page.status_code == catalog.status_code == 200
        assert catalog.json()["count"] > 0
        token = session.get(base + "/auth/csrf/", timeout=10).json()["csrfToken"]
        assert session.post(base + "/auth/logout/", json={}, headers={"X-CSRFToken": token}, timeout=10).status_code == 204
        assert session.get(base + "/pacientes/", timeout=10).status_code == 401
        print(institution, "login/me/lectura/catalogo/logout OK; pacientes:", page.json()["count"])
