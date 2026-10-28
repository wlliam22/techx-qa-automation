import os
import pytest
from playwright.sync_api import sync_playwright

# ==============================================================================
# CONFIGURACIÓN BASE & ZERO TRUST (.env mapping multi-rol)
# ==============================================================================
API_URL = os.getenv("ASUDIR_API_URL")
ADMIN_TOKEN = os.getenv("STAGING_JWT_TOKEN")          # Token de superadmin
U_AGUA_TOKEN = os.getenv("STAGING_USUARIO_AGUA_TOKEN") # Token de usuario_agua
VERCEL_BYPASS = os.getenv("VERCEL_ASUDIR_BYPASS_SECRET")

def create_headers(token):
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "x-vercel-protection-bypass": VERCEL_BYPASS
    }

@pytest.fixture(scope="module")
def api_contexts():
    """Inicializa contextos de API separados para validar RBAC (OWASP A01)."""
    if not API_URL or not ADMIN_TOKEN or not U_AGUA_TOKEN:
        pytest.fail("Faltan variables de entorno críticas (Tokens o URL). Verifica tu .env.")
        
    with sync_playwright() as p:
        admin_ctx = p.request.new_context(base_url=API_URL, extra_http_headers=create_headers(ADMIN_TOKEN))
        u_agua_ctx = p.request.new_context(base_url=API_URL, extra_http_headers=create_headers(U_AGUA_TOKEN))
        
        yield {"admin": admin_ctx, "u_agua": u_agua_ctx}
        
        admin_ctx.dispose()
        u_agua_ctx.dispose()

# ==============================================================================
# BATERÍA DE PRUEBAS API - ASU-FEAT-184
# ==============================================================================

def test_asu_184_cp_01_crear_editar_pivote_central(api_contexts):
    """
    ASU-184-CP-01 [Auto-Ready]: Flujo Feliz de Creación, Edición y Preservación.
    Utiliza el DTO exacto interceptado de la UI de Staging.
    """
    admin_api = api_contexts["admin"]
    
    # 1. Creación del Cultivo (Payload exacto de Network Tab)
    payload_creacion = {
        "data": {
            "ciclo_agricola": 4,
            "Lamina": 15,
            "NombreCultivo": "NOGAL D AUTO",
            "tipo_cultivo": "perennes",
            "tipo_riego": "pivote central"
        }
    }
    
    response_post = admin_api.post("/api/cultivos", data=payload_creacion)
    assert response_post.status == 201, f"Fallo al crear el cultivo. Status: {response_post.status}. Response: {response_post.text()}"
    
    cultivo_creado = response_post.json().get("data", {})
    cultivo_document_id = cultivo_creado.get("documentId")
    
    # Verificación de persistencia inicial
    assert cultivo_creado.get("attributes", {}).get("tipo_riego") == "pivote central", "El tipo de riego guardado no coincide con 'pivote central'."
    
    # 2. Edición Parcial (Validar inmutabilidad de otros campos al actualizar)
    payload_edicion = {
        "data": {
            "Lamina": 20
        }
    }
    
    response_put = admin_api.put(f"/api/cultivos/{cultivo_document_id}", data=payload_edicion)
    assert response_put.ok, f"Fallo al actualizar la lámina. Status: {response_put.status}"
    
    cultivo_actualizado = response_put.json().get("data", {}).get("attributes", {})
    
    # Verificación de inmutabilidad
    assert cultivo_actualizado.get("Lamina") == 20, "La lámina no se actualizó."
    assert cultivo_actualizado.get("tipo_riego") == "pivote central", "Al editar otro campo, el backend borró o alteró 'pivote central'."
    
    # Teardown (Limpieza del dato de prueba en Staging)
    admin_api.delete(f"/api/cultivos/{cultivo_document_id}")


def test_asu_184_sec_01_rbac_usuario_agua(api_contexts):
    """
    ASU-184-SEC-01 (OWASP A01) [Auto-Ready]: Inyección de Cultivo por Rol No Autorizado.
    Validar que la protección exista en backend y no solo ocultando el menú en frontend.
    """
    u_agua_api = api_contexts["u_agua"]
    
    # Payload con la estructura correcta confirmada
    payload = {
        "data": {
            "ciclo_agricola": 4,
            "Lamina": 10,
            "NombreCultivo": "INYECCION ILEGAL",
            "tipo_cultivo": "perennes",
            "tipo_riego": "pivote central"
        }
    }
    
    response = u_agua_api.post("/api/cultivos", data=payload)
    
    # Aserción DevSecOps: El servidor debe proteger la ruta.
    assert response.status in [401, 403], f"🚨 BRECHA A01 CRÍTICA: El usuario_agua pudo crear un cultivo saltándose la UI. Status devuelto: {response.status}."