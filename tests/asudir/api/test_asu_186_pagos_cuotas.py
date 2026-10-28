import os
import pytest
from playwright.sync_api import sync_playwright

# ==============================================================================
# CONFIGURACIÓN BASE & ZERO TRUST (.env mapping multi-rol)
# ==============================================================================
API_URL = os.getenv("ASUDIR_API_URL")
ADMIN_TOKEN = os.getenv("STAGING_JWT_TOKEN")
U_AGUA_TOKEN = os.getenv("STAGING_USUARIO_AGUA_TOKEN")
CONTA_TOKEN = os.getenv("STAGING_USUARIO_CONTABILIDAD")
VERCEL_BYPASS = os.getenv("VERCEL_ASUDIR_BYPASS_SECRET")

# ID de cuota válido para las pruebas (Reemplazar con el ID real de la Batería 1 / 3 en Staging)
TARGET_CUOTA_ID = "jx7o65jsqxy81nzm3jnwueg7"

def create_headers(token=None):
    headers = {
        "Content-Type": "application/json",
        "x-vercel-protection-bypass": VERCEL_BYPASS
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers

@pytest.fixture(scope="module")
def api_contexts():
    """Inicializa 4 contextos: Anon (Sin Auth), Admin, Usuario Agua y Contabilidad."""
    if not API_URL or not ADMIN_TOKEN or not CONTA_TOKEN:
        pytest.fail("Faltan variables de entorno críticas. Verifica STAGING_USUARIO_CONTABILIDAD y STAGING_JWT_TOKEN.")
        
    with sync_playwright() as p:
        anon_ctx = p.request.new_context(base_url=API_URL, extra_http_headers=create_headers())
        admin_ctx = p.request.new_context(base_url=API_URL, extra_http_headers=create_headers(ADMIN_TOKEN))
        u_agua_ctx = p.request.new_context(base_url=API_URL, extra_http_headers=create_headers(U_AGUA_TOKEN))
        conta_ctx = p.request.new_context(base_url=API_URL, extra_http_headers=create_headers(CONTA_TOKEN))
        
        yield {"anon": anon_ctx, "admin": admin_ctx, "u_agua": u_agua_ctx, "conta": conta_ctx}
        
        anon_ctx.dispose()
        admin_ctx.dispose()
        u_agua_ctx.dispose()
        conta_ctx.dispose()

# ==============================================================================
# BATERÍA DE PRUEBAS API - ASU-SEC-186 (OWASP A01)
# ==============================================================================

def test_asu_186_sec_01_fuzzing_rutas_eliminadas(api_contexts):
    """
    ASU-186-SEC-01 (OWASP A04): Validar que las 7 rutas públicas fueron purgadas.
    Atacamos /generar-todas sin autenticación.
    """
    anon_api = api_contexts["anon"]
    payload = {"cicloId": 3, "forzarRecalculo": True}
    
    response = anon_api.post("/api/cuota-bateria-ciclos/generar-todas", data=payload)
    assert response.status in [404, 405], f"Brecha Activa: La ruta eliminada sigue respondiendo a mutaciones. Status: {response.status}"

def test_asu_186_sec_02_bloqueo_acceso_anonimo(api_contexts):
    """
    ASU-186-SEC-02 (OWASP A01): Un usuario sin sesión intenta registrar un pago.
    Debe rebotar con 401 Unauthorized.
    """
    anon_api = api_contexts["anon"]
    payload = {"tipo_cuota": "riego", "tipo_operacion": "pago_completo"}
    
    response = anon_api.post(f"/api/cuota-bateria-ciclos/{TARGET_CUOTA_ID}/registrar-pago", data=payload)
    assert response.status == 401, f"Brecha Activa: Se permite acceso sin sesión. Status: {response.status}"

def test_asu_186_sec_03_exclusion_superadmin(api_contexts):
    """
    ASU-186-SEC-03 (OWASP A01): El Administrador (superadmin) intenta anular un pago.
    Debe rebotar con 403 Forbidden. Valida que no se use un middleware genérico.
    """
    admin_api = api_contexts["admin"]
    # Simulamos el payload de anulación
    payload = {"transaccion_id": 999, "motivo": "Prueba de intrusión Superadmin"}
    
    response = admin_api.post(f"/api/cuota-bateria-ciclos/{TARGET_CUOTA_ID}/anular-pago", data=payload)
    assert response.status == 403, f"Brecha RBAC: El Administrador logró saltarse el filtro de Contabilidad. Status: {response.status}"

def test_asu_186_cp_01_flujo_contabilidad(api_contexts):
    """
    ASU-186-CP-01: El rol Contabilidad registra un abono legítimo.
    """
    conta_api = api_contexts["conta"]
    payload = {"tipo_cuota": "riego", "tipo_operacion": "abono", "monto": 500.50}
    
    response = conta_api.post(f"/api/cuota-bateria-ciclos/{TARGET_CUOTA_ID}/registrar-pago", data=payload)
    
    # Si la cuota ya está pagada o el id es inválido, el backend podría arrojar 400. 
    # Nos interesa confirmar que la barrera de Auth (401/403) fue superada.
    assert response.status not in [401, 403], f"Fallo de Permisos: Contabilidad fue bloqueado. Status: {response.status}"