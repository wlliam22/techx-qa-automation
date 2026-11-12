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
WEB_URL = os.getenv("MARLA_WEB_URL", "https://marla-diaz-videos-git-staging-tech-x.vercel.app")
ADMIN_EMAIL = os.getenv("MARLA_ADMIN_EMAIL", "admin@admin.com")
ADMIN_PASS = os.getenv("MARLA_ADMIN_PASSWORD")
VERCEL_SECRET = os.getenv("VERCEL_MARLA_BYPASS_SECRET")

OUTPUT_DIR = Path("docs/marla_spider")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

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

def _capturar_paso(page, nombre, flow_data):
    print(f"   📸 Capturando: {nombre}")
    safe_name = nombre.replace(" ", "_").replace("/", "_")
    screenshot_path = OUTPUT_DIR / f"screenshot_{safe_name}.png"
    page.screenshot(path=str(screenshot_path), full_page=True)
    
    try:
        aria = page.locator("body").aria_snapshot()
    except Exception:
        aria = "Error"
    
    html_file = OUTPUT_DIR / f"dom_{safe_name}.html"
    html_file.write_text(page.content(), encoding="utf-8")
    
    flow_data[nombre] = {
        "url": page.url,
        "screenshot": str(screenshot_path),
        "html_file": str(html_file),
        "aria_snapshot": aria,
    }

def main():
    if not ADMIN_EMAIL or not ADMIN_PASS:
        raise ValueError("🚨 Faltan credenciales de Admin Marla en el .env")

    flow_data = {}

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
            _capturar_paso(page, "01_Home_Post_Login", flow_data)

            # 2. Navegar directo a /admin/courses (URL exacta del DOM)
            print("[-] Navegando a /admin/courses...")
            page.goto("/admin/courses", wait_until="networkidle")
            page.wait_for_timeout(3000)
            _capturar_paso(page, "02_Lista_Cursos", flow_data)

            # 3. Buscar el primer curso y hacer clic
            print("[-] Entrando al primer curso...")
            try:
                # Buscamos enlaces que contengan /admin/courses/ (con ID)
                primer_curso = page.locator('a[href*="/admin/courses/"]').first
                if not primer_curso.is_visible():
                    # Fallback: buscar botón "Editar" o "Administrar"
                    primer_curso = page.get_by_role("button", name=re.compile("Editar|Administrar|Ver", re.I)).first
                
                primer_curso.wait_for(state="visible", timeout=5000)
                primer_curso.click()
                page.wait_for_timeout(4000)
                _capturar_paso(page, "03_Curso_Seleccionado", flow_data)
                
                # 4. Intentar abrir el modal de "Agregar video"
                print("[-] Buscando botón 'Agregar video' o módulo...")
                page.wait_for_timeout(2000)
                
                # Buscar cualquier botón que diga "Agregar video" o similar
                btn_agregar = page.get_by_role("button", name=re.compile("Agregar video|Añadir video|Subir video|Nuevo video", re.I)).first
                if btn_agregar.is_visible():
                    btn_agregar.click()
                    page.wait_for_timeout(3000)
                    _capturar_paso(page, "04_Modal_Agregar_Video", flow_data)
                else:
                    print("   ⚠️ No se encontró botón 'Agregar video'. Capturando estado del curso.")
                    _capturar_paso(page, "04_Estado_Curso", flow_data)
                
            except Exception as e:
                print(f"   ⚠️ No se pudo entrar al curso: {e}")
                _capturar_paso(page, "03b_Estado_Lista_Cursos", flow_data)

        except Exception as e:
            print(f"🚨 Error: {e}")
            page.screenshot(path=str(OUTPUT_DIR / "error_flujo.png"))
        finally:
            browser.close()

    # Generar Reporte
    md = "# 🗺️ Mapa de Reconocimiento: Marla Díaz (Admin)\n\n"
    for nombre, data in flow_data.items():
        md += f"## 📍 {nombre}\n"
        md += f"- **URL:** `{data['url']}`\n"
        md += f"- **HTML:** `{data['html_file']}`\n"
        md += "### 🎭 Aria Snapshot\n```yaml\n"
        lines = data["aria_snapshot"].split("\n")
        md += "\n".join(lines[:100])
        if len(lines) > 100:
            md += f"\n... ({len(lines) - 100} líneas más)\n"
        md += "\n```\n\n---\n\n"
    
    md_file = OUTPUT_DIR / "marla_admin_mapa.md"
    md_file.write_text(md, encoding="utf-8")
    print(f"✅ Documento generado: {md_file}")

if __name__ == "__main__":
    main()