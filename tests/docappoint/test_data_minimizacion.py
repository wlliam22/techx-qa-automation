import pytest
from playwright.sync_api import APIRequestContext
import os

@pytest.mark.security
@pytest.mark.auto_ready
def test_doca_61_sec_anonymous_doctor_data_minimization(playwright):
    """
    DOCA-61-SEC-01: Validar que la ficha por ID de un médico sin sesión
    NO filtre hash de contraseña, códigos de recuperación, CLABE, ni teléfono.
    """
    # Consumir la URL del backend API, no del frontend web
    base_url = os.getenv("DOCAPPOINT_API_URL", "https://test-docappoint.techxmx.com")
    doctor_id = "de5d2dea-8448-4fef-9086-f75b9bb7e0d0" # ID de Staging

    api_context = playwright.request.new_context(base_url=base_url)
    response = api_context.get(f"/user/{doctor_id}")
    
    assert response.status == 200, f"Error al consultar ficha pública: {response.status}"
    
    # Candado DevSecOps: Validar que el servidor entregue JSON y no un fallback HTML
    content_type = response.headers.get("content-type", "")
    assert "application/json" in content_type, f"Respuesta no es JSON. Content-Type recibido: {content_type}"
    
    data = response.json()

    # Campos PROHIBIDOS en ficha pública (Zero Trust / OWASP A01 & A02)
    campos_prohibidos = ["password", "hash", "recovery_code", "verification_code", "clabe", "rfc", "phone", "email"]
    for campo in campos_prohibidos:
        assert campo not in data, f"ALERTA DEVSECOPS: El campo sensible '{campo}' se está fugando en la ficha pública!"