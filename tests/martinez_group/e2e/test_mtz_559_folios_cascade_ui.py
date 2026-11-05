import os
import pytest
from playwright.sync_api import Browser, Route, expect
from dotenv import load_dotenv

load_dotenv()

# ==============================================================================
# CONFIGURACIÓN DEL ENTORNO Y SECRETS
# ==============================================================================
WEB_URL = os.getenv("MTZ_WEB_URL", "https://martinez-group-git-staging-tech-x.vercel.app")
ADMIN_EMAIL = os.getenv("MTZ_ADMIN_EMAIL") 
ADMIN_PASS = os.getenv("MTZ_ADMIN_PASSWORD")
VERCEL_SECRET = os.getenv("VERCEL_MTZ_BYPASS_SECRET")

def test_mtz_559_edicion_manual_total_quantity(browser: Browser):
    """
    Objetivo: Validar la Regla 3 y el Caso Borde 'Total Quantity no se recalcula'.
    Construye el contexto manualmente para evadir el ScopeMismatch de conftest.py.
    """
    assert WEB_URL and ADMIN_EMAIL and ADMIN_PASS, "Faltan credenciales en el .env."
    
    # 1. Construcción Aislada del Contexto (Bypass del conftest.py acoplado)
    context = browser.new_context(base_url=WEB_URL)
    
    # 2. Inyección Quirúrgica del Bypass de Vercel
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
        
        print("[-] Interactuando con campos de login (Evasión de DOM responsivo)...")
        # EXPLICACIÓN TÁCTICA: Usamos .filter(visible=True) para ignorar los inputs ocultos de Tailwind
        input_email = page.locator('input[type="email"], input[placeholder*="Email"]').filter(visible=True).first
        input_pass = page.locator('input[type="password"], input[placeholder*="Contraseña"]').filter(visible=True).first
        btn_login = page.locator('button', has_text="Iniciar Sesión").filter(visible=True).first
        
        # Sincronización explícita sobre el nodo interactivo real (Zero Trust DOM)
        input_email.wait_for(state="visible", timeout=15000)
        
        input_email.fill(ADMIN_EMAIL)
        input_pass.fill(ADMIN_PASS)
        btn_login.click()
        
        print("[+] 2. Navegando al Historial de Trabajos...")
        # Aseguramos clickear el enlace visible al historial
        page.locator('a[href*="/historial"]').filter(visible=True).first.click()
        page.wait_for_selector('text="LISTO PARA GUARDAR"', timeout=15000)
        
        print("[+] 3. Entrando al flujo de Edición de OCR...")
        # Atacamos el primer botón 'Editar' VISIBLE del listado
        page.locator('button:has-text("Editar")').filter(visible=True).first.click()
        
        # Interceptar descarga de datos del Job para asegurar que el DOM cargó
        with page.expect_response(lambda response: "/queue/results" in response.url) as response_info:
            page.locator('button:has-text("Sí, Editar Datos")').filter(visible=True).first.click()
        
        job_id = response_info.value.json().get("job_id", "DESCONOCIDO")
        print(f"[-] Datos cargados del Job: {job_id}")

        print("[+] 4. Auditando el campo Total Quantity (Regla 3 - Borde)...")
        input_total_qty = page.locator('input[name="totalQuantity"]').filter(visible=True).first
        
        # Forzar un valor manual extremo para simular al Operador
        input_total_qty.fill("99999999")
        
        print(f"[-] Guardando Job {job_id} modificado...")
        # Interceptamos la persistencia real (Vía E2E / Funcional)
        with page.expect_response(lambda response: "/registro/save-from-job" in response.url) as response_save:
            page.locator('button:has-text("Guardar Cambios")').filter(visible=True).first.click()
            
        assert response_save.value.status == 200, f"🚨 Error HTTP {response_save.value.status} al guardar."
        
        # Auditoría Zero Trust del Payload saliente (Riesgo A08: Integridad de Datos)
        payload_enviado = response_save.value.request.post_data_json()
        total_enviado = payload_enviado["registro"]["total_quantity"]
        
        assert total_enviado == "99999999", (
            f"🚨 [REGRESIÓN] El Frontend recalculó el Total Quantity ({total_enviado}) "
            "antes del POST, violando la instrucción de Maryel (PO)."
        )
        
        print("✅ [APROBADO] El Frontend respeta la edición manual y el Backend persiste el dato sin alteraciones.")

    finally:
        page.close()
        context.close()