import os
import re
import json
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeoutError
from dotenv import load_dotenv

load_dotenv()

# ==============================================================================
# CONFIGURACIÓN
# ==============================================================================
WEB_URL = os.getenv("DOCAPPOINT_WEB_URL", "https://docappoint-git-staging-tech-x.vercel.app")
PACIENTE_EMAIL = os.getenv("DOCA_PACIENTE_EMAIL")
PACIENTE_PASS = os.getenv("DOCA_PACIENTE_PASSWORD")
VERCEL_SECRET = os.getenv("VERCEL_DOCAPPOINT_BYPASS_SECRET")

OUTPUT_DIR = Path("docs/doca_flujo_paciente")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

MEDICO_PRUEBA = os.getenv("DOCA_MEDICO_PRUEBA", "Paul Lopez")

# ==============================================================================
# HELPERS
# ==============================================================================
def _bypass_vercel_and_cors(context):
    if not VERCEL_SECRET: return
    domain = "docappoint-git-staging-tech-x.vercel.app"
    context.add_cookies([{
        "name": "_vercel_jwt", "value": VERCEL_SECRET, "domain": domain, 
        "path": "/", "httpOnly": True, "secure": True, "sameSite": "None"
    }])
    context.set_extra_http_headers({
        "x-vercel-protection-bypass": VERCEL_SECRET, 
        "Origin": WEB_URL
    })
    def _route_handler(route):
        if route.request.method == "OPTIONS":
            route.fulfill(status=200, headers={"Access-Control-Allow-Origin": WEB_URL, "Access-Control-Allow-Headers": "*"})
        else:
            route.continue_()
    context.route("**/api/**", _route_handler)
    context.route("**/auth/**", _route_handler)

def _capturar_paso(page, nombre_paso, flow_data):
    print(f"   📸 Capturando: {nombre_paso}")
    safe_name = nombre_paso.replace(" ", "_").replace("→", "").replace(".", "").strip()
    screenshot_path = OUTPUT_DIR / f"screenshot_{safe_name}.png"
    page.screenshot(path=str(screenshot_path), full_page=True)
    
    try:
        aria = page.locator("body").aria_snapshot()
    except Exception:
        aria = "Error al generar Aria Snapshot"
    
    html_file = OUTPUT_DIR / f"dom_{safe_name}.html"
    html_file.write_text(page.content(), encoding="utf-8")
    
    flow_data[nombre_paso] = {
        "url": page.url,
        "screenshot": str(screenshot_path),
        "html_file": str(html_file),
        "aria_snapshot": aria,
    }

def _login_paciente(page):
    print("\n[-] Logueando como Paciente...")
    page.goto("/login", wait_until="networkidle")
    page.get_by_role("textbox", name="Ingrese aquí su correo o usuario").fill(PACIENTE_EMAIL)
    page.get_by_role("textbox", name="Ingrese aquí su contraseña").fill(PACIENTE_PASS)
    page.get_by_role("button", name="Iniciar Sesión").click()
    page.wait_for_url(lambda url: "/login" not in url, timeout=15000)
    print("✅ Login OK")

def _limpiar_filtro_ciudad(page):
    print("   → Limpiando filtro de Ciudad...")
    try:
        combos = page.get_by_role("combobox")
        ciudad_combo = combos.nth(1) 
        ciudad_combo.click()
        page.wait_for_timeout(1000)
        opcion_todas = page.get_by_role("option", name=re.compile(r"Todas las Ciudades|Todas|All", re.I)).first
        if opcion_todas.is_visible():
            opcion_todas.click()
            page.wait_for_timeout(1500)
            print("   ✅ Filtro de Ciudad limpiado.")
        else:
            page.keyboard.press("Escape")
    except Exception as e:
        print(f"   ⚠️ No se pudo limpiar el filtro: {e}")

def _flujo_agendamiento_con_pago(page, nombre_medico, flow_data):
    print(f"\n[-] Iniciando flujo para el médico: {nombre_medico}")
    
    page.goto("/citas", wait_until="networkidle")
    page.wait_for_timeout(3000)
    _limpiar_filtro_ciudad(page)
    
    search = page.get_by_role("textbox", name="Buscar por nombre o especialidad")
    search.fill(nombre_medico)
    page.wait_for_timeout(2500)
    _capturar_paso(page, "01_Busqueda_Medico", flow_data)

    try:
        link_medico = page.get_by_role("link", name=re.compile(nombre_medico, re.I)).first
        link_medico.wait_for(state="visible", timeout=10000)
        link_medico.click()
        page.wait_for_url(re.compile(r"/[a-z0-9\-]+/[a-f0-9\-]+"), timeout=15000)
        page.wait_for_timeout(3000)
        _capturar_paso(page, "02_Perfil_Medico", flow_data)
    except Exception as e:
        print(f"   🚨 No se pudo abrir el perfil: {e}")
        return

    try:
        botones_hora = page.get_by_role("button").filter(has_text=re.compile(r"^\d{2}:\d{2}$"))
        if botones_hora.count() > 0:
            botones_hora.first.click()
            page.wait_for_timeout(2000)
            _capturar_paso(page, "03_Horario_Seleccionado", flow_data)
    except Exception as e:
        print(f"   🚨 Error al seleccionar horario: {e}")
        return

    try:
        btn_agendar = page.get_by_role("button", name=re.compile(r"Agendar cita", re.I)).first
        btn_agendar.click()
        page.wait_for_timeout(3000)
        _capturar_paso(page, "04_Confirmacion_Agendamiento", flow_data)
        
        # --- FASE CRÍTICA: Clic en "Solicitar Cita" y esperar al pago ---
        btn_solicitar = page.get_by_role("button", name=re.compile(r"Solicitar Cita", re.I)).first
        if btn_solicitar.is_visible():
            print("   → Haciendo clic en 'Solicitar Cita'...")
            
            # Interceptamos las peticiones de red para ver si redirige a pasarela
            with page.expect_navigation(timeout=15000) as nav_info:
                btn_solicitar.click()
            
            # Capturar el estado post-clic
            page.wait_for_timeout(5000)
            _capturar_paso(page, "05_Estado_Final_Agendamiento", flow_data)
            
            # Analizar si estamos en una pasarela de pago
            url_final = page.url
            if "stripe" in url_final.lower() or "mercadopago" in url_final.lower() or "pago" in url_final.lower() or "checkout" in url_final.lower():
                print(f"   💰 Redirección detectada a pasarela de pago: {url_final}")
                _capturar_paso(page, "06_Pasarela_Pago", flow_data)
            else:
                print(f"   → Estado final en: {url_final}")
                _capturar_paso(page, "06_Estado_Post_Solicitud", flow_data)

    except Exception as e:
        print(f"   🚨 Error al procesar la cita: {e}")

def main():
    if not PACIENTE_EMAIL or not PACIENTE_PASS:
        raise ValueError("🚨 Faltan credenciales de Paciente en el .env")

    flow_data = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(base_url=WEB_URL, ignore_https_errors=True)
        _bypass_vercel_and_cors(context)
        page = context.new_page()

        try:
            _login_paciente(page)
            _flujo_agendamiento_con_pago(page, MEDICO_PRUEBA, flow_data)
        except Exception as e:
            print(f"🚨 Error global en el flujo: {e}")
            page.screenshot(path=str(OUTPUT_DIR / "error_flujo.png"))
        finally:
            browser.close()

    print("\n[-] Generando documento de mapeo...")
    md = "# 🗺️ Mapa de Flujo: Agendamiento de Paciente CON Pago (Docappoint)\n\n"
    for nombre, data in flow_data.items():
        md += f"## 📍 {nombre}\n\n"
        md += f"- **URL:** `{data['url']}`\n"
        md += f"- **HTML:** `{data['html_file']}`\n\n"
        md += "### 🎭 Aria Snapshot\n```yaml\n"
        lines = data["aria_snapshot"].split("\n")
        md += "\n".join(lines[:70])
        if len(lines) > 70:
            md += f"\n... ({len(lines) - 70} líneas más)\n"
        md += "\n```\n\n---\n\n"
    
    md_file = OUTPUT_DIR / "flujo_paciente_con_pago_mapa.md"
    md_file.write_text(md, encoding="utf-8")
    print(f"✅ Documento generado: {md_file}")

if __name__ == "__main__":
    main()