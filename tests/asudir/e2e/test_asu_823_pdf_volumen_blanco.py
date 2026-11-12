import os
import re
import base64
import pytest
import pdfplumber
from pathlib import Path
from playwright.sync_api import Browser, Page, expect, TimeoutError as PWTimeoutError
from dotenv import load_dotenv

load_dotenv()

# ==============================================================================
# CONFIGURACIÓN DEL ENTORNO Y SECRETS (ASU-823)
# ==============================================================================
WEB_URL        = os.getenv("ASUDIR_WEB_URL", "https://asudir-front-git-staging-tech-x.vercel.app")
ADMIN_EMAIL    = os.getenv("ASU_ADMIN_EMAIL")
ADMIN_PASS     = os.getenv("ASU_ADMIN_PASSWORD")
VERCEL_SECRET  = os.getenv("VERCEL_ASUDIR_BYPASS_SECRET")

POZO_BLANCO      = os.getenv("ASU_POZO_BLANCO", "3818")
N_USUARIOS_3818  = int(os.getenv("ASU_N_USUARIOS_3818", "7"))

# ==============================================================================
# HELPERS
# ==============================================================================
def _bypass_vercel_sso(context):
    if not VERCEL_SECRET: return
    domain = re.sub(r"^https?://", "", WEB_URL).split("/")[0]
    context.add_cookies([{"name": "_vercel_jwt", "value": VERCEL_SECRET, "domain": domain, "path": "/", "httpOnly": True, "secure": True, "sameSite": "None"}])
    context.set_extra_http_headers({"x-vercel-protection-bypass": VERCEL_SECRET, "Origin": WEB_URL})
    def _route_handler(route):
        if route.request.method == "OPTIONS":
            route.fulfill(status=200, headers={"Access-Control-Allow-Origin": WEB_URL, "Access-Control-Allow-Headers": "*"})
        else:
            route.continue_()
    context.route("**/api/**", _route_handler)
    print("🔐 [A01/A07] Bypass Vercel + Interceptor CORS inyectados.")

def _login_admin(page: Page) -> None:
    print("\n[-] 1. Autenticación en Asudir 051 como Admin...")
    page.goto("/login", wait_until="domcontentloaded")
    expect(page.locator('input[name="identifier"]')).to_be_visible(timeout=10000)
    page.locator('input[name="identifier"]').fill(ADMIN_EMAIL)
    page.locator('input[name="password"]').fill(ADMIN_PASS)
    submit_btn = page.get_by_role("button", name="Iniciar Sesión")
    expect(submit_btn).to_be_visible(timeout=5000)
    with page.expect_response(lambda r: "/login" in r.url and r.request.method == "POST", timeout=20000) as resp_info:
        submit_btn.click()
    resp = resp_info.value
    assert resp.ok, f"🚨 Login falló con HTTP {resp.status}."
    page.wait_for_url(lambda url: "/home" in url or "/login" not in url, timeout=15000)
    print(f"✅ Login OK (HTTP {resp.status}).")

def _navegar_a_constancia(page: Page) -> None:
    print("[-] 2. Navegando directamente a /constancia...")
    page.goto("/constancia", wait_until="domcontentloaded")
    search_input = page.locator('input[role="combobox"][placeholder*="Buscar por número"]').first
    expect(search_input).to_be_attached(timeout=15000)
    expect(search_input).to_be_visible(timeout=15000)
    print("✅ Vista de Constancia de Usuario cargada.")

def _seleccionar_pozo(page: Page, pozo_id: str) -> None:
    print(f"[-] 3. Seleccionando pozo {pozo_id}...")
    search_input = page.locator('input[role="combobox"][placeholder*="Buscar por número"]').first
    search_input.click()
    search_input.fill(pozo_id)
    page.wait_for_timeout(2500)
    opcion_pozo = page.locator(f'[role="option"]:has-text("{pozo_id}")').first
    expect(opcion_pozo).to_be_visible(timeout=10000)
    opcion_pozo.click()
    page.wait_for_timeout(2000)
    btn_imprimir = page.get_by_role("button", name="Imprimir")
    expect(btn_imprimir).to_be_enabled(timeout=10000)
    print(f"✅ Pozo {pozo_id} seleccionado.")

def _completar_ciclo_y_firmas(page: Page) -> None:
    print("[-] 4. Verificando pre-configuración de ciclo y firmas...")
    btn_imprimir = page.get_by_role("button", name="Imprimir")
    if btn_imprimir.is_enabled():
        print("✅ Formulario ya pre-configurado (ciclo y firmas por defecto).")
        return
    print("⚠️  Configurando manualmente...")
    try:
        ciclo = page.locator('div[role="combobox"]').filter(has_text=re.compile(r"20\d{2}-20\d{2}")).first
        if ciclo.is_visible(): ciclo.click(); page.locator('[role="listbox"] [role="option"]').first.click(); page.wait_for_timeout(500)
    except Exception: pass
    try:
        firmas = page.locator('div[role="combobox"]').filter(has_text=re.compile(r"\d+ Firmas?")).first
        if firmas.is_visible(): firmas.click(); page.locator('[role="listbox"] [role="option"]').first.click(); page.wait_for_timeout(500)
    except Exception: pass
    expect(btn_imprimir).to_be_enabled(timeout=10000)

def _imprimir_y_capturar_pdf(context, page: Page, out_path: Path) -> Path:
    print("[-] 5. Presionando 'Imprimir' y capturando el PDF desde la nueva pestaña (blob)...")
    btn = page.get_by_role("button", name="Imprimir")
    expect(btn).to_be_enabled(timeout=10000)
    try:
        with context.expect_page(timeout=15000) as popup_info:
            btn.click()
    except PWTimeoutError:
        raise AssertionError("🚨 El botón Imprimir no abrió una nueva pestaña.")
    popup_page = popup_info.value
    popup_page.wait_for_load_state("networkidle", timeout=15000)
    url = popup_page.url
    if url.startswith("blob:"):
        b64 = popup_page.evaluate("""async () => {
            const r = await fetch(location.href);
            const b = await r.arrayBuffer();
            return btoa(String.fromCharCode(...new Uint8Array(b)));
        }""")
        out_path.write_bytes(base64.b64decode(b64))
        print(f"✅ PDF capturado vía popup blob → {out_path}")
        return out_path
    raise AssertionError(f"🚨 La nueva pestaña no es un blob PDF: {url}")

def _validar_pdf_volumen_blanco(pdf_path: Path) -> dict:
    print(f"[-] 6. Parseando PDF con pdfplumber ({pdf_path})...")
    assert pdf_path.exists() and pdf_path.stat().st_size > 0, "🚨 PDF vacío."

    texto_completo = ""
    with pdfplumber.open(pdf_path) as pdf:
        for p in pdf.pages:
            # Extraemos el texto plano manteniendo el layout (x_tolerance ajustado)
            t = p.extract_text(x_tolerance=2, y_tolerance=2)
            if t: texto_completo += t + "\n"

    # Imprimimos un preview del texto para debug en consola si falla
    print("--- Preview del texto del PDF ---")
    print("\n".join(texto_completo.splitlines()[:15]))
    print("--------------------------------")

    # Expresión regular para capturar filas: 
    # Ej: "1 AURORA T CISCOMANI DAVILA 100.0000 HAS 30.0000 HAS"
    # Grupo 1: Num, Grupo 2: Nombre, Grupo 3: Volumen (opcional), Grupo 4: Sup Fisica, Grupo 5: Sup Riego
    patron_fila = re.compile(
        r"^\s*(\d+)\s+"                          # Número
        r"([A-ZÁÉÍÓÚÑa-záéíóúñ\s\.]+?)\s+"        # Nombre (letras y espacios)
        r"(?:(\d+\.\d{2}\s+MM3)\s+)?"             # VOLUMEN (Opcional)
        r"(\d+\.\d{4}\s+HAS)\s+"                  # SUP. FÍSICA
        r"(\d+\.\d{4}\s+HAS)",                    # SUP. RIEGO
        re.MULTILINE
    )

    stats = {"total": 0, "en_blanco": 0, "con_mm3": 0}
    
    for match in patron_fila.finditer(texto_completo):
        num, nombre, volumen, fisica, riego = match.groups()
        nombre = nombre.strip()
        
        # Ignoramos posibles falsos positivos
        if "USUARIO" in nombre.upper(): continue
        
        stats["total"] += 1
        
        if volumen:
            stats["con_mm3"] += 1
            # AC 4: Validación del formato del volumen
            assert re.match(r"^\d+\.\d{2}\s+MM3$", volumen), f"🚨 Error de formato en Volumen: {volumen}"
        else:
            stats["en_blanco"] += 1

        # AC 5: Superficies siempre presentes
        assert fisica != "", f"🚨 Falla Sup. Física en fila {num}"
        assert riego != "", f"🚨 Falla Sup. Riego en fila {num}"

    # Validaciones finales
    assert stats["total"] > 0, "🚨 No se detectó ninguna fila de usuario en el PDF."
    
    # Validamos el caso del pozo 3818 (todos sin volumen)
    if int(POZO_BLANCO) == 3818:
        assert stats["en_blanco"] == N_USUARIOS_3818, f"🚨 Se esperaban {N_USUARIOS_3818} en blanco, pero hay {stats['en_blanco']}."

    return stats

# ==============================================================================
# TEST PRINCIPAL
# ==============================================================================
@pytest.mark.e2e
def test_asu_823_pdf_volumen_blanco(browser: Browser, tmp_path: Path):
    assert WEB_URL and ADMIN_EMAIL and ADMIN_PASS, "🚨 Faltan credenciales ASUDIR en el .env."

    context = browser.new_context(base_url=WEB_URL, accept_downloads=True, ignore_https_errors=True)
    _bypass_vercel_sso(context)
    page = context.new_page()

    try:
        _login_admin(page)
        _navegar_a_constancia(page)
        _seleccionar_pozo(page, POZO_BLANCO)
        _completar_ciclo_y_firmas(page)

        pdf_path = tmp_path / f"constancia_{POZO_BLANCO}.pdf"
        _imprimir_y_capturar_pdf(context, page, pdf_path)

        stats = _validar_pdf_volumen_blanco(pdf_path)

        print(f"\n✅ [APROBADO] ASU-823 — {stats['en_blanco']} celdas VOLUMEN en blanco, {stats['con_mm3']} con 'MM3'.")

    except AssertionError:
        forensic = Path("artifacts") / "asu_823"
        forensic.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(forensic / "fallo_pantalla.png"))
        for p in tmp_path.glob("*.pdf"):
            (forensic / p.name).write_bytes(p.read_bytes())
            print(f"📎 PDF y screenshot preservados en: {forensic}")
        raise
    finally:
        context.close()