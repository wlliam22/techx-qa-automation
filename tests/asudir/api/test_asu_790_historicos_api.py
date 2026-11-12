import os
import pytest
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

load_dotenv()

# ==============================================================================
# CONFIGURACIÓN BASE & ZERO TRUST (.env mapping)
# ==============================================================================
API_URL = os.getenv("ASUDIR_API_URL", "https://back-staging.asudir051.com")
TOKEN_ADMIN = os.getenv("STAGING_JWT_TOKEN_ADMINISTRACION")
TOKEN_JURIDICO = os.getenv("STAGING_JWT_TOKEN_JURIDICO") 
TOKEN_AGUA = os.getenv("STAGING_JWT_AGUA_TOKEN")

# Coordenadas exactas extraídas del cURL de Staging
CICLO_CERRADO_ID = "vvda8s5jqskp6c6klyu3l3zq" # Ej. 2024-2025
CICLO_ACTIVO_ID = "s4h2vobk1iukm91azkf968nr" # Reemplazar con el ID real de Staging
POZO_CEDENTE = "x48p1wajjbkgwn5crd0r57zi"
POZO_RECEPTOR = "kporx91wb2xmlgszj1whh1kq"
USUARIO_CEDENTE = "glkdo2q8kp17fiywd6qz29z2"
USUARIO_RECEPTOR = "ta635314v7efrf9472tmga8h"

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
    if not TOKEN_ADMIN:
        pytest.fail("🚨 [ERROR] Faltan JWTs en .env para Asudir 051.")
        
    with sync_playwright() as p:
        admin_ctx = p.request.new_context(base_url=API_URL, extra_http_headers=create_headers(TOKEN_ADMIN))
        juridico_ctx = p.request.new_context(base_url=API_URL, extra_http_headers=create_headers(TOKEN_JURIDICO)) if TOKEN_JURIDICO else None
        agua_ctx = p.request.new_context(base_url=API_URL, extra_http_headers=create_headers(TOKEN_AGUA)) if TOKEN_AGUA else None
        
        yield {"admin": admin_ctx, "juridico": juridico_ctx, "agua": agua_ctx}
        
        admin_ctx.dispose()
        if juridico_ctx: juridico_ctx.dispose()
        if agua_ctx: agua_ctx.dispose()

def get_base_payload():
    return {
        "data": {
            "pozo_cedente": POZO_CEDENTE,
            "pozo_receptor": POZO_RECEPTOR,
            "usuario_cedente": USUARIO_CEDENTE,
            "usuario_receptor": USUARIO_RECEPTOR,
            "volumen_cedido": 10000,
            "ciclo_agricola": CICLO_CERRADO_ID,
            "fecha_transmision": "2025-10-15", # Ajustar a una fecha válida del ciclo cerrado
            "nombre_predio_cedente": "TERRENATE",
            "nombre_predio_receptor": "SAN EDUARDO"
        }
    }

# ==============================================================================
# BATERÍA DE PRUEBAS API - ASU-790 (Shift-Left)
# Endpoint: POST /api/transmision-historicas
# ==============================================================================

@pytest.mark.security
def test_asu_790_sec_01_roles_no_autorizados(api_contexts):
    """
    OWASP A01 (AC 16): Jurídico y Usuario de Agua intentan registrar un histórico.
    DEBEN recibir 403 Forbidden.
    """
    payload = get_base_payload()
    
    # 1. Test Usuario de Agua
    if api_contexts["agua"]:
        res_agua = api_contexts["agua"].post("/api/transmision-historicas", data=payload)
        assert res_agua.status == 403, f"🚨 Brecha A01: Usuario de Agua saltó el 403. Status: {res_agua.status}"
    
    # 2. Test Jurídico
    if api_contexts["juridico"]:
        res_juridico = api_contexts["juridico"].post("/api/transmision-historicas", data=payload)
        assert res_juridico.status == 403, f"🚨 Brecha A01: Jurídico saltó el 403. Status: {res_juridico.status}"
        
    print("✅ [APROBADO] A01: Roles bloqueados correctamente en el nuevo endpoint.")

@pytest.mark.security
def test_asu_790_sec_02_inyeccion_ciclo_activo(api_contexts):
    """
    OWASP A08 (AC 4): Admin inyecta ciclo activo en un registro histórico.
    DEBE recibir 400 Bad Request ("Solo se pueden registrar traspasos históricos en ciclos cerrados").
    """
    api = api_contexts["admin"]
    payload = get_base_payload()
    payload["data"]["ciclo_agricola"] = CICLO_ACTIVO_ID
    
    response = api.post("/api/transmision-historicas", data=payload)
    
    assert response.status in [400, 403], f"🚨 Brecha A08 ACTIVA: Se permitió histórico en ciclo activo. Status: {response.status}"
    
    msg = str(response.text()).lower()
    assert "cerrado" in msg, f"Mensaje de validación de ciclo cerrado ausente: {msg}"

@pytest.mark.business_logic
@pytest.mark.parametrize("volumen, expect_success", [
    (600000, True),  # 600 MM3 (AC 5: Mayor a la dotación, debe pasar sin validar límite)
    (0, False),      # 0 MM3 (AC 5: Rechazado)
    (-5000, False)   # Negativo (AC 5: Rechazado)
])
def test_asu_790_ec_01_volumen_limites(api_contexts, volumen, expect_success):
    """
    AC 5: Volumen > 0, sin tope máximo validado contra el pozo.
    """
    api = api_contexts["admin"]
    payload = get_base_payload()
    payload["data"]["volumen_cedido"] = volumen
    
    response = api.post("/api/transmision-historicas", data=payload)
    
    if expect_success:
        assert response.status in [200, 201], f"Fallo al guardar volumen infinito {volumen}. Body: {response.text()}"
        id_creado = response.json().get("data", {}).get("id")
        if id_creado:
            api.delete(f"/api/transmision-historicas/{id_creado}")
    else:
        assert response.status == 400, f"Se permitió volumen inválido {volumen}. Status: {response.status}"

@pytest.mark.business_logic
@pytest.mark.parametrize("fecha, expect_success", [
    ("2024-10-01", True),  # Límite inferior válido (Ejemplo de fechas del ciclo cerrado)
    ("2025-09-30", True),  # Límite superior válido
    ("2024-09-30", False), # Fuera por debajo (AC 6)
    ("2025-10-01", False), # Fuera por arriba (AC 6)
])
def test_asu_790_ec_02_fechas_ciclo(api_contexts, fecha, expect_success):
    """
    AC 6: Fechas estrictamente dentro del ciclo cerrado.
    *Nota: Modifica las fechas del array parametrizado a las reales del ciclo vvda...*
    """
    api = api_contexts["admin"]
    payload = get_base_payload()
    payload["data"]["fecha_transmision"] = fecha
    
    response = api.post("/api/transmision-historicas", data=payload)
    
    if expect_success:
        assert response.status in [200, 201], f"Fallo fecha válida {fecha}. Body: {response.text()}"
        id_creado = response.json().get("data", {}).get("id")
        if id_creado:
            api.delete(f"/api/transmision-historicas/{id_creado}")
    else:
        assert response.status == 400, f"Se permitió fecha fuera de rango {fecha}. Status: {response.status}"

@pytest.mark.business_logic
def test_asu_790_ec_03_mismo_pozo(api_contexts):
    """
    AC 7: Pozo cedente no puede ser el mismo que el receptor.
    """
    api = api_contexts["admin"]
    payload = get_base_payload()
    payload["data"]["pozo_receptor"] = POZO_CEDENTE # Inyectamos colisión
    
    response = api.post("/api/transmision-historicas", data=payload)
    
    assert response.status == 400, f"Brecha de lógica: Se permitió auto-transmisión. Status {response.status}"