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

@pytest.mark.business_logic
@pytest.mark.e2e
def test_mtz_678_qb_sku_3304001_condiciones(browser: Browser):
    """
    Objetivo (MTZ-678-CP-01):
    Validar que un packslip de Q&B del SKU 3304001 procesado en modo
    Condiciones (selector en None), llena una sola fila con folios, splits, 
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
        
        # Seleccionar Cliente Q&B utilizando su value exacto del DOM ('qb') y despachar evento React
        select_cliente = page.locator('select#clienteSelect')
        select_cliente.wait_for(state="visible", timeout=10000)
        select_cliente.select_option(value='qb')
        select_cliente.evaluate("element => { element.dispatchEvent(new Event('change', { bubbles: true })); }")
        
        # Activar panel Condiciones asegurando visibilidad del botón
        btn_condiciones = page.locator('button', has_text="Condiciones").filter(visible=True).first
        btn_condiciones.wait_for(state="visible", timeout=5000)
        btn_condiciones.click()
        
        print(f"[+] 3. Inyectando Packslip SKU 3304001 desde: {TEST_IMAGE_PATH}...")
        page.locator('input#fileInput-packslip').first.set_input_files(TEST_IMAGE_PATH)
        
        print("[+] 4. Procesando Imágenes y enviando a la cola OCR...")
        page.locator('button', has_text="Procesar").filter(visible=True).first.click()
        
        # Interceptamos el Toast de éxito visualmente confirmado
        toast_exito = page.locator('text="¡Trabajo enviado con éxito!"')
        toast_exito.wait_for(state="visible", timeout=15000)
        print("[-] Job enviado exitosamente a la cola OCR.")
        
        print("[+] 5. Polling en Historial (Vía Toast Bypass)...")
        # BYPASS UI: Clic en "Ver Historial" directo en el Toast
        btn_toast_historial = page.locator('button', has_text="Ver Historial").filter(visible=True).first
        btn_toast_historial.wait_for(state="visible", timeout=5000)
        btn_toast_historial.click()
        
        max_retries = 15
        trabajo_encontrado = False
        btn_editar_target = None
        
        for i in range(max_retries):
            print(f"    -> Intento {i+1}/{max_retries}...")
            
            # [CRÍTICO] Manejo de Amnesia SPA: Si el DOM se resetea al Home, forzamos navegación directa vía JS puro
            try:
                page.wait_for_selector('text="Historial de Trabajos"', timeout=8000)
            except Exception:
                print("    [*] SPA reseteado a Home o retrasado. Forzando navegación al Historial (JS Bypass UI)...")
                page.evaluate('''() => {
                    const link = document.querySelector('a[href*="/historial"]');
                    if(link) link.click();
                }''')
                page.wait_for_selector('text="Historial de Trabajos"', timeout=10000)

            page.wait_for_timeout(4000) # Tiempo vital para que React renderice las tarjetas
            
            # Buscamos los contenedores de las tarjetas
            cards = page.locator('div.bg-white').filter(has_text="LISTO PARA GUARDAR")
            count = cards.count()
            
            if count > 0:
                # Tomamos SIEMPRE la primera tarjeta (Job más reciente cronológicamente)
                btn_editar = cards.nth(0).locator('button', has_text="Editar")
                if btn_editar.count() > 0 and btn_editar.first.is_visible():
                    btn_editar_target = btn_editar.first
                    trabajo_encontrado = True
                    print("✅ [APROBADO] Trabajo finalizado detectado en el Historial (Job más reciente).")
                    break
            
            if i < max_retries - 1:
                print("    [*] Recargando página (reload) para actualizar la cola OCR...")
                page.reload()
                page.wait_for_timeout(3000)
            
        assert trabajo_encontrado, "🚨 [ERROR] El trabajo OCR para el SKU 3304001 no finalizó a tiempo en el Historial."
        
        print("[+] 6. Validando Nomenclatura Automática e Inmutabilidad de Datos...")
        # Forzamos el clic vía JavaScript para evadir overlays invisibles
        btn_editar_target.evaluate("node => node.click()")
        
        # 1. Esperamos la vista intermedia de Resumen ("Análisis completado")
        print("[-] Esperando vista de resumen y validando alertas...")
        btn_si_editar_resumen = page.locator('button', has_text="Sí, Editar").filter(visible=True).first
        btn_si_editar_resumen.wait_for(state="visible", timeout=15000)
        
        # Validar ausencia de avisos de nomenclatura pendiente en la vista de resumen
        expect(page.locator('text=/no está registrado en las condiciones/i')).not_to_be_visible()
        
        # 2. Clic en "Sí, Editar" para disparar el modal de confirmación
        btn_si_editar_resumen.click()
        
        # 3. Confirmar Edición en el Modal emergente
        print("[-] Confirmando modal de edición...")
        page.wait_for_selector('text="Confirmar Edición"', timeout=5000)
        page.locator('button', has_text="Sí, Editar").filter(visible=True).last.click()
        
        # 4. Ahora sí, esperamos a que cargue el "Editor de Datos Extraídos"
        print("[-] Cargando Editor de Datos Extraídos...")
        page.wait_for_selector('button:has-text("Guardar Cambios")', timeout=15000)
        page.wait_for_timeout(2000) # Pausa para que React hidrate los inputs
        
        # Aserciones de Criterio de Aceptación MTZ-678 para SKU 3304001
        print("[-] Ejecutando aserciones de reglas de negocio en inputs...")
        expect(page.locator('input[value="3304001"]').first).to_be_visible(timeout=10000)
        expect(page.locator('input[value="72"]').first).to_be_visible()
        expect(page.locator('input[value="5"]').first).to_be_visible()
        
        print("✅ [APROBADO] MTZ-678: Flujo de Condiciones procesado y validado exitosamente en UI.")
        
    finally:
        page.close()
        context.close()
    