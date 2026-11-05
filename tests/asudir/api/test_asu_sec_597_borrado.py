import os
import pytest
from playwright.sync_api import sync_playwright

# ==============================================================================
# CONFIGURACIÓN BASE & ZERO TRUST (.env mapping)
# ==============================================================================
API_URL = os.getenv("ASUDIR_API_URL", "https://back-staging.asudir051.com")
TOKEN_AGUA = os.getenv("STAGING_USUARIO_AGUA_TOKEN")
TOKEN_ADMIN = os.getenv("STAGING_JWT_TOKEN_ADMINISTRACION")

# Usamos un ID muy alto para simular la regla: "Responde 403 aunque no exista"
TARGET_SOLICITUD_ID = "99999" 

def create_headers(token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers

@pytest.fixture(scope="module")
def api_contexts():
    if not TOKEN_AGUA or not TOKEN_ADMIN:
        pytest.fail("Faltan JWTs en .env para Asudir 051.")
        
    with sync_playwright() as p:
        agua_ctx = p.request.new_context(base_url=API_URL, extra_http_headers=create_headers(TOKEN_AGUA))
        admin_ctx = p.request.new_context(base_url=API_URL, extra_http_headers=create_headers(TOKEN_ADMIN))
        anon_ctx = p.request.new_context(base_url=API_URL) # Sin headers
        
        yield {"agua": agua_ctx, "admin": admin_ctx, "anon": anon_ctx}
        
        agua_ctx.dispose()
        admin_ctx.dispose()
        anon_ctx.dispose()

# ==============================================================================
# BATERÍA DE PRUEBAS API - ASU-SEC-597 (OWASP A01)
# ==============================================================================

def test_asu_597_sec_01_borrado_cedente(api_contexts):
    """
    OWASP A01: Un Usuario de Agua (Cedente) intenta borrar una solicitud.
    DEBE recibir 403 Forbidden.
    """
    api = api_contexts["agua"]
    
    # Asumiendo nomenclatura estándar de Strapi v4
    response = api.delete(f"/api/transmision-procesos/{TARGET_SOLICITUD_ID}")
    
    assert response.status == 403, f"Brecha A01 ACTIVA: El Cedente logró saltar el 403. Status: {response.status}. Body: {response.text()}"
    
    body = response.json()
    msg = str(body.get("error", {}).get("message") or body)
    assert "No tienes acceso a este recurso" in msg, f"Mensaje de error incorrecto: {msg}"

def test_asu_597_sec_02_borrado_admin_id_inexistente(api_contexts):
    """
    OWASP A01: Un Admin intenta borrar un ID inventado.
    DEBE recibir 403 antes que 404 (Regla 3 de Negocio).
    """
    api = api_contexts["admin"]
    
    response = api.delete(f"/api/transmision-procesos/{TARGET_SOLICITUD_ID}")
    
    assert response.status == 403, f"Vulnerabilidad de Enumeración/Borrado: El Admin no recibió 403. Status: {response.status}. Body: {response.text()}"
    
    body = response.json()
    msg = str(body.get("error", {}).get("message") or body)
    assert "No tienes acceso a este recurso" in msg, f"Mensaje de error incorrecto: {msg}"

def test_asu_597_sec_03_borrado_sin_sesion(api_contexts):
    """
    Regla 4: Petición sin JWT debe ser rechazada con 401.
    """
    api = api_contexts["anon"]
    
    response = api.delete(f"/api/transmision-procesos/{TARGET_SOLICITUD_ID}")
    
    assert response.status == 401, f"Brecha de Autenticación: Status {response.status}"