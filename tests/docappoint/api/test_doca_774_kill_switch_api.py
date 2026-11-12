import os
import pytest
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

load_dotenv()

# ==============================================================================
# CONFIGURACIÓN BASE & ZERO TRUST (.env mapping)
# ==============================================================================
API_URL = os.getenv("DOCA_API_URL", "https://back-staging.docappoint.com") # Ajustar URL de tu entorno
TOKEN_DOCTOR = os.getenv("STAGING_JWT_TOKEN_MEDICO")

# Variables de entorno simuladas para el test
ID_PACIENTE = "PACIENTE_TEST_ID"
ID_EXPEDIENTE = "E-77"
ID_TRANSCRIPCION = "T-56"
ID_ANALISIS = "A-1001"

def create_headers(token=None):
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers

@pytest.fixture(scope="module")
def api_contexts():
    with sync_playwright() as p:
        # Contexto Doctor (Autenticado)
        doctor_ctx = p.request.new_context(base_url=API_URL, extra_http_headers=create_headers(TOKEN_DOCTOR)) if TOKEN_DOCTOR else None
        # Contexto Anónimo (Sin JWT para atacar webhook)
        anon_ctx = p.request.new_context(base_url=API_URL, extra_http_headers=create_headers())
        
        yield {"doctor": doctor_ctx, "anon": anon_ctx}
        
        if doctor_ctx: doctor_ctx.dispose()
        anon_ctx.dispose()

# ==============================================================================
# BATERÍA DE PRUEBAS API - DOCA-774 (KILL SWITCH)
# ==============================================================================

@pytest.mark.security
def test_doca_774_sec_01_subir_audio_404(api_contexts):
    """
    OWASP A01 (AC 13): El endpoint de subir audio debe estar EXTIRPADO.
    Incluso con sesión médica, debe dar 404 estricto para evitar envíos huérfanos.
    """
    api = api_contexts["doctor"]
    if not api:
        pytest.skip("Falta TOKEN_DOCTOR en el .env")
        
    payload = {
        "id_paciente": ID_PACIENTE,
        "id_expediente": ID_EXPEDIENTE,
        "audio_base64": "UklGRiQAAABXQVZFZm10IBAAAAABAAEARKwAAIhYAQACABAAZGF0YQAAAAA=" # Dummy audio
    }
    
    response = api.post("/api/transcripciones/upload", data=payload)
    
    assert response.status == 404, f"🚨 ALARMA A01: El endpoint de subida de audio SIGUE VIVO. Status: {response.status}"
    
    body = response.json()
    assert body.get("error") == "Not Found", "Falta mensaje estándar de 404 del app.js general."
    print("✅ [APROBADO] AC 13: Endpoint de subida de audio destruido.")

@pytest.mark.security
def test_doca_774_sec_02_webhook_avisar_404(api_contexts):
    """
    OWASP A01/A08 (AC 14): El webhook que inyectaba las transcripciones al expediente debe estar EXTIRPADO.
    Debe dar 404 estricto, previniendo escrituras sin credencial.
    """
    api = api_contexts["anon"]
    
    # 1. Ataque normal
    res_normal = api.post(f"/api/transcripciones/{ID_TRANSCRIPCION}/notify")
    assert res_normal.status == 404, f"🚨 ALARMA A08: Webhook de notificación sigue vivo. Status: {res_normal.status}"
    
    # 2. Ataque con force=true (Como dice Maryel en AC 14)
    res_force = api.post(f"/api/transcripciones/{ID_TRANSCRIPCION}/notify?force=true")
    assert res_force.status == 404, f"🚨 ALARMA A08: Webhook sigue vivo con force=true. Status: {res_force.status}"
    
    print("✅ [APROBADO] AC 14: Webhook de notificación IA destruido.")

@pytest.mark.security
def test_doca_774_sec_03_interpretar_analisis_503(api_contexts):
    """
    OWASP A04 (AC 12): El endpoint de interpretación IA no debe estar borrado (para que sea reversible),
    sino bloqueado con 503 y un mensaje específico.
    """
    api = api_contexts["doctor"]
    if not api:
        pytest.skip("Falta TOKEN_DOCTOR en el .env")
        
    response = api.post(f"/api/analisis/{ID_ANALISIS}/interpretar")
    
    assert response.status == 503, f"🚨 ALARMA A04: La IA de laboratorio no está bloqueada. Status: {response.status}"
    
    body = response.json()
    msg = str(body.get("message", ""))
    assert "deshabilitada" in msg.lower(), f"Mensaje de error incorrecto: {msg}"
    
    print("✅ [APROBADO] AC 12: Interpretación IA interceptada y bloqueada temporalmente.")