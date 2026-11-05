import os
import pytest
import requests
from dotenv import load_dotenv

load_dotenv()

# ==============================================================================
# CONFIGURACIÓN DEL ENTORNO Y SECRETS (Zero Trust)
# ==============================================================================
API_URL = os.getenv("DOCA_API_URL")
TOKEN_PACIENTE = os.getenv("STAGING_JWT_TOKEN_PACIENTE")

# Variables estandarizadas del .env
ID_PACIENTE = os.getenv("DOCA_ID_PACIENTE_A")
ID_DOCTOR = os.getenv("DOCA_ID_DOCTOR")
SERVICE_ID_CARO = os.getenv("SERVICE_ID_CARO")

# Necesitas capturar el ID de pago real de Stripe tras pagar el servicio barato
PAYMENT_ID_BARATO = os.getenv("STRIPE_PAYMENT_ID_BARATO", "adv_pay_xxxxx")

HEADERS = {
    "Authorization": f"Bearer {TOKEN_PACIENTE}",
    "Content-Type": "application/json",
}

@pytest.mark.security
def test_doca_sec_03_stripe_price_tampering():
    """
    Objetivo: Validar que el backend rechaza un agendamiento si el ID de pago 
    no coincide con el precio/servicio solicitado.
    Vulnerabilidad objetivo: OWASP A04 (Insecure Design - Business Logic).
    """
    assert API_URL, "CRÍTICO: DOCA_API_URL no configurado."
    assert TOKEN_PACIENTE, "CRÍTICO: STAGING_JWT_TOKEN_PACIENTE no configurado."
    assert ID_PACIENTE and ID_DOCTOR, "CRÍTICO: IDs de Paciente y Doctor no configurados."
    assert SERVICE_ID_CARO, "CRÍTICO: SERVICE_ID_CARO no configurado."
    assert PAYMENT_ID_BARATO != "adv_pay_xxxxx", "CRÍTICO: Inyecta un Payment ID real de Stripe en STRIPE_PAYMENT_ID_BARATO."

    url = f"{API_URL}/nuevoTurnoCheckOut"
    
    # Payload malicioso: Mezclamos el ID de pago de un servicio barato con el UUID de un servicio premium
    payload = {
        "user": {"id": ID_PACIENTE},
        "doctor": {"id": ID_DOCTOR},
        "turno": "2026-12-01T10:00:00.000Z", # Fecha ficticia a futuro
        "type": "Servicio Adicional",
        "slotTimezone": "America/Caracas",
        "serviceId": SERVICE_ID_CARO,
        "advancePaymentId": PAYMENT_ID_BARATO # <- EL VECTOR DE ATAQUE
    }

    print(f"\n[+] Iniciando Asalto Tampering de Stripe...")
    print(f"[+] Endpoint: POST {url}")
    print(f"[+] Inyectando Payment ID barato en Servicio Caro ({SERVICE_ID_CARO})...")

    try:
        response = requests.post(url, json=payload, headers=HEADERS, timeout=10)
    except requests.exceptions.RequestException as e:
        pytest.fail(f"🚨 Falla crítica de conexión: {e}")
    
    print(f"Respuesta HTTP: {response.status_code}")

    # ASERCIÓN ZERO TRUST: Control de Entorno
    if response.status_code == 401:
        pytest.fail(f"🚨 [ERROR DE ENTORNO] Token revocado o inválido (HTTP 401). "
                    f"Recuerda que DOCA revoca sesiones anteriores. "
                    f"Actualiza el STAGING_JWT_TOKEN_PACIENTE en el .env con el de tu sesión actual. Payload: {response.text}")

    # Si pasamos el auth, el servidor DEBE abortar la transacción financiera.
    assert response.status_code in [400, 402, 403, 409], (
        f"🚨 [CRÍTICO - OWASP A04 PRICE TAMPERING CONFIRMADO]\n"
        f"El servidor respondió {response.status_code} y procesó la cita con discrepancia financiera.\n"
        f"Falla de validación en backend. Payload devuelto: {response.text[:250]}"
    )
    
    print("✅ [APROBADO] El backend validó la integridad del pago contra el servicio.")