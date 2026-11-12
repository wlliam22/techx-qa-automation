import os
import pytest
from playwright.sync_api import Browser, Route, expect
from dotenv import load_dotenv
import time

load_dotenv()

# ==============================================================================
# CONFIGURACIÓN DEL ENTORNO Y SECRETS (MTZ-678)
# ==============================================================================
WEB_URL = os.getenv("MTZ_WEB_URL", "https://martinez-group-git-staging-tech-x.vercel.app")
ADMIN_EMAIL = os.getenv("MTZ_ADMIN_EMAIL") 
ADMIN_PASS = os.getenv("MTZ_ADMIN_PASSWORD")
VERCEL_SECRET = os.getenv("VERCEL_MTZ_BYPASS_SECRET")

# Ruta absoluta al packslip modificado para el SKU 3304001 de Q&B
TEST_IMAGE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../adjuntos/Q&Bsku3304001.jpg"))

@pytest.mark.e2e
def test_mtz_678_qb_sku_3304001_condiciones(browser: Browser):
    """
    Objetivo (MTZ-678-CP-01):
    Validar que un packslip de Q&B del SKU 3304001 con 1,440 piezas, procesado en modo
    Condiciones (selector en None), llena una sola fila con folios 1-20, splits 20A, 
    Quantity 72, Bulk 5, sin disparar avisos de nomenclatura pendiente.
    """
    assert WEB_URL and ADMIN_EMAIL and ADMIN_PASS, "Faltan credenciales MTZ en el .env."
    assert os.path.exists(TEST_IMAGE_PATH), f"No se encontró la imagen de prueba en {TEST_IMAGE_PATH}"
    
    # 1. Bypass Vercel & Context (Zero Trust)
    context = browser.new_context(base_url=WEB_URL)
    if VERCEL_SECRET:
        def vercel_bypass(route: Route):
            headers = route.request.headers.copy()
            headers["x-vercel-protection-bypass"] = VERCEL_SECRET
            headers["x-vercel-set-bypass-cookie"] = "true"
            route.continue_(headers=headers)
        context.route("**/*vercel.app/**", vercel_bypass)

    page = context.new_page()
    
    try:
        print("\n[+] 1. Autenticación en plataforma Staging Martinez Group...")
        page.goto("/")
        
        input_email = page.locator('input[type="email"], input[placeholder*="Email"]').filter(visible=True).first
        input_pass = page.locator('input[type="password"], input[placeholder*="Contraseña"]').filter(visible=True).first
        btn_login = page.locator('button', has_text="Iniciar Sesión").filter(visible=True).first
        
        input_email.wait_for(state="visible", timeout=15000)
        input_email.fill(ADMIN_EMAIL)
        input_pass.fill(ADMIN_PASS)
        btn_login.click()
        
        print("[+] 2. Configurando Parámetros de Escaneo (Q&B / Condiciones)...")
        page.wait_for_selector('text="Escaneo de Empaque"', timeout=15000)
        
        # Seleccionar Cliente Q&B utilizando su value exacto del DOM ('qb') de forma única
        select_cliente = page.locator('select#clienteSelect')
        select_cliente.wait_for(state="visible", timeout=10000)
        select_cliente.select_option(value='qb')
        
        # Activar panel Condiciones
        page.locator('button', has_text="Condiciones").filter(visible=True).first.click()
        
        print(f"[+] 3. Inyectando Packslip SKU 3304001 desde: {TEST_IMAGE_PATH}...")
        page.locator('input#fileInput-packslip').first.set_input_files(TEST_IMAGE_PATH)
        
        print("[+] 4. Procesando Imágenes y enviando a la cola OCR...")
        page.locator('button', has_text="Procesar").filter(visible=True).first.click()
        
        toast_exito = page.locator('text="¡Trabajo enviado con éxito!"')
        toast_exito.wait_for(state="visible", timeout=15000)
        print("[-] Job enviado exitosamente.")
        
        print("[+] 5. Polling en Historial: Esperando estado 'LISTO PARA GUARDAR'...")
        page.locator('button', has_text="Ver Historial").filter(visible=True).first.click()
        
        max_retries = 12
        trabajo_terminado = False
        
        for i in range(max_retries):
            print(f"    -> Intento {i+1}/{max_retries}...")
            page.wait_for_selector('text="Historial de Trabajos"', timeout=15000)
            page.wait_for_timeout(4000)
            
            btn_editar = page.locator('button', has_text="Editar").filter(visible=True).first
            if btn_editar.is_visible():
                trabajo_terminado = True
                print("✅ [APROBADO] Trabajo finalizado detectado ('LISTO PARA GUARDAR').")
                break
            
            if i < max_retries - 1:
                time.sleep(15)
                page.reload()
            
        assert trabajo_terminado, "🚨 [ERROR] El trabajo OCR no finalizó a tiempo."
        
        print("[+] 6. Validando Nomenclatura Automática e Inmutabilidad de Datos...")
        btn_editar.click()
        
        # Validar ausencia de avisos de nomenclatura pendiente
        expect(page.locator('text=/no está registrado en las condiciones/i')).not_to_be_visible()
        
        # Confirmar Edición en Modal
        page.locator('button', has_text="Sí, Editar").filter(visible=True).first.click()
        page.wait_for_selector('text="Confirmar Edición"', timeout=5000)
        page.locator('button', has_text="Sí, Editar").filter(visible=True).last.click()
        
        # Aserciones de Criterio de Aceptación MTZ-678-CP-01
        expect(page.locator('input[value="3304001"]')).to_be_visible()
        expect(page.locator('input[value="1-20"]')).to_be_visible()
        expect(page.locator('input[value="72"]')).to_be_visible()
        expect(page.locator('input[value="5"]')).to_be_visible()
        
        print("✅ [APROBADO] MTZ-678: Nomenclatura de Condiciones generada con precisión milimétrica.")
        
    finally:
        page.close()
        context.close()