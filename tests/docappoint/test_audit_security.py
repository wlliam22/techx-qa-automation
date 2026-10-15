import pytest
from playwright.sync_api import Page, expect
from pages.base_page import BasePage
from pages.docappoint.login_page import LoginPage
import os

@pytest.mark.security
@pytest.mark.auto_ready
def test_doca_50_sec_01_audit_data_minimization(page: Page):
    """
    DOCA-50-SEC-01: Validar acceso seguro a auditoría e integridad
    del listado de eventos clínicos tras autenticación formal.
    """
    base_url = os.getenv("DOCAPPOINT_WEB_URL")
    admin_user = os.getenv("DOCAPPOINT_ADMIN_USER")
    admin_pass = os.getenv("DOCAPPOINT_ADMIN_PASS")

    # 1. Autenticar en Docappoint para inyectar token en localStorage
    login_page = LoginPage(page)
    login_page.login_as_admin(admin_user, admin_pass, base_url)

    # 2. Navegar a la sección de auditoría con sesión activa
    base_page = BasePage(page)
    base_page.navigate(f"{base_url}/admin?section=auditoria")

    # 3. Validar que la tabla cargue sin errores de React
    tabla = page.locator("table, .MuiTable-root").first
    expect(tabla).to_be_visible(timeout=10000)

    # 4. Validar presencia del botón 'Ver' en el primer registro
    btn_ver = page.locator("button:has-text('Ver')").first
    expect(btn_ver).to_be_visible()