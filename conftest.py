import os
from typing import Generator
from dotenv import load_dotenv
import pytest
from playwright.sync_api import Browser, BrowserContext, Page, Route

from utils.credentials import CredentialManager, UserRole
from pages.docappoint.login_page import LoginPage

load_dotenv()


@pytest.fixture(scope="function")
def base_url(request) -> str:
    """Resuelve la URL base según el proyecto auditado."""
    cli_url = request.config.getoption("base_url", default=None)
    if cli_url:
        return cli_url.rstrip("/")

    node_path = str(getattr(request.node, "path", request.node.fspath)).lower()

    if "asudir" in node_path:
        env_url = os.getenv("ASUDIR_WEB_URL") or os.getenv("BASE_URL")
        return (env_url or "https://asudir-front-git-staging-tech-x.vercel.app").rstrip("/")

    env_url = os.getenv("DOCAPPOINT_WEB_URL") or os.getenv("BASE_URL")
    return (env_url or "https://docappoint-git-staging-tech-x.vercel.app").rstrip("/")


@pytest.fixture(scope="function")
def vercel_bypass_secret(request, base_url: str) -> str | None:
    """Obtiene el token de bypass según el proyecto."""
    node_path = str(getattr(request.node, "path", request.node.fspath)).lower()
    target_url = base_url.lower()

    if "docappoint" in node_path or "docappoint" in target_url:
        return os.getenv("VERCEL_DOCAPPOINT_BYPASS_SECRET")
    elif "asudir" in node_path or "asudir" in target_url:
        return os.getenv("VERCEL_ASUDIR_BYPASS_SECRET")
    return None


def _get_authenticated_context(
    browser: Browser,
    role: UserRole,
    base_url: str,
    bypass_secret: str | None = None
) -> BrowserContext:
    """
    Genera el contexto autenticado sin contaminar las peticiones a la API con cabeceras de Vercel.
    """
    cred = CredentialManager.get_credentials(role)

    # 1. Resolver el archivo de estado de sesión (Shift-Left)
    state_path = None
    possible_paths = [
        cred.auth_state_path,
        f"auth_{role.value}.json",
        "auth.json"
    ]
    for path in possible_paths:
        if path and os.path.exists(path):
            state_path = path
            break

    context_args = {"base_url": base_url}
    if state_path:
        context_args["storage_state"] = state_path

    # Creación limpia del contexto SIN extra_http_headers globales
    context = browser.new_context(**context_args)

    # 2. Inyección Quirúrgica de Vercel Bypass mediante Route Interceptor
    if bypass_secret:
        def vercel_route_handler(route: Route):
            headers = route.request.headers.copy()
            headers["x-vercel-protection-bypass"] = bypass_secret
            headers["x-vercel-set-bypass-cookie"] = "true"
            route.continue_(headers=headers)

        # SOLO intercepta llamadas a Vercel. Jamás toca test-docappoint.techxmx.com
        context.route("**/*vercel.app/**", vercel_route_handler)

    # 3. Si no hay sesión previa guardada, realiza login por UI
    if not state_path:
        page = context.new_page()
        login_page = LoginPage(page)
        login_page.login_with_role(role, base_url, save_state=True)
        page.close()

    return context


@pytest.fixture(scope="function")
def patient_page(browser: Browser, base_url: str, vercel_bypass_secret: str | None) -> Generator[Page, None, None]:
    """Página con sesión activa de Paciente y aislamiento de red."""
    context = _get_authenticated_context(browser, UserRole.PATIENT, base_url, bypass_secret=vercel_bypass_secret)
    page = context.new_page()
    yield page
    page.close()
    context.close()


@pytest.fixture(scope="function")
def doctor_page(browser: Browser, base_url: str, vercel_bypass_secret: str | None) -> Generator[Page, None, None]:
    """Página con sesión activa de Doctor y aislamiento de red."""
    context = _get_authenticated_context(browser, UserRole.DOCTOR, base_url, bypass_secret=vercel_bypass_secret)
    page = context.new_page()
    yield page
    page.close()
    context.close()