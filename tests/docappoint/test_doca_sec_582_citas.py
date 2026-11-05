import os
import pytest
from playwright.sync_api import sync_playwright
import json
import base64

# ==============================================================================
# CONFIGURACIÓN BASE & ZERO TRUST (.env mapping multi-rol)
# ==============================================================================
API_URL = os.getenv("DOCA_API_URL", "https://test-docappoint.techxmx.com")
TOKEN_MEDICO = os.getenv("STAGING_JWT_TOKEN_MEDICO")
TOKEN_PACIENTE = os.getenv("STAGING_JWT_TOKEN_PACIENTE")

def get_id_from_token(token):
    if not token: return None
    payload_b64 = token.split(".")[1]
    payload_b64 += "=" * ((4 - len(payload_b64) % 4) % 4)
    payload = json.loads(base64.urlsafe_b64decode(payload_b64))
    return payload.get("id")

TARGET_DOCTOR_ID = get_id_from_token(TOKEN_MEDICO)
TARGET_PACIENTE_ID = get_id_from_token(TOKEN_PACIENTE)

def create_headers(token):
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }

@pytest.fixture(scope="module")
def api_contexts():
    if not TOKEN_MEDICO or not TOKEN_PACIENTE:
        pytest.fail("Faltan JWTs en .env (STAGING_JWT_TOKEN_MEDICO, STAGING_JWT_TOKEN_PACIENTE).")
        
    with sync_playwright() as p:
        medico_ctx = p.request.new_context(base_url=API_URL, extra_http_headers=create_headers(TOKEN_MEDICO))
        paciente_ctx = p.request.new_context(base_url=API_URL, extra_http_headers=create_headers(TOKEN_PACIENTE))
        
        yield {"medico": medico_ctx, "paciente": paciente_ctx}
        
        medico_ctx.dispose()
        paciente_ctx.dispose()

# ==============================================================================
# BATERÍA DE PRUEBAS API - DOCA-SEC-582 (OWASP A01, A04, A08)
# ==============================================================================

def test_doca_582_sec_01_inyectar_estado_como_medico(api_contexts):
    """
    OWASP A08 (Data Tampering): Médico intenta forzar estado 'aceptada'.
    El servidor DEBE sobreescribirlo a 'pendiente_aprobacion_paciente'.
    """
    api = api_contexts["medico"]
    payload = {
        "doctorId": TARGET_DOCTOR_ID,
        "patientId": TARGET_PACIENTE_ID,
        "date": "2026-11-20T10:00:00.000Z",
        "state": "aceptada",
        "createdByDoctor": True
    }
    
    # Endpoint validado empíricamente desde el Frontend
    response = api.post("/nuevoTurnoCheckOut", data=payload)
        
    assert response.status in [200, 201], f"Fallo en creación. Status: {response.status}. Body: {response.text()}"
    
    data = response.json()
    estado_final = data.get("stateTurno") or data.get("state") or data.get("data", {}).get("stateTurno")
    
    assert estado_final == "pendiente_aprobacion_paciente", f"Brecha Activa A08: El servidor aceptó la inyección. Estado devuelto: {estado_final}"

def test_doca_582_sec_02_inyectar_estado_como_paciente(api_contexts):
    """
    OWASP A08 (Data Tampering): Paciente intenta agendar como 'aceptada'.
    El servidor DEBE sobreescribirlo a 'pendiente'.
    """
    api = api_contexts["paciente"]
    payload = {
        "doctorId": TARGET_DOCTOR_ID,
        "date": "2026-11-20T11:00:00.000Z",
        "state": "aceptada",
        "createdByDoctor": False
    }
    
    response = api.post("/nuevoTurnoCheckOut", data=payload)
        
    assert response.status in [200, 201], f"Fallo en creación. Status: {response.status}. Body: {response.text()}"
    
    data = response.json()
    estado_final = data.get("stateTurno") or data.get("state") or data.get("data", {}).get("stateTurno")
    
    assert estado_final == "pendiente", f"Brecha Activa A08: El servidor no purificó el payload. Estado: {estado_final}"

def test_doca_582_sec_03_backdoor_occupied_turnos(api_contexts):
    """
    OWASP A01 (Broken Access Control): Intentar ocupar horario a nombre de un tercero (Paciente).
    Debe rebotar con 403.
    """
    api = api_contexts["medico"]
    payload = {
        "doctorId": TARGET_DOCTOR_ID,
        "userId": TARGET_PACIENTE_ID,
        "date": "2026-11-20T17:00:00.000Z"
    }
    
    # Asumimos que esta ruta tampoco lleva /api/ basado en la nomenclatura del proyecto
    response = api.post("/occupied-turnos", data=payload)
        
    assert response.status == 403, f"Brecha A01: El backdoor de occupied-turnos sigue abierto. Status: {response.status}. Body: {response.text()}"

def test_doca_582_sec_04_coercion_boolean(api_contexts):
    """
    OWASP A04 (Insecure Design): Coerción de tipo en createdByDoctor.
    Pasar un string 'true' no debe bypassear las validaciones.
    """
    api = api_contexts["medico"]
    payload = {
        "doctorId": TARGET_DOCTOR_ID,
        "patientId": TARGET_PACIENTE_ID,
        "date": "2026-11-20T12:00:00.000Z",
        "createdByDoctor": "true"
    }
    
    response = api.post("/nuevoTurnoCheckOut", data=payload)
        
    assert response.status in [200, 201]
    
    data = response.json()
    estado_final = data.get("stateTurno") or data.get("state") or data.get("data", {}).get("stateTurno")
    
    assert estado_final == "pendiente_aprobacion_paciente", f"Brecha A04: Fallo de Type Coercion: {estado_final}"