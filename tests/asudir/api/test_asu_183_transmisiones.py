import os
import pytest
from playwright.sync_api import sync_playwright

# ==============================================================================
# CONFIGURACIÓN BASE & ZERO TRUST (.env mapping)
# ==============================================================================
API_URL = os.getenv("ASUDIR_API_URL")
ADMIN_TOKEN = os.getenv("STAGING_JWT_TOKEN")
VERCEL_BYPASS = os.getenv("VERCEL_ASUDIR_BYPASS_SECRET")

HEADERS = {
    "Authorization": f"Bearer {ADMIN_TOKEN}",
    "Content-Type": "application/json",
    "x-vercel-protection-bypass": VERCEL_BYPASS
}

@pytest.fixture(scope="module")
def api_context():
    """Inicializa el request context de Playwright."""
    if not API_URL or not ADMIN_TOKEN:
        pytest.fail("Faltan variables de entorno críticas en el .env (ASUDIR_API_URL o STAGING_JWT_TOKEN).")
        
    with sync_playwright() as p:
        request_context = p.request.new_context(
            base_url=API_URL,
            extra_http_headers=HEADERS
        )
        yield request_context
        request_context.dispose()

# ==============================================================================
# BATERÍA DE PRUEBAS DE SEGURIDAD (OWASP) Y REGRESIÓN
# ==============================================================================

def test_asu_183_sec_01_volume_tampering(api_context):
    """
    ASU-183-SEC-01 (OWASP A04 - Insecure Design): 
    Inyección de payload exacto interceptado del front, con Volumen Tampering.
    """
    # DTO extraído estrictamente del cURL de Staging.
    payload = {
        "data": {
            "ciclo_agricola": "s4h2vobk1iukm91azkf968nr",
            "volumen_cedido": 9999999, # <- TAMPERING: Excediendo capacidad lógica
            "firma": "ñññ",
            "pozo_cedente": "e3z2778vdcwb5eoqebz2tfiq",
            "usuario_cedente": "i5sqcmp5884zltdxykgacaii",
            "pozo_receptor": "sgxox2h4stmb5s3mdqw1wx1f",
            "usuario_receptor": "okcufd5aomk516odil3vzlka",
            "fecha_transmision": "2026-10-26",
            "nombre_predio_cedente": "EL FUNDADOR",
            "nombre_predio_receptor": "SANTA PATRICIA",
            "estado": "completada"
        }
    }

    # Usamos el endpoint exacto del cURL (Strapi v4 router nativo)
    response = api_context.post("/api/transmisions?populate=*", data=payload)
    
    # Aserción: El servidor debe rechazar la operación por fondos insuficientes, NO por esquema inválido.
    assert response.status == 400, f"Status Code inesperado: {response.status}. Respuesta: {response.text()}"
    
    response_body = response.json()
    error_message = response_body.get("error", {}).get("message", "")
    
    assert "No tiene volumen suficiente" in error_message, f"Vulnerabilidad detectada o validación ausente. Mensaje: {error_message}"


def test_asu_183_sec_02_state_mutation(api_context):
    """
    ASU-183-SEC-02 (OWASP A08 - Software and Data Integrity Failures): 
    Auto-Discovery de transmisión completada y ataque de mutación de estado.
    """
    # 1. Fase de Reconocimiento: Buscar una transmisión que ya esté completada.
    get_response = api_context.get("/api/transmisions?filters[estado][$eq]=completada&pagination[pageSize]=1")
    assert get_response.ok, "Fallo al consultar transmisiones existentes para la prueba."
    
    transmisiones = get_response.json().get("data", [])
    if not transmisiones:
        pytest.skip("No hay transmisiones 'completadas' en Staging para ejecutar esta prueba de mutación.")
        
    target_document_id = transmisiones[0]["documentId"]
    
    # 2. Fase de Ataque: Forzar estado a cancelada.
    payload = {
        "data": {
            "estado": "cancelada"
        }
    }

    response = api_context.put(f"/api/transmisions/{target_document_id}", data=payload)
    
    # Aserción: El lifecycle beforeUpdate de Juan/Marcos debe interceptar esto.
    assert response.status == 400, f"Fallo de Integridad Crítico: El sistema permitió revertir una transmisión completada (Status {response.status})."
    
    response_body = response.json()
    error_message = response_body.get("error", {}).get("message", "")
    
    assert "Una transmisión completada no puede cambiar de estado" in error_message, "El candado de estado en el backend no está activo o arroja un error incorrecto."


def test_asu_183_reg_01_cuota_bateria_x1000_fix(api_context):
    """
    ASU-183-REG-01: Verificación matemática de la cuota por batería.
    Confirma la remoción del bug exponencial (x1000) en el cálculo.
    """
    # Usando la convención de pluralización spanglish inferida y documentIds simulados
    bateria_document_id = "tzz6pk4mbhjvfy0w4dqy91qp" 
    ciclo_document_id = "s4h2vobk1iukm91azkf968nr"
    
    endpoint = f"/api/cuota-bateria-ciclos?filters[bateria][documentId][$eq]={bateria_document_id}&filters[ciclo][documentId][$eq]={ciclo_document_id}"
    
    response = api_context.get(endpoint)
    
    # Si devuelve 404, significa que la ruta pluralizada de cuotas es diferente. Lo ajustaremos si falla.
    assert response.ok, f"Endpoint de cuotas no encontrado o falló. Status: {response.status}"
    
    response_body = response.json()
    cuotas = response_body.get("data", [])
    
    if not cuotas:
        pytest.skip("No se encontraron cuotas para evaluar el cálculo.")
        
    cuota = cuotas[0].get("attributes", {})
    excedente = float(cuota.get("excedente_volumetrico", 0))
    
    assert excedente == 0.0, f"Regresión Crítica: Excedente calculado en {excedente}. El fix del x1000 no está aplicando."