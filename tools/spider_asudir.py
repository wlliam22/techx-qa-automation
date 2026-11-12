import os
import json
import time
from pathlib import Path
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

load_dotenv()

# ==============================================================================
# CONFIGURACIÓN
# ==============================================================================
WEB_URL       = os.getenv("ASUDIR_WEB_URL", "https://asudir-front-git-staging-tech-x.vercel.app")
ADMIN_EMAIL   = os.getenv("ASU_ADMIN_EMAIL")
ADMIN_PASS    = os.getenv("ASU_ADMIN_PASSWORD")
VERCEL_SECRET = os.getenv("VERCEL_ASUDIR_BYPASS_SECRET")

OUTPUT_DIR = Path("docs/asudir_spider")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Rutas a explorar (puedes ir agregando más)
RUTAS_A_EXPLORAR = [
    "/login",
    "/constancia",
    # "/pozos",
    # "/usuarios",
]

def _bypass_vercel_sso(context):
    if not VERCEL_SECRET:
        return
    import re
    domain = re.sub(r"^https?://", "", WEB_URL).split("/")[0]
    context.add_cookies([{
        "name": "_vercel_jwt", "value": VERCEL_SECRET, "domain": domain,
        "path": "/", "httpOnly": True, "secure": True, "sameSite": "None",
    }])
    context.set_extra_http_headers({"x-vercel-protection-bypass": VERCEL_SECRET})

def main():
    if not ADMIN_EMAIL or not ADMIN_PASS:
        raise ValueError("🚨 Faltan credenciales en el .env")

    mapa_datos = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False) # headless=False para ver qué pasa
        context = browser.new_context(base_url=WEB_URL, ignore_https_errors=True)
        _bypass_vercel_sso(context)

        # --- FASE 1: LOGIN ---
        print("[-] Iniciando sesión para habilitar rutas protegidas...")
        page = context.new_page()
        page.goto("/login", wait_until="networkidle")
        
        page.locator('input[name="identifier"]').fill(ADMIN_EMAIL)
        page.locator('input[name="password"]').fill(ADMIN_PASS)
        
        # Interceptamos el OPTIONS para saltar el CORS molesto
        context.route("**/api/**", lambda route: route.fulfill(status=200, headers={"Access-Control-Allow-Origin": WEB_URL, "Access-Control-Allow-Headers": "*"}) if route.request.method == "OPTIONS" else route.continue_())

        page.get_by_role("button", name="Iniciar Sesión").click()
        page.wait_for_url(lambda url: "/login" not in url, timeout=15000)
        print("✅ Login exitoso.")

        # --- FASE 2: EXPLORACIÓN ---
        for ruta in RUTAS_A_EXPLORAR:
            print(f"\n[-] Explorando ruta: {ruta}")
            
            consola_msgs = []
            page.on("console", lambda msg: consola_msgs.append({"type": msg.type, "text": msg.text}))
            
            start_time = time.time()
            try:
                page.goto(ruta, wait_until="networkidle", timeout=20000)
                page.wait_for_timeout(3000) # Dar tiempo a que React pinte el DOM completo
            except Exception as e:
                print(f"⚠️ Error navegando a {ruta}: {e}")

            # Capturar datos
            html_content = page.content()
            screenshot_path = OUTPUT_DIR / f"screenshot_{ruta.strip('/').replace('/', '_') or 'home'}.png"
            page.screenshot(path=str(screenshot_path), full_page=True)

            # Intentar extraer estructura de accesibilidad (muy útil para Playwright)
            aria_snapshot = page.locator("body").aria_snapshot()

            mapa_datos[ruta] = {
                "url_final": page.url,
                "tiempo_carga_ms": int((time.time() - start_time) * 1000),
                "screenshot": str(screenshot_path),
                "consola_errores": [m for m in consola_msgs if m["type"] == "error"],
                "aria_snapshot": aria_snapshot,
                "html_length": len(html_content),
                # Guardamos el HTML en un archivo separado para no hacer el JSON gigante
                "html_file": f"dom_{ruta.strip('/').replace('/', '_') or 'home'}.html"
            }

            # Guardar HTML crudo
            (OUTPUT_DIR / mapa_datos[ruta]["html_file"]).write_text(html_content, encoding="utf-8")
            print(f"✅ Ruta {ruta} mapeada. Errores en consola: {len(mapa_datos[ruta]['consola_errores'])}")

        browser.close()

    # --- FASE 3: GENERAR REPORTE MARKDOWN ---
    print("\n[-] Generando documento único de mapeo...")
    md_content = "# 🗺️ Mapa de Reconocimiento Web - Asudir 051\n\n"
    md_content += f"Generado el: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    md_content += "Este documento ha sido autogenerado por el Spider de Playwright para eliminar asunciones en los scripts.\n\n"

    for ruta, data in mapa_datos.items():
        md_content += f"## 📍 Ruta: `{ruta}`\n"
        md_content += f"- **URL Final:** {data['url_final']}\n"
        md_content += f"- **Tiempo de carga:** {data['tiempo_carga_ms']} ms\n"
        md_content += f"- **Screenshot:** `{data['screenshot']}`\n"
        
        md_content += "\n### 🚨 Errores de Consola\n"
        if data["consola_errores"]:
            for err in data["consola_errores"]:
                md_content += f"- `{err['type']}`: {err['text']}\n"
        else:
            md_content += "- *Sin errores detectados.*\n"

        md_content += "\n### 🎭 Aria Snapshot (Selectores Recomendados)\n"
        md_content += "```yaml\n"
        # Truncamos el snapshot si es muy largo para el Markdown
        lines = data["aria_snapshot"].split("\n")
        md_content += "\n".join(lines[:50]) # Primeras 50 líneas
        if len(lines) > 50:
            md_content += f"\n... ({len(lines) - 50} líneas más. Ver archivo HTML completo)\n"
        md_content += "```\n\n"

        md_content += f"### 🌐 DOM Crudo\n"
        md_content += f"El DOM completo de esta vista está en: `{data['html_file']}`\n"
        md_content += "---\n\n"

    (OUTPUT_DIR / "asudir_mapa.md").write_text(md_content, encoding="utf-8")
    (OUTPUT_DIR / "asudir_mapa.json").write_text(json.dumps(mapa_datos, indent=2), encoding="utf-8")
    
    print(f"✅ Documento maestro generado en: {OUTPUT_DIR / 'asudir_mapa.md'}")
    print(f"✅ Datos JSON generados en: {OUTPUT_DIR / 'asudir_mapa.json'}")

if __name__ == "__main__":
    main()