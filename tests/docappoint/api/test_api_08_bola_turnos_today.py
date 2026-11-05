import os
import pytest
import requests
from dotenv import load_dotenv

# Cargar variables del .env
load_dotenv()

# ==============================================================================
# CONFIGURACIÓN DEL ENTORNO Y SECRETS (Zero Trust)
# ==============================================================================
API_URL = os.getenv("DOCA_API_URL")
TOKEN_PACIENTE_A = os.getenv("STAGING_JWT_TOKEN_PACIENTE")

HEADERS_PACIENTE_A = {
    "Authorization": f"Bearer {TOKEN_PACIENTE_A}",
    "Content-Type": "application/json",
}

@pytest.mark.security
def test_doca_sec_02_bola_wildcard_turnos():
    """
    Objetivo: Validar que un paciente no pueda hacer scraping de todas las citas del sistema.
    Vulnerabilidades: OWASP A01 (BOLA) y A03 (Wildcard Injection).
    """
    assert API_URL, "CRÍTICO: DOCA_API_URL no configurado en el .env"
    assert TOKEN_PACIENTE_A, "CRÍTICO: STAGING_JWT_TOKEN_PACIENTE no configurado en el .env"

    # Inyección del comodín SQL (%) URL-encoded como %25
    payload_date = "%25"
    url = f"{API_URL}/getTurnosToday?date={payload_date}"
    
    print(f"\n[+] Iniciando Asalto BOLA + Wildcard Injection...")
    print(f"[+] Actor: Paciente A | Objetivo: Extracción masiva de citas (date={payload_date})")
    print(f"[+] GET {url}")

    try:
        # Timeout extendido intencionalmente: Si hay Auto-DoS, la BD tardará en responder
        response = requests.get(url, headers=HEADERS_PACIENTE_A, timeout=15)
    except requests.exceptions.Timeout:
        pytest.fail("🚨 [CRÍTICO - OWASP A04 Auto-DoS] El servidor agotó el tiempo de respuesta. La inyección % tumbó el hilo de Node.js o saturó la BD.")
    except requests.exceptions.RequestException as e:
        pytest.fail(f"🚨 Falla crítica de conexión en la capa de red: {e}")
    
    print(f"Respuesta HTTP: {response.status_code}")

    # ASERCIÓN ZERO TRUST
    assert response.status_code in [400, 401, 403], (
        f"🚨 [CRÍTICO - BOLA / INYECCIÓN CONFIRMADA]\n"
        f"El servidor respondió {response.status_code} al payload de volcado de datos.\n"
        f"Exfiltración de PII activa. Payload devuelto (parcial): {response.text[:300]}..."
    )
    
    # Doble candado: Si por alguna razón devolvió 200 pero vacío, asegurarnos de que no hay datos
    if response.status_code == 200:
        data = response.json()
        assert len(data) == 0, "🚨 [CRÍTICO] El servidor devolvió una lista con datos clínicos a un actor no autorizado."

    print("✅ [APROBADO] El backend bloqueó el payload y el acceso global correctamente.")