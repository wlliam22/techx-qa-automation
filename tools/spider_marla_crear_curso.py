import os
import re
import json
from datetime import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeoutError
from dotenv import load_dotenv

load_dotenv()

# ==============================================================================
# CONFIGURACIÓN
# ==============================================================================
WEB_URL = os.getenv("MARLA_WEB_URL", "https://marla-diaz-videos-git-staging-tech-x.vercel.app")
ADMIN_EMAIL = os.getenv("MARLA_ADMIN_EMAIL", "admin@admin.com")
ADMIN_PASS = os.getenv("MARLA_ADMIN_PASSWORD")
VERCEL_SECRET = os.getenv("VERCEL_MARLA_BYPASS_SECRET")

# Nomenclatura versionada: run_YYYYMMDD_HHMMSS
RUN_ID = datetime.now().strftime("run_%Y%m%d_%H%M%S")
BASE_DIR = Path("docs/marla_spider")
RUN_DIR = BASE_DIR / RUN_ID
RUN_DIR.mkdir(parents=True, exist_ok=True)

# Registrar la última ejecución
(BASE_DIR / "latest_run.txt").write_text(RUN_ID, encoding="utf-8")

# ==============================================================================
# HELPERS
# ==============================================================================
def _bypass_vercel(context):
    if not VERCEL_SECRET: return
    domain = "marla-diaz-videos-git-staging-tech-x.vercel.app"
    context.add_cookies([{
        "name": "_vercel_jwt", "value": VERCEL_SECRET, "domain": domain, 
        "path": "/", "httpOnly": True, "secure": True, "sameSite": "None"
    }])
    context.set_extra_http_headers({
        "x-vercel-protection-bypass": VERCEL_SECRET, 
        "Origin": WEB_URL
    })

def _capturar_paso(page, numero, nombre, flow_data):
    """Captura un paso con numeración para mantener el orden del flujo."""
    prefijo = f"{numero:02d}_{nombre.replace(' ', '_').replace('/', '_')}"
    print(f"   📸 Capturando: {prefijo}")
    
    screenshot_path = RUN_DIR / f"{prefijo}.png"
    page.screenshot(path=str(screenshot_path), full_page=True)
    
    try:
        aria = page.locator("body").aria_snapshot()
    except Exception:
        aria = "Error"
    
    html_file = RUN_DIR / f"{prefijo}.html"
    html_file.write_text(page.content(), encoding="utf-8")
    
    flow_data[prefijo] = {
        "url": page.url,
        "screenshot": str(screenshot_path),
        "html_file": str(html_file),
        "aria_snapshot": aria,
    }

def main():
    if not ADMIN_EMAIL or not ADMIN_PASS:
        raise ValueError("🚨 Faltan credenciales de Admin Marla en el .env")

    flow_data = {}
    print(f"\n🗂️  Ejecución ID: {RUN_ID}")
    print(f"📁 Guardando en: {RUN_DIR}\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(base_url=WEB_URL, ignore_https_errors=True)
        _bypass_vercel(context)
        page = context.new_page()

        try:
            # 1. Login
            print("[-] Logueando como Admin...")
            page.goto("/login", wait_until="networkidle")
            page.locator('input[type="email"]').first.fill(ADMIN_EMAIL)
            page.locator('input[type="password"]').first.fill(ADMIN_PASS)
            page.get_by_role("button", name=re.compile("Iniciar|Entrar|Login|Acceder", re.I)).first.click()
            page.wait_for_url(lambda url: "/login" not in url, timeout=15000)
            page.wait_for_timeout(2000)
            _capturar_paso(page, 1, "Home_Post_Login", flow_data)

            # 2. Crear Curso
            print("[-] Navegando a Crear Nuevo Curso...")
            page.goto("/admin/courses/new", wait_until="networkidle")
            page.wait_for_timeout(2000)
            _capturar_paso(page, 2, "Formulario_Crear_Curso", flow_data)
            
            page.locator('#title').fill("Curso QA Videos")
            page.locator('#description').fill("Curso para mapear el flujo de videos.")
            page.locator('#price').fill("100")
            page.locator('#priceUsd').fill("5")
            page.get_by_role("button", name="Crear y continuar").click()
            page.wait_for_timeout(4000)
            _capturar_paso(page, 3, "Curso_Creado", flow_data)
            print(f"   → URL del curso: {page.url}")

            # 3. Crear Módulo
            print("[-] Creando primer módulo...")
            modulo_titulo = page.get_by_placeholder("Título del módulo *")
            modulo_titulo.wait_for(state="visible", timeout=5000)
            modulo_titulo.fill("Módulo de Prueba QA")
            
            modulo_desc = page.get_by_placeholder("Descripción (opcional)")
            if modulo_desc.is_visible():
                modulo_desc.fill("Módulo creado por el Spider.")
            
            _capturar_paso(page, 4, "Formulario_Modulo_Lleno", flow_data)

            page.get_by_role("button", name="Agregar módulo").click()
            page.wait_for_timeout(4000)
            _capturar_paso(page, 5, "Modulo_Creado", flow_data)

            # 4. Buscar "Agregar video"
            print("[-] Buscando 'Agregar video' en el módulo...")
            btn_agregar_video = page.get_by_role("button", name=re.compile("Agregar video|Añadir video|Subir video", re.I)).first
            if btn_agregar_video.is_visible():
                btn_agregar_video.click()
                page.wait_for_timeout(3000)
                _capturar_paso(page, 6, "Modal_Agregar_Video", flow_data)
            else:
                print("   ⚠️ No se encontró botón 'Agregar video'. Capturando estado actual.")
                _capturar_paso(page, 6, "Estado_Sin_Boton_Video", flow_data)

        except Exception as e:
            print(f"🚨 Error: {e}")
            page.screenshot(path=str(RUN_DIR / "ERROR_flujo.png"))

        finally:
            browser.close()

    # ==========================================================================
    # GENERAR RESUMEN 00_resumen.md
    # ==========================================================================
    md = f"# 🗺️ Spider Run: {RUN_ID}\n\n"
    md += f"- **Fecha:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    md += f"- **URL Base:** {WEB_URL}\n"
    md += f"- **Admin:** {ADMIN_EMAIL}\n"
    md += f"- **Pasos capturados:** {len(flow_data)}\n\n"
    md += "## 📑 Índice de Pasos\n\n"
    md += "| # | Paso | URL |\n"
    md += "|---|------|-----|\n"
    for nombre, data in flow_data.items():
        md += f"| `{nombre}` | {nombre.split('_', 1)[1].replace('_', ' ')} | `{data['url']}` |\n"
    
    md += "\n---\n\n"
    for nombre, data in flow_data.items():
        md += f"## 📍 {nombre}\n\n"
        md += f"- **URL:** `{data['url']}`\n"
        md += f"- **Screenshot:** `{data['screenshot']}`\n"
        md += f"- **HTML:** `{data['html_file']}`\n\n"
        md += "### 🎭 Aria Snapshot\n```yaml\n"
        lines = data["aria_snapshot"].split("\n")
        md += "\n".join(lines[:120])
        if len(lines) > 120:
            md += f"\n... ({len(lines) - 120} líneas más)\n"
        md += "\n```\n\n---\n\n"
    
    md_file = RUN_DIR / "00_resumen.md"
    md_file.write_text(md, encoding="utf-8")
    
    print(f"\n✅ Resumen generado: {md_file}")
    print(f"📁 Ejecución: {RUN_DIR}")
    print(f"📌 Última ejecución registrada en: {BASE_DIR / 'latest_run.txt'}")

if __name__ == "__main__":
    main()