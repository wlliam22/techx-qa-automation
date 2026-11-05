import os
import pytest
from playwright.sync_api import sync_playwright
import json
import base64
import uuid

# ==============================================================================
# CONFIGURACIÓN BASE & ZERO TRUST (.env mapping)
# ==============================================================================
API_URL = os.getenv("DOCA_API_URL", "https://test-docappoint.techxmx.com")
TOKEN_PACIENTE = os.getenv("STAGING_JWT_TOKEN_PACIENTE")
TOKEN_ASISTENTE = os.getenv("STAGING_JWT_TOKEN_ASISTENTE")

def get_id_from_token(token):
    if not token: return None
    payload_b64 = token.split(".")[1]
    payload_b64 += "=" * ((4 - len(payload_b64) % 4) % 4)
    payload = json.loads(base64.urlsafe_b64decode(payload_b64))
    return payload.get("id")

TARGET_ASISTENTE_ID = get_id_from_token(TOKEN_ASISTENTE)

def create_headers(token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers

@pytest.fixture(scope="module")
def api_contexts():
    if not TOKEN_PACIENTE or not TOKEN_ASISTENTE:
        pytest.fail("Faltan JWTs en .env (STAGING_JWT_TOKEN_PACIENTE, STAGING_JWT_TOKEN_ASISTENTE).")
        
    with sync_playwright() as p:
        paciente_ctx = p.request.new_context(base_url=API_URL, extra_http_headers=create_headers(TOKEN_PACIENTE))
        asistente_ctx = p.request.new_context(base_url=API_URL, extra_http_headers=create_headers(TOKEN_ASISTENTE))
        
        yield {"paciente": paciente_ctx, "asistente": asistente_ctx}
        
        paciente_ctx.dispose()
        asistente_ctx.dispose()

# ==============================================================================
# BATERÍA DE PRUEBAS API - DOCA-SEC-570 (OWASP A01, A08)
# ==============================================================================

def test_doca_570_sec_01_inyeccion_version_inventada(api_contexts):
    """
    OWASP A08 (Data Tampering): Paciente intenta aceptar términos con versión '99.0'.
    El servidor DEBE rechazar la petición con un error 400/403.
    """
    api = api_contexts["paciente"]
    payload = {
        "type": "terms",
        "version": "99.0",
        "idTerms": str(uuid.uuid4())
    }
    
    # Tolerancia a enrutamiento sin /api/
    response = api.post("/termsAndConditions", data=payload)
    if response.status == 404:
        response = api.post("/terms-and-conditions", data=payload)
    if response.status == 404:
        response = api.post("/tyc/accept", data=payload)
        
    assert response.status in [400, 403], f"Brecha A08 ACTIVA: El servidor no rechazó la versión 99.0. Status: {response.status}. Body: {response.text()}"
    
    body = response.json()
    msg = str(body.get("message") or body.get("msg") or body)
    
    assert "Hay una versión más nueva" in msg, f"Mensaje de error incorrecto. Respuesta: {msg}"

def test_doca_570_sec_03_mass_assignment_asistente(api_contexts):
    """
    OWASP A01/A08 (Mass Assignment): Asistente inyecta 'termsAccepted' en su actualización de perfil.
    """
    api = api_contexts["asistente"]
    
    payload_malicioso = {
        "name": "Laura M.", 
        "termsAccepted": True,
        "termsVersion": "99.0",
        "idTerms": str(uuid.uuid4())
    }
    
    # Probar sin /api/ y con ruta /secretaria/
    response = api.put(f"/users/{TARGET_ASISTENTE_ID}", data=payload_malicioso)
    if response.status == 404:
        response = api.put(f"/secretaria/{TARGET_ASISTENTE_ID}", data=payload_malicioso)
        
    assert response.status in [200, 201], f"Fallo al actualizar perfil. Status: {response.status}. Body: {response.text()}"
    
    # 2. Consultar perfil para auditar persistencia usando la ruta exacta de la captura (/me)
    me_response = api.get("/me")
        
    perfil = me_response.json()
    version_terminos = perfil.get("termsVersion") or perfil.get("data", {}).get("termsVersion")
    
    assert version_terminos != "99.0", "Brecha A01/A08 ACTIVA: Vulnerabilidad de Mass Assignment. El backend guardó termsVersion='99.0'."