import os
import pytest
import requests
from playwright.sync_api import Page, expect
from dotenv import load_dotenv

load_dotenv()

# ==============================================================================
# CONFIGURACIÓN DEL ENTORNO
# ==============================================================================
API_URL = os.getenv("DOCA_API_URL", "https://test-docappoint.techxmx.com")
BYPASS_SECRET = os.getenv("VERCEL_DOCAPPOINT_BYPASS_SECRET")

ADMIN_EMAIL = os.getenv("DOCA_ADMIN_EMAIL")
ADMIN_PASSWORD = os.getenv("DOCA_ADMIN_PASSWORD")
DOCA_DOCTOR_EMAIL = os.getenv("DOCA_DOCTOR_EMAIL")
DOCA_DOCTOR_PASSWORD = os.getenv("DOCA_DOCTOR_PASSWORD")
DOCA_ID_DOCTOR = os.getenv("DOCA_ID_DOCTOR")

def suspender_doctor_via_api():
    """Shift-Left: Usamos 'requests' puro para suspender vía API."""
    assert ADMIN_EMAIL and ADMIN_PASSWORD, "Faltan credenciales de Admin en el .env"
    assert DOCA_ID_DOCTOR, "Falta el DOCA_ID_DOCTOR en el .env"
    
    # 1. Autologin del Administrador
    login_url = f"{API_URL}/login"
    login_resp = requests.post(login_url, json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    
    assert login_resp.status_code in [200, 201], f"Fallo al iniciar sesión como Admin vía API. HTTP {login_resp.status_code}: {login_resp.text}"
    
    token = login_resp.json().get("token") or login_resp.json().get("data", {}).get("token")
    assert token, "El endpoint de login no devolvió un token JWT."
    
    # 2. Suspender al doctor con el JWT obtenido
    suspend_url = f"{API_URL}/users/{DOCA_ID_DOCTOR}/suspend"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    suspend_resp = requests.patch(suspend_url, headers=headers)
    assert suspend_resp.status_code in [200, 204, 400], f"Fallo al suspender cuenta vía API. HTTP {suspend_resp.status_code}: {suspend_resp.text}"
    print("[-] Cuenta del doctor suspendida a nivel de base de datos.")
    return True

@pytest.mark.business_logic
@pytest.mark.security
def test_doca_651_regla2_login_rechazado_para_suspendido(patient_page: Page, base_url: str):
    """
    Objetivo: Validar Regla 2. Una cuenta suspendida no obtiene sesión.
    Se utiliza patient_page para alinearnos con la arquitectura del conftest.py local.
    """
    assert DOCA_DOCTOR_EMAIL and DOCA_DOCTOR_PASSWORD, "Faltan credenciales del doctor en .env"

    print(f"\n[+] 1. Shift-Left (Backend): Suspendiendo al Doctor {DOCA_ID_DOCTOR} vía API...")
    suspender_doctor_via_api()

    # Bypass Vercel en UI (Zero Trust en entorno Staging)
    if BYPASS_SECRET:
        patient_page.context.set_extra_http_headers({
            "x-vercel-protection-bypass": BYPASS_SECRET,
            "x-vercel-set-bypass-cookie": "true"
        })

    print("[+] 2. Validando Frontend: Intento de inicio de sesión de cuenta suspendida...")
    patient_page.goto(f"{base_url}/login")

    # Validación visual de que estamos en Login y no en Vercel Protection
    expect(patient_page.locator('button', has_text="Iniciar Sesión")).to_be_visible(timeout=15000)

    # Interceptamos la llamada de Login para validar el HTTP 403 del backend
    with patient_page.expect_response(lambda r: "/login" in r.url and r.request.method == "POST") as login_response:
        # Localizadores más amplios para eludir el problema de type/name
        patient_page.locator('input[placeholder*="correo" i], input[placeholder*="email" i], input[type="email"]').first.fill(DOCA_DOCTOR_EMAIL)
        patient_page.locator('input[placeholder*="contraseña" i], input[placeholder*="password" i], input[type="password"]').first.fill(DOCA_DOCTOR_PASSWORD)
        patient_page.locator('button', has_text="Iniciar Sesión").click()

    res = login_response.value
    data = res.json()
    
    print(f"[-] Respuesta del Backend al Login: HTTP {res.status}")
    
    # 3. Aserciones Criterios de Aceptación (OWASP A07 - Authentication Failures)
    assert res.status == 403, f"CRÍTICO: El backend no devolvió 403 Forbidden. Devolvió {res.status}"
    
    # Validamos el código de error
    assert data.get("code") == "ACCOUNT_SUSPENDED" or "suspendida" in data.get("message", "").lower(), f"El backend devolvió un código incorrecto: {data}"

    # 4. Aserciones de Frontend UI
    print("[+] 3. Verificando renderizado de la alerta exacta en UI...")
    mensaje_esperado = "Tu cuenta está suspendida. Para más información, escribe a soporte."
    
    alerta_ui = patient_page.locator(f'text="{mensaje_esperado}"').first
    expect(alerta_ui).to_be_visible(timeout=10000)
    
    assert "/login" in patient_page.url, "CRÍTICO: El usuario fue redirigido fuera del login a pesar de la suspensión."
    
    print("✅ [APROBADO] Regla 2: Login bloqueado correctamente. JWT no emitido. UI alerta coincidente.")