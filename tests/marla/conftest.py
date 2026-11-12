import os
import io
import re
import pytest
import requests
from pathlib import Path
from playwright.sync_api import Browser, Page, TimeoutError as PWTimeoutError
from dotenv import load_dotenv

load_dotenv()

WEB_URL = os.getenv("MARLA_WEB_URL", "https://marla-diaz-videos-git-staging-tech-x.vercel.app")
API_URL = os.getenv("MARLA_API_URL", "https://staging-marla-videos.techxmx.com")
ADMIN_EMAIL = os.getenv("MARLA_ADMIN_EMAIL", "william@mailtechxmx.com")
ADMIN_PASS = os.getenv("MARLA_ADMIN_PASSWORD", "Wm20745046.")
VERCEL_SECRET = os.getenv("VERCEL_MARLA_BYPASS_SECRET")
ORIGIN = WEB_URL

ASSETS_DIR = Path(__file__).parent / "assets"
LIMITE_3GB = 3_221_225_472


# ==============================================================================
# HELPERS COMPARTIDOS
# ==============================================================================
def apply_bypass_and_cors(context):
    """Inyecta bypass Vercel + interceptor CORS."""
    if VERCEL_SECRET:
        domain = re.sub(r"^https?://", "", WEB_URL).split("/")[0]
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
    context.route("**/api/**", _route_handler)
    context.route("**/auth/**", _route_handler)


def login_admin(page: Page):
    """Login con reintento."""
    for intento in range(2):
        try:
            page.goto("/login", wait_until="domcontentloaded", timeout=20000)
            page.locator('input[type="email"]').first.wait_for(state="visible", timeout=10000)
            page.locator('input[type="email"]').first.fill(ADMIN_EMAIL)
            page.locator('input[type="password"]').first.fill(ADMIN_PASS)
            page.get_by_role("button", name=re.compile("Iniciar|Entrar|Login", re.I)).first.click()
            page.wait_for_url(lambda url: "/login" not in url, timeout=15000)
            return
        except PWTimeoutError:
            if intento == 1:
                raise


def crear_curso_y_modulo(page: Page, curso_nombre: str = "Curso QA Suite"):
    """Crea curso + módulo y devuelve la URL del curso."""
    page.goto("/admin/courses/new", wait_until="domcontentloaded", timeout=20000)
    page.wait_for_timeout(2000)
    page.locator('#title').fill(curso_nombre)
    page.locator('#description').fill("Curso para suite QA.")
    page.locator('#price').fill("100")
    page.locator('#priceUsd').fill("5")
    page.get_by_role("button", name="Crear y continuar").click()
    page.wait_for_timeout(4000)
    
    page.get_by_placeholder("Título del módulo *").fill("Módulo QA")
    page.get_by_role("button", name="Agregar módulo").click()
    page.wait_for_timeout(3000)
    
    return page.url


def make_sparse_bytes(size: int) -> io.BytesIO:
    """BytesIO sparse para simular archivos grandes sin cargar RAM."""
    buf = io.BytesIO()
    buf.seek(size - 1)
    buf.write(b'\x00')
    buf.seek(0)
    return buf


def headers_api(token=None, is_multipart=False):
    h = {"Origin": ORIGIN, "Referer": f"{ORIGIN}/", "Accept": "application/json"}
    if not is_multipart:
        h["Content-Type"] = "application/json"
    if VERCEL_SECRET:
        h["x-vercel-protection-bypass"] = VERCEL_SECRET
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


# ==============================================================================
# FIXTURES PYTEST
# ==============================================================================
@pytest.fixture(scope="session")
def marla_context(browser: Browser):
    """Contexto de Playwright con bypass + CORS."""
    ctx = browser.new_context(base_url=WEB_URL, ignore_https_errors=True)
    apply_bypass_and_cors(ctx)
    yield ctx
    ctx.close()


@pytest.fixture(scope="function")
def admin_page(marla_context):
    """Página con login de Admin ya hecho."""
    page = marla_context.new_page()
    login_admin(page)
    yield page
    page.close()


@pytest.fixture(scope="session")
def admin_token():
    """Token JWT del admin para tests de API."""
    r = requests.post(
        f"{API_URL}/api/auth/signin",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASS},
        headers=headers_api(),
        timeout=15,
    )
    assert r.status_code == 200, f"Login API falló: {r.text[:300]}"
    token = r.json().get("token") or r.json().get("jwt") or r.json().get("accessToken")
    assert token
    return token


@pytest.fixture(scope="session")
def curso_modulo_api(admin_token):
    """Crea curso + módulo por API y devuelve IDs."""
    r = requests.post(f"{API_URL}/api/courses",
        json={"title": "Curso QA API", "description": "Test", "price": 100, "priceUsd": 5},
        headers=headers_api(admin_token), timeout=15)
    assert r.status_code in [200, 201]
    curso_id = (r.json().get("data") or r.json()).get("id")
    
    r = requests.post(f"{API_URL}/api/chapters",
        json={"courseId": curso_id, "title": "Módulo QA"},
        headers=headers_api(admin_token), timeout=15)
    assert r.status_code in [200, 201]
    chapter_id = (r.json().get("data") or r.json()).get("id")
    
    return {"curso_id": curso_id, "chapter_id": chapter_id}


@pytest.fixture(scope="function")
def assets_dir():
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    return ASSETS_DIR