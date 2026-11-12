import os
import pytest
from playwright.sync_api import Browser, expect
from dotenv import load_dotenv

load_dotenv()

# ==============================================================================
# CONFIGURACIÓN DEL ENTORNO Y SECRETS (DOCA-801 UI)
# ==============================================================================
WEB_URL = os.getenv("DOCAPPOINT_WEB_URL", "https://front-staging.docappoint.com")
PACIENTE_EMAIL = os.getenv("DOCA_PATIENT_EMAIL")
PACIENTE_PASS = os.getenv("DOCA_PATIENT_PASSWORD")
VERCEL_SECRET = os.getenv("VERCEL_DOCAPPOINT_BYPASS_SECRET")

@pytest.mark.e2e
def test_doca_801_ui_01_formato_izquierdo_y_sangria(browser: Browser):
    """
    AC 1: La pantalla de Términos (vista pública de Paciente) debe tener alineación 
    a la izquierda (no centrada) y las listas deben tener sangría (margin-left/padding-left).
    """
    assert WEB_URL and PACIENTE_EMAIL and PACIENTE_PASS, "🚨 Faltan credenciales DOCA."
    
    context = browser.new_context(base_url=WEB_URL)
    page = context.new_page()
    
    try:
        url_bypass = f"/?x-vercel-protection-bypass={VERCEL_SECRET}&x-vercel-set-bypass-cookie=true" if VERCEL_SECRET else "/"
        page.goto(url_bypass)
        
        # 1. Login
        page.goto("/login")
        page.locator('input#identifier, input[name="identifier"]').wait_for(state="visible", timeout=15000)
        page.locator('input#identifier, input[name="identifier"]').fill(PACIENTE_EMAIL)
        page.locator('input#password, input[name="password"]').fill(PACIENTE_PASS)
        page.locator('button:has-text("Iniciar sesión"), button:has-text("Iniciar Sesión")').first.click()
        page.wait_for_url(lambda url: "/login" not in url, timeout=15000)
        
        # 2. Manejo del Modal (Si el usuario ya aceptó, esto pasará de largo automáticamente)
        print("\n[-] 1. Verificando bloqueo por modal de 'Actualización de Documentos Legales'...")
        try:
            modal_titulo = page.locator('text="Actualización de Documentos Legales"')
            modal_titulo.wait_for(state="visible", timeout=5000)
            print("       -> Modal detectado. Aceptando nuevos términos para desbloquear la UI...")
            page.locator('input[type="checkbox"]').first.check(force=True)
            page.locator('button:has-text("Aceptar y Continuar")').click()
            modal_titulo.wait_for(state="hidden", timeout=10000)
            print("       -> Modal superado con éxito.")
        except Exception:
            print("       -> No hay modal bloqueante. Continuando...")

        # 3. FIX: Navegación DIRECTA (Incursión táctica evadiendo el layout del perfil)
        print("[-] 2. Navegando directamente a la vista de Términos y Condiciones...")
        page.goto("/terminos-y-condiciones")
        page.wait_for_load_state("networkidle")
        
        print("[-] 3. Evaluando Regla CSS de Alineación Izquierda (Zero Trust CSS)...")
        # Aseguramos que el DOM cargó el título
        container = page.locator('h1, h2').first.locator('..')
        container.wait_for(state="visible", timeout=10000)
        
        # Aserción 1: Alineación (No debe estar centrado)
        text_align = container.evaluate('''(el) => window.getComputedStyle(el).textAlign''')
        assert text_align in ['start', 'left'], f"🚨 A04 UI: El texto sigue centrado o justificado. textAlign actual: {text_align}"
        
        # Aserción 2: Sangría en listas (viñetas)
        print("[-] 4. Evaluando sangría de viñetas (ul/li)...")
        list_items = page.locator('ul > li, ol > li')
        if list_items.count() > 0:
             padding_left = list_items.first.evaluate('''(el) => parseFloat(window.getComputedStyle(el).paddingLeft)''')
             margin_left = list_items.first.evaluate('''(el) => parseFloat(window.getComputedStyle(el).marginLeft)''')
             assert padding_left > 0 or margin_left > 0, "🚨 A04 UI: Las viñetas no tienen sangría aplicada."
             
        print("✅ [APROBADO] AC 1: Formato renderizado a la izquierda y con sangrías correctas.")
        
    finally:
        context.close()