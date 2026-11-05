import os
import pytest
import requests
from dotenv import load_dotenv

# Cargar las variables desde el archivo .env de techx-qa-automatio
load_dotenv()

# ==============================================================================
# CONFIGURACIÓN DEL ENTORNO Y SECRETS (Zero Trust)
# ==============================================================================
API_URL = os.getenv("DOCA_API_URL")

# Token de Paciente A (Atacante) e ID de Paciente B (Víctima)
TOKEN_PACIENTE_A = os.getenv("STAGING_JWT_TOKEN_PACIENTE")
ID_PACIENTE_B = os.getenv("DOCA_ID_PACIENTE")

HEADERS_PACIENTE_A = {
    "Authorization": f"Bearer {TOKEN_PACIENTE_A}",
    "Content-Type": "application/json",
    # Descomentar si Vercel bloquea el request directo
    # "x-vercel-protection-bypass": os.getenv("VERCEL_DOCA_BYPASS_SECRET") 
}

@pytest.mark.security
def test_doca_sec_01_bola_user_profile():
    """
    Objetivo: Validar que un paciente no pueda extraer el PHI de otro paciente.
    Vulnerabilidad objetivo: OWASP A01 (BOLA / IDOR).
    """
    assert API_URL, "CRÍTICO: DOCA_API_URL no configurado en el .env"
    assert TOKEN_PACIENTE_A, "CRÍTICO: STAGING_JWT_TOKEN_PACIENTE no configurado en el .env"
    assert ID_PACIENTE_B, "CRÍTICO: DOCA_ID_PACIENTE (Víctima) no configurado en el .env"

    url = f"{API_URL}/user/{ID_PACIENTE_B}"
    
    print(f"\n[+] Iniciando Asalto BOLA...")
    print(f"[+] Actor: Paciente A | Objetivo: Perfil de Paciente B ({ID_PACIENTE_B})")
    print(f"[+] GET {url}")

    try:
        response = requests.get(url, headers=HEADERS_PACIENTE_A, timeout=10)
    except requests.exceptions.RequestException as e:
        pytest.fail(f"🚨 Falla crítica de conexión en la capa de red: {e}")
    
    print(f"Respuesta HTTP: {response.status_code}")

    # ASERCIÓN ZERO TRUST: El servidor DEBE bloquear la petición (401, 403, o 404).
    assert response.status_code in [401, 403, 404], (
        f"🚨 [CRÍTICO - OWASP A01 BOLA CONFIRMADO]\n"
        f"El servidor respondió {response.status_code} permitiendo el acceso a datos ajenos.\n"
        f"Fuga de PII inminente. Payload devuelto (parcial): {response.text[:250]}..."
    )
    
    print("✅ [APROBADO] El backend bloqueó el acceso al perfil ajeno correctamente.")