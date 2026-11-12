import os
import pytest
from playwright.sync_api import Browser, expect
from dotenv import load_dotenv

load_dotenv()

# ==============================================================================
# CONFIGURACIÓN DEL ENTORNO Y SECRETS (DOCA-774 UI)
# ==============================================================================
WEB_URL = os.getenv("DOCAPPOINT_WEB_URL", "https://front-staging.docappoint.com")
PACIENTE_EMAIL = os.getenv("DOCA_PATIENT_EMAIL")
PACIENTE_PASS = os.getenv("DOCA_PATIENT_PASSWORD")
VERCEL_SECRET = os.getenv("VERCEL_DOCAPPOINT_BYPASS_SECRET")

# Datos de prueba para el script (Actualizar con un médico sin y con cobro en Staging)
MEDICO_SIN_COBRO = "wieudbf" 
MEDICO_CON_COBRO = "William Parral"

@pytest.mark.e2e
def test_doca_774_ui_01_agendar_sin_cobro_sin_modal(browser: Browser):
    """
    AC 1: Agendar cita con médico sin cobro -> No pide permiso de grabación.
    """
    assert WEB_URL and PACIENTE_EMAIL and PACIENTE_PASS, "🚨 Faltan credenciales DOCA en el .env."
    
    context = browser.new_context(base_url=WEB_URL)
    page = context.new_page()
    
    try:
        print(f"\n[+] 1. Autenticación en Docappoint Staging como Paciente...")
        url_bypass = f"/?x-vercel-protection-bypass={VERCEL_SECRET}&x-vercel-set-bypass-cookie=true" if VERCEL_SECRET else "/"
        page.goto(url_bypass)
        
        # Login (Locadores de alta precisión para MUI)
        page.goto("/login")
        
        input_usuario = page.locator('input#identifier, input[name="identifier"]')
        input_usuario.wait_for(state="visible", timeout=15000)
        input_usuario.fill(PACIENTE_EMAIL)
        
        input_password = page.locator('input#password, input[name="password"]')
        input_password.fill(PACIENTE_PASS)
        
        btn_login = page.locator('button:has-text("Iniciar sesión"), button:has-text("Iniciar Sesión")').first
        btn_login.click()
        
        # Corrección Zero Trust: Esperamos salir de /login en lugar de forzar /dashboard
        page.wait_for_url(lambda url: "/login" not in url, timeout=15000)
        
        print(f"[-] 2. Buscando perfil del {MEDICO_SIN_COBRO}...")
        page.goto("/especialistas")
        
        buscador = page.locator('input[placeholder*="Buscar"]')
        buscador.wait_for(state="visible")
        buscador.fill(MEDICO_SIN_COBRO)
        
        # FIX TÁCTICO: Bypass para el debounce de React. Obligamos una pausa dura de 2s para que el DOM se hidrate con el fetch.
        page.wait_for_timeout(2000) 
        
        resultado_medico = page.locator(f'text="{MEDICO_SIN_COBRO}"').first
        resultado_medico.wait_for(state="visible", timeout=15000)
        resultado_medico.click()
        
        print("[-] 3. Seleccionando turno disponible...")
        page.wait_for_selector('.turno-disponible', timeout=10000)
        page.locator('.turno-disponible').first.click()
        
        print("[-] 4. Presionando 'Solicitar Cita'...")
        btn_solicitar = page.locator('button:has-text("Solicitar Cita")')
        
        # Interceptamos la petición POST para verificar el payload (authorization_audio = false)
        with page.expect_response(lambda response: "turnos" in response.url and response.request.method == "POST", timeout=15000) as response_info:
            btn_solicitar.click()
            
        print("[+] 5. Verificando aserciones de interfaz y red...")
        # 1. El modal NO debe existir en el DOM
        modal_grabacion = page.locator('text="Autorización para grabación de audio"')
        expect(modal_grabacion).not_to_be_visible()
        
        # 2. Debe llevar a pantalla de éxito o 'Mis citas'
        expect(page.locator('text="Turno reservado correctamente"').or_(page.locator('text="Mis citas"'))).to_be_visible()
        
        # 3. Payload Check (Regla 1)
        req_post_data = response_info.value.request.post_data_json
        assert req_post_data.get("authorization_audio") is False or "authorization_audio" not in req_post_data, "🚨 El frontend sigue mandando authorization_audio en true."
        
        print("✅ [APROBADO] AC 1: Flujo de agendamiento estándar limpio de IA.")
        
    finally:
        page.close()
        context.close()

@pytest.mark.e2e
def test_doca_774_ui_02_reprogramacion_sin_modal(browser: Browser):
    """
    AC 4: Aceptar reprogramación de cita -> No pide permiso de grabación.
    Nota: Requiere que el paciente tenga una cita con reprogramación pendiente en Staging.
    """
    context = browser.new_context(base_url=WEB_URL)
    page = context.new_page()
    
    try:
        url_bypass = f"/?x-vercel-protection-bypass={VERCEL_SECRET}&x-vercel-set-bypass-cookie=true" if VERCEL_SECRET else "/"
        page.goto(url_bypass)
        
        # Login (Locadores de alta precisión para MUI)
        page.goto("/login")
        
        input_usuario = page.locator('input#identifier, input[name="identifier"]')
        input_usuario.wait_for(state="visible", timeout=15000)
        input_usuario.fill(PACIENTE_EMAIL)
        
        input_password = page.locator('input#password, input[name="password"]')
        input_password.fill(PACIENTE_PASS)
        
        btn_login = page.locator('button:has-text("Iniciar sesión"), button:has-text("Iniciar Sesión")').first
        btn_login.click()
        
        # Corrección Zero Trust: Esperamos salir de /login
        page.wait_for_url(lambda url: "/login" not in url, timeout=15000)
        
        print("\n[-] 1. Navegando a 'Mis Citas' buscando reprogramaciones pendientes...")
        page.goto("/paciente/mis-citas")
        
        btn_aceptar_cambio = page.locator('button:has-text("Aceptar"):visible').first
        if btn_aceptar_cambio.count() == 0:
            pytest.skip("No hay citas con propuesta de reprogramación en la cuenta de prueba.")
            
        print("[-] 2. Presionando 'Aceptar' reprogramación...")
        with page.expect_response(lambda response: response.request.method in ["PUT", "PATCH"] and "turnos" in response.url, timeout=10000):
            btn_aceptar_cambio.click()
            
        print("[+] 3. Verificando ausencia de modales intrusivos...")
        expect(page.locator('text="Autorización para grabación de audio"')).not_to_be_visible()
        expect(page.locator('text="Nueva fecha confirmada"')).to_be_visible()
        
        print("✅ [APROBADO] AC 4: Flujo de reprogramación limpio de IA.")
        
    finally:
        page.close()
        context.close()