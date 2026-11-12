import os
import random
import pytest
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

load_dotenv()

# ==============================================================================
# CONFIGURACIÓN DEL ENTORNO Y SECRETS (DOCA-801 API)
# ==============================================================================
API_URL = os.getenv("DOCA_API_URL", "https://test-docappoint.techxmx.com")
TOKEN_ADMIN = os.getenv("STAGING_JWT_TOKEN_ADMIN")
ENDPOINT_POLITICAS = "/tyc" 

MSG_ERROR_ESPERADO = "El contenido no tiene formato. Agrega al menos un título y párrafos o listas en HTML, y revisa la vista previa antes de publicar."

def create_headers(token):
    return {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {token}"
    }

@pytest.fixture(scope="module")
def api_context():
    with sync_playwright() as p:
        if not TOKEN_ADMIN:
            pytest.skip("🚨 Faltan credenciales de Admin (TOKEN_ADMIN) en el .env.")
        api = p.request.new_context(base_url=API_URL, extra_http_headers=create_headers(TOKEN_ADMIN))
        yield api
        api.dispose()

# ==============================================================================
# MATRIZ DE ATAQUE ZERO TRUST (Payload Fuzzing)
# ==============================================================================
@pytest.mark.security
@pytest.mark.parametrize("descripcion, payload_content, expect_success", [
    ("Texto plano sin etiquetas", "Políticas de Privacidad de DocAppoint Última actualización: 30/03/2026", False),
    ("Sintaxis Markdown", "# Políticas\n- punto uno", False),
    ("Solo Título (Sin P/UL/OL)", "<h1>Política</h1>Texto suelto<br>otra línea", False),
    ("Solo Párrafos (Sin H1-H6)", "<p>Primer párrafo</p><p>Segundo</p>", False),
    ("Estructura válida básica", "<h1>Política</h1><p>Texto</p>", True),
    ("Etiquetas con mayúsculas y atributos (DOM Parser check)", '<H2 class="x">1. Datos</H2><UL><LI>Nombre</LI></UL>', True),
])
def test_doca_801_sec_01_validacion_html_backend(api_context, descripcion, payload_content, expect_success):
    """
    AC 5, 6, 7 y 8: El servidor debe rechazar estrictamente cualquier payload que no cumpla 
    con la estructura HTML mínima: al menos un <hX> y al menos un <p>, <ul> u <ol>.
    """
    # Generamos una versión dinámica (ej. 9.145) para evitar colisiones Unique Constraint en DB
    version_dinamica = f"9.{random.randint(100, 999)}"
    
    payload = {
        "type": "terms", 
        "version": version_dinamica, 
        "content": payload_content
    }
    
    response = api_context.post(ENDPOINT_POLITICAS, data=payload)
    body = response.json()
    
    if expect_success:
        assert response.status in [200, 201], f"🚨 FALSO NEGATIVO: El backend rechazó un HTML válido ({descripcion}). Status: {response.status}. Body: {body}"
        print(f"✅ [APROBADO] Payload aceptado: {descripcion} (Versión: {version_dinamica})")
    else:
        assert response.status == 400, f"🚨 ALARMA A04: El backend aceptó código basura ({descripcion}) permitiendo inyección. Status: {response.status}"
        error_msg = body.get("msg", "")
        assert error_msg == MSG_ERROR_ESPERADO, f"🚨 Mensaje de error incorrecto o genérico. \nEsperado: {MSG_ERROR_ESPERADO}\nObtenido: {error_msg}"
        print(f"✅ [APROBADO] Payload bloqueado correctamente: {descripcion}")