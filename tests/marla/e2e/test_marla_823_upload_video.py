import os
import re
import subprocess
import pytest
from pathlib import Path
from playwright.sync_api import Browser, Page, expect, TimeoutError as PWTimeoutError
from dotenv import load_dotenv

load_dotenv()

# ==============================================================================
# CONFIGURACIÓN
# ==============================================================================
WEB_URL = os.getenv("MARLA_WEB_URL", "https://marla-diaz-videos-git-staging-tech-x.vercel.app")
ADMIN_EMAIL = os.getenv("MARLA_ADMIN_EMAIL", "admin@admin.com")
ADMIN_PASS = os.getenv("MARLA_ADMIN_PASSWORD")
VERCEL_SECRET = os.getenv("VERCEL_MARLA_BYPASS_SECRET")

ASSETS_DIR = Path(__file__).parent / "assets"

# ==============================================================================
# HELPERS
# ==============================================================================
def _bypass_vercel_and_cors(context):
    """Inyecta bypass de Vercel y salta el CORS en Staging."""
    if VERCEL_SECRET:
        domain = "marla-diaz-videos-git-staging-tech-x.vercel.app"
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
            route.fulfill(status=200, headers={
                "Access-Control-Allow-Origin": WEB_URL,
                "Access-Control-Allow-Headers": "*",
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH"
            })
        else:
            route.continue_()
    
    # Interceptar todas las peticiones a API
    context.route("**/api/**", _route_handler)
    context.route("**/auth/**", _route_handler)
    # También interceptar el backend de Strapi de Marla (por si usa otro path)
    context.route("**/*.tech-x.vercel.app/**", _route_handler)
    print("🔐 [A01/A07] Bypass Vercel + Interceptor CORS inyectados.")


def _crear_archivo_sparse(path: Path, size_bytes: int) -> Path:
    """
    Crea un archivo sparse del tamaño especificado (no ocupa espacio real en disco).
    Usa fsutil en Windows (rápido). Si falla, usa truncate via Python.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    
    if os.name == 'nt':
        try:
            # fsutil file createnew <path> <size> - instantáneo, no escribe bytes
            result = subprocess.run(
                ['fsutil', 'file', 'createnew', str(path), str(size_bytes)],
                check=True, capture_output=True, timeout=10
            )
            print(f"   ✅ fsutil OK: {path.name}")
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
            print(f"   ⚠️ fsutil falló. Usando truncate...")
            # Fallback: crear archivo vacío y expandirlo con seek+write (sparse)
            with open(path, 'wb') as f:
                f.seek(size_bytes - 1)
                f.write(b'\x00')
    else:
        # Linux/Mac: sparse file instantáneo
        with open(path, 'wb') as f:
            f.seek(size_bytes - 1)
            f.write(b'\x00')
    
    actual_size = path.stat().st_size
    print(f"   📦 Archivo creado: {path.name} ({actual_size / (1024**3):.2f} GB)")
    return path


def _login_admin(page: Page):
    """
    Login con reintento. Usa domcontentloaded en vez de networkidle para 
    evitar timeouts en SPA.
    """
    print("\n[-] 1. Logueando como Admin...")
    
    # CAMBIO CLAVE: domcontentloaded es más rápido y confiable que networkidle
    for intento in range(2):
        try:
            page.goto("/login", wait_until="domcontentloaded", timeout=20000)
            page.locator('input[type="email"]').first.wait_for(state="visible", timeout=10000)
            page.locator('input[type="email"]').first.fill(ADMIN_EMAIL)
            page.locator('input[type="password"]').first.fill(ADMIN_PASS)
            page.get_by_role("button", name=re.compile("Iniciar|Entrar|Login", re.I)).first.click()
            page.wait_for_url(lambda url: "/login" not in url, timeout=15000)
            print(f"✅ Login OK (intento {intento + 1})")
            return
        except PWTimeoutError:
            if intento == 0:
                print(f"   ⚠️ Intento {intento + 1} falló. Reintentando...")
            else:
                raise


def _ir_a_formulario_agregar_video(page: Page):
    print("[-] 2. Navegando a Crear Curso...")
    page.goto("/admin/courses/new", wait_until="domcontentloaded", timeout=20000)
    page.wait_for_timeout(3000)
    page.locator('#title').fill("Curso QA Automatización")
    page.locator('#description').fill("Curso para test E2E.")
    page.locator('#price').fill("100")
    page.locator('#priceUsd').fill("5")
    page.get_by_role("button", name="Crear y continuar").click()
    page.wait_for_timeout(4000)
    print(f"   → Curso creado en: {page.url}")

    print("[-] 3. Creando módulo...")
    page.get_by_placeholder("Título del módulo *").fill("Módulo QA")
    page.get_by_role("button", name="Agregar módulo").click()
    page.wait_for_timeout(4000)


# ==============================================================================
# TESTS
# ==============================================================================
@pytest.mark.e2e
def test_marla_823_ac1_aviso_limite_3gb(browser: Browser):
    """AC 1: El aviso debajo del campo de video dice 'Máximo 3 GB'."""
    context = browser.new_context(base_url=WEB_URL, ignore_https_errors=True)
    _bypass_vercel_and_cors(context)
    page = context.new_page()

    try:
        _login_admin(page)
        _ir_a_formulario_agregar_video(page)

        aviso_limite = page.get_by_text("Formato aceptado de video: Solo MP4 · Máximo 3 GB")
        expect(aviso_limite).to_be_visible(timeout=5000)
        print("✅ [APROBADO] AC 1: El aviso 'Máximo 3 GB' está presente.")
    finally:
        context.close()


@pytest.mark.e2e
def test_marla_823_ac12_miniatura_mayor_10mb_rechazada(browser: Browser):
    """AC 12: Una miniatura de más de 10 MB se rechaza al elegirla."""
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    imagen_fake = ASSETS_DIR / "imagen_12mb.jpg"
    imagen_fake.write_bytes(b"x" * (12 * 1024 * 1024))

    context = browser.new_context(base_url=WEB_URL, ignore_https_errors=True)
    _bypass_vercel_and_cors(context)
    page = context.new_page()

    try:
        _login_admin(page)
        _ir_a_formulario_agregar_video(page)

        miniatura_input = page.locator('input[type="file"]').nth(3)
        miniatura_input.set_input_files(str(imagen_fake))
        page.wait_for_timeout(1500)

        error_msg = page.locator('text="La imagen supera el límite de 10 MB"')
        expect(error_msg.first).to_be_visible(timeout=5000)
        print("✅ [APROBADO] AC 12: La miniatura de 12 MB fue rechazada correctamente.")
    finally:
        context.close()


@pytest.mark.e2e
def test_marla_823_ac3_video_mayor_3gb_rechazado(browser: Browser):
    """
    AC 3: Un video de más de 3 GB se rechaza al elegirlo.
    Usa archivo sparse que el navegador ve como 3.1 GB pero no se sube.
    """
    LIMITE_3GB = 3_221_225_472
    video_3_1gb = _crear_archivo_sparse(
        ASSETS_DIR / "video_3.1gb.mp4",
        LIMITE_3GB + 1024
    )
    
    context = browser.new_context(base_url=WEB_URL, ignore_https_errors=True)
    _bypass_vercel_and_cors(context)
    page = context.new_page()

    try:
        _login_admin(page)
        _ir_a_formulario_agregar_video(page)

        print("[-] 4. Localizando el input de video...")
        video_input = page.locator('input[type="file"][accept*="video"]').first
        print(f"   → Inputs de video encontrados: {page.locator('input[type=\"file\"][accept*=\"video\"]').count()}")
        
        print(f"[-] 5. Subiendo video de 3.1 GB (simulado, sin enviar)...")
        try:
            video_input.set_input_files(str(video_3_1gb))
        except Exception as e:
            print(f"   ⚠️ Playwright lanzó error (esperado si el input rechaza): {e}")
        
        page.wait_for_timeout(1500)

        print("[-] 6. Verificando mensaje de error...")
        error_msg = page.locator('text="El video supera el límite de 3 GB"')
        expect(error_msg.first).to_be_visible(timeout=5000)
        print("✅ [APROBADO] AC 3: El video de 3.1 GB fue rechazado correctamente.")

    finally:
        context.close()
        try:
            video_3_1gb.unlink()
        except Exception:
            pass