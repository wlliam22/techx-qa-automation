import os
import pytest
from playwright.sync_api import Browser, Route, expect
from dotenv import load_dotenv
import time

load_dotenv()

# ==============================================================================
# CONFIGURACIÓN DEL ENTORNO Y SECRETS
# ==============================================================================
WEB_URL = os.getenv("MTZ_WEB_URL", "https://martinez-group-git-staging-tech-x.vercel.app")
ADMIN_EMAIL = os.getenv("MTZ_ADMIN_EMAIL") 
ADMIN_PASS = os.getenv("MTZ_ADMIN_PASSWORD")
VERCEL_SECRET = os.getenv("VERCEL_MTZ_BYPASS_SECRET")

# 🔥 ADVERTENCIA: La imagen debe tener FÍSICAMENTE alterado el SKU a 999999 con FUENTE DE TEXTO CLARA (Arial/Calibri)
TEST_IMAGE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../assets/chosen_packslip_999999.jpg"))

@pytest.mark.business_logic
def test_mtz_condiciones_sku_no_registrado_alerta(browser: Browser):
    """
    Objetivo: Validar que un SKU no registrado en modo Condiciones (Sesajal Chosen Foods)
    dispara el aviso de error en la vista de edición y modifica la UI (Folios sin Índice).
    Protocolo: MTZ-FEAT-COND
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
        print("\n[+] 1. Infiltración en Vercel (Auth)...")
        page.goto("/")
        
        # Login (DOM Responsivo seguro)
        input_email = page.locator('input[type="email"], input[placeholder*="Email"]').filter(visible=True).first
        input_pass = page.locator('input[type="password"], input[placeholder*="Contraseña"]').filter(visible=True).first
        btn_login = page.locator('button', has_text="Iniciar Sesión").filter(visible=True).first
        
        input_email.wait_for(state="visible", timeout=15000)
        input_email.fill(ADMIN_EMAIL)
        input_pass.fill(ADMIN_PASS)
        btn_login.click()
        
        print("[+] 2. Configurando Parámetros de Escaneo (Chosen Foods / Condiciones)...")
        # Aseguramos estar en el Dashboard de Escaneo
        page.wait_for_selector('text="Escaneo de Empaque"', timeout=15000)
        
        # Selector Cliente Principal (id="clienteSelect")
        page.locator('select#clienteSelect').select_option('sesajal')
        
        # Selector Variante Sesajal (id="sesajalSelect")
        page.locator('select#sesajalSelect').select_option('sesajal-chosen')
        
        # Activar Tab/Modo Condiciones
        page.locator('button', has_text="Condiciones").filter(visible=True).first.click()
        
        print(f"[+] 3. Inyectando Packslip Malicioso (SKU No Registrado) desde: {TEST_IMAGE_PATH}...")
        # Inyección directa de archivo forzando el primer nodo (Bypass Strict Mode)
        page.locator('input#fileInput-packslip').first.set_input_files(TEST_IMAGE_PATH)
        
        print("[+] 4. Procesando Imágenes y esperando confirmación de envío...")
        # Hacemos clic en Procesar
        page.locator('button', has_text="Procesar").filter(visible=True).first.click()
        
        # Esperamos el Toast verde inicial de éxito para confirmar que salió a la cola
        toast_exito = page.locator('text="¡Trabajo enviado con éxito!"')
        toast_exito.wait_for(state="visible", timeout=15000)
        print("[-] Job enviado exitosamente a la cola de OCR.")
        
        print("[+] 5. Polling en Historial: Esperando a que el Worker cambie a LISTO PARA GUARDAR (Max 3 mins)...")
        # 🚀 BYPASS UI: Hacemos clic en "Ver Historial" directo en el Toast para evitar el Sidebar oculto por Tailwind
        page.locator('button', has_text="Ver Historial").filter(visible=True).first.click()
        
        # Bucle de Polling: Recargar la página hasta que exista un trabajo en "LISTO PARA GUARDAR"
        max_retries = 12
        trabajo_terminado = False
        
        for i in range(max_retries):
            print(f"    -> Intento {i+1}/{max_retries}...")
            
            # Asegurar que el layout del Historial esté cargado tras el reload
            page.wait_for_selector('text="Historial de Trabajos"', timeout=15000)
            page.wait_for_timeout(4000) # Tiempo a React para fetch de /queue/my-jobs
            
            # Verificamos si existe al menos una tarjeta con "LISTO PARA GUARDAR"
            btn_editar = page.locator('button', has_text="Editar").filter(visible=True).first
            
            if btn_editar.is_visible():
                trabajo_terminado = True
                print("✅ [APROBADO] Se detectó un trabajo finalizado ('LISTO PARA GUARDAR').")
                break
            
            if i < max_retries - 1:
                time.sleep(15)
                page.reload()
            
        assert trabajo_terminado, "🚨 [ERROR] Ningún trabajo pasó a estado 'LISTO PARA GUARDAR' tras 3 minutos."
        
        print("[+] 6. Validando Alerta y Nodos de Edición Internos (Inmutabilidad)...")
        # Clic en Editar en la primera tarjeta disponible
        btn_editar.click()
        
        # Esperamos a que cargue la vista de análisis y buscamos el texto de error esperado usando Regex
        expect(page.locator('text=/no está registrado en las condiciones/i').first).to_be_visible(timeout=15000)
        print("✅ [APROBADO] Mensaje analítico de 'Producto no registrado' detectado.")
        
        # Clic en Sí, Editar (Abre el modal)
        page.locator('button', has_text="Sí, Editar").filter(visible=True).first.click()
        
        # Confirmamos la acción dentro del Modal de Advertencia
        print("[-] Confirmando advertencia de seguridad en Modal...")
        page.wait_for_selector('text="Confirmar Edición"', timeout=5000)
        page.locator('button', has_text="Sí, Editar").filter(visible=True).last.click()
        
        # Confirmamos que Folios existe en la vista de edición real
        expect(page.locator('text="Folios"')).to_be_visible(timeout=10000)
        
        # CUIDADO OWASP A08: Confirmamos que Índice NO se renderiza
        assert page.locator('text="Índice"').is_hidden() is True, "🚨 [ERROR] El campo 'Índice' está filtrándose en la UI."
        
        print("✅ [APROBADO] Componentes UI (Folios) renderizados correctamente; Índice bloqueado.")
        
    finally:
        page.close()
        context.close()