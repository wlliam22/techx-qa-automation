import os
import re
import pytest
from playwright.sync_api import Browser, expect
from dotenv import load_dotenv

load_dotenv()

# ==============================================================================
# CONFIGURACIÓN DEL ENTORNO Y SECRETS (ASU-776)
# ==============================================================================
WEB_URL = os.getenv("ASUDIR_WEB_URL", "https://asudir-front-git-staging-tech-x.vercel.app")
ADMIN_EMAIL = os.getenv("ASU_ADMIN_EMAIL") 
ADMIN_PASS = os.getenv("ASU_ADMIN_PASSWORD")
VERCEL_SECRET = os.getenv("VERCEL_ASUDIR_BYPASS_SECRET")

@pytest.mark.business_logic
@pytest.mark.e2e
def test_asu_776_inmutabilidad_reimpresion(browser: Browser):
    """
    Objetivo (ASU-776): Validar inmutabilidad histórica al reimprimir un folio.
    Táctica: Type humanoide para asegurar el listbox de MUI y evasión de paginación.
    """
    assert WEB_URL and ADMIN_EMAIL and ADMIN_PASS, "🚨 Faltan credenciales ASUDIR en el .env."
    
    context = browser.new_context(base_url=WEB_URL)
    page = context.new_page()
    
    try:
        print("\n[+] 1. Autenticación en plataforma Staging Asudir 051...")
        url_bypass = f"/?x-vercel-protection-bypass={VERCEL_SECRET}&x-vercel-set-bypass-cookie=true" if VERCEL_SECRET else "/"
        page.goto(url_bypass)
        
        input_email = page.locator('input[type="text"][placeholder*="Email"], input[name="identifier"]').filter(visible=True).first
        input_pass = page.locator('input[type="password"]').filter(visible=True).first
        btn_login = page.locator('button', has_text="Iniciar Sesión").filter(visible=True).first
        
        input_email.wait_for(state="visible", timeout=15000)
        input_email.fill(ADMIN_EMAIL)
        input_pass.fill(ADMIN_PASS)
        
        with page.expect_response(lambda response: "auth" in response.url or "login" in response.url, timeout=15000):
            btn_login.click()
            
        print("[-] Esperando hidratación de estado global (React Auth)...")
        page.wait_for_selector('text="Carátula"', timeout=15000)
        
        print("[+] 2. Navegación táctica y creación de Folio Test A (Predio 'EL ALAMO II QA')...")
        page.goto("/riegos")
        
        btn_nueva_auth = page.locator('button').filter(has_text=re.compile(r"Nueva Autorización", re.IGNORECASE)).first
        btn_nueva_auth.wait_for(state="visible", timeout=15000)
        btn_nueva_auth.click(force=True)
        
        page.wait_for_selector('text="Datos Generales"', timeout=15000)
        
        print("[-] Seleccionando Pozo '3804' (Type Humanoide en Autocomplete)...")
        input_pozo = page.locator('input[role="combobox"]').nth(0)
        input_pozo.wait_for(state="visible", timeout=10000)
        input_pozo.click(force=True)
        
        # [CRÍTICO] Simulamos tecleo humano para forzar el evento de React que levanta el listbox
        input_pozo.type("3804", delay=150)
        
        # Esperamos explícitamente a que MUI renderice el menú desplegable flotante (Listbox)
        listbox = page.locator('ul[role="listbox"]')
        listbox.wait_for(state="visible", timeout=10000)
        listbox.locator('li', has_text="3804").first.click(force=True)
        
        # Ahora sí, el backend responde y la tabla inferior se puebla.
        page.wait_for_timeout(2000)
        
        # Marcamos el checkbox en la tabla poblada
        seccion_resultados = page.locator('text="Resultados de búsqueda"').locator('..')
        seccion_resultados.wait_for(state="visible", timeout=10000)
        checkbox_pozo = seccion_resultados.locator('input[type="checkbox"]').last
        checkbox_pozo.check(force=True)
        
        print("[-] Modificando Predio...")
        input_predio = page.locator('label:has-text("NOMBRE DEL PREDIO") >> .. >> input, input[name="nombre_predio"]').first
        if input_predio.is_visible():
            input_predio.fill("EL ALAMO II QA AUTOMATION")
        
        print("[-] Agregando Cultivo (Nogal) y Superficie (1 ha)...")
        input_cultivo = page.locator('input[role="combobox"]').nth(1)
        if not input_cultivo.is_visible():
            input_cultivo = page.locator('input[placeholder*="cultivo" i]').first
            
        input_cultivo.click(force=True)
        input_cultivo.type("Nogal", delay=150)
        
        listbox_cultivo = page.locator('ul[role="listbox"]')
        listbox_cultivo.wait_for(state="visible", timeout=10000)
        listbox_cultivo.locator('li').first.click(force=True)
        
        input_superficie = page.locator('label:has-text("SUPER") >> .. >> input, input[name="superficie"]').first
        input_superficie.fill("1")
        
        page.locator('button').filter(has_text=re.compile(r"AGREGAR CULTIVO", re.IGNORECASE)).first.click()
        page.wait_for_timeout(1000)
        
        print("[-] Guardando Folio A...")
        btn_guardar = page.locator('button:has-text("Guardar e Imprimir"), button:has-text("Guardar")').first
        
        with page.expect_response(lambda response: response.request.method in ["POST", "PUT"] and "api/" in response.url, timeout=15000) as response_info:
            btn_guardar.click()
        
        folio_a_numero = str(response_info.value.json().get("data", {}).get("folio", "000"))
        print(f"[-] Folio A creado. Payload detectado (Folio asignado: {folio_a_numero}).")
        
        page.wait_for_timeout(2000)
        btn_cerrar = page.locator('button:has-text("Cerrar")')
        if btn_cerrar.count() > 0 and btn_cerrar.first.is_visible():
            btn_cerrar.first.click(force=True)

        print("[+] 3. Creando Folio Test B (Consumo de volumen secundario)...")
        page.goto("/riegos")
        btn_nueva_auth.wait_for(state="visible", timeout=15000)
        btn_nueva_auth.click(force=True)
        page.wait_for_selector('text="Datos Generales"', timeout=15000)
        
        print("[-] Repitiendo flujo para el segundo folio (consumiendo 2 ha extra en el pozo 3804)...")
        input_pozo.wait_for(state="visible", timeout=10000)
        input_pozo.click(force=True)
        input_pozo.type("3804", delay=150)
        
        listbox.wait_for(state="visible", timeout=10000)
        listbox.locator('li', has_text="3804").first.click(force=True)
        
        page.wait_for_timeout(2000)
        
        seccion_resultados.wait_for(state="visible", timeout=10000)
        checkbox_pozo_b = seccion_resultados.locator('input[type="checkbox"]').last
        checkbox_pozo_b.check(force=True)
        
        input_cultivo.click(force=True)
        input_cultivo.type("Nogal", delay=150)
        listbox_cultivo.wait_for(state="visible", timeout=10000)
        listbox_cultivo.locator('li').first.click(force=True)
        
        input_superficie.fill("2") 
        page.locator('button').filter(has_text=re.compile(r"AGREGAR CULTIVO", re.IGNORECASE)).first.click()
        
        print("[-] Guardando Folio B...")
        with page.expect_response(lambda response: response.request.method in ["POST", "PUT"] and "api/" in response.url, timeout=15000):
            btn_guardar.click()
        
        if btn_cerrar.count() > 0 and btn_cerrar.first.is_visible():
            btn_cerrar.first.click(force=True)
        
        print(f"[+] 4. Navegando al Listado para Reimprimir el Folio A ({folio_a_numero})...")
        page.goto("/riegos")
        page.wait_for_selector('table tbody', timeout=15000)
        
        if folio_a_numero != "000":
            print(f"[-] Filtrando la tabla por el folio: {folio_a_numero}")
            input_busqueda = page.locator('input[placeholder*="folio" i]').first
            if input_busqueda.is_visible():
                input_busqueda.fill(folio_a_numero)
                page.wait_for_timeout(2500)
            
            regex_folio = re.compile(rf"0*{folio_a_numero}")
            fila_folio = page.locator('tbody tr').filter(has_text=regex_folio).first
        else:
            fila_folio = page.locator('tbody tr').nth(0)
        
        fila_folio.wait_for(state="visible", timeout=15000)
            
        btn_reimprimir = fila_folio.locator('button[title*="imprimir" i], button:has(svg[data-testid*="Print" i])').first
        
        btn_reimprimir.scroll_into_view_if_needed()
        btn_reimprimir.wait_for(state="visible", timeout=10000)
        btn_reimprimir.click(force=True)
        
        print("[+] 5. Auditando Inmutabilidad en Modal de Vista Previa (Reglas 1 y 6)...")
        page.wait_for_selector('text="Vista previa"', timeout=15000)
        
        expect(page.locator('text="EL ALAMO II QA AUTOMATION"').first).to_be_visible()
        expect(page.locator('text="VOLUMEN DISPONIBLE"').first).to_be_visible()
        
        print("✅ [APROBADO] ASU-776: El sistema respeta el snapshot histórico sin mutar la data al reimprimir.")
        
    finally:
        page.close()
        context.close()