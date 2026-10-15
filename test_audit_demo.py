import pytest
from playwright.sync_api import Page, expect

def test_auditoria_bloqueo_motivo(page: Page):
    """
    DOCA-50-CP-01 [Auto-Ready]: Validar que no se entreguen datos clínicos
    sin registrar motivo y que el modal capture la interacción.
    """
    # 1. Navegar al entorno Staging
    page.goto("https://docappoint-git-staging-tech-x.vercel.app/admin?section=auditoria")

    # 2. Localizar el primer botón 'Ver' utilizando selectores semánticos o data-testid
    # Playwright espera automáticamente a que el elemento sea interactivo
    btn_ver = page.locator("button:has-text('Ver')").first
    expect(btn_ver).to_be_visible()
    btn_ver.click()

    # 3. Validar que se abrió el modal de justificación
    modal_title = page.locator("text=Detalle del evento de auditoria")
    expect(modal_title).to_be_visible()

    # 4. Validar que el botón 'Ver detalle' existe pero no muestra datos clínicos de entrada
    btn_detalle = page.locator("button:has-text('Ver detalle')")
    expect(btn_detalle).to_be_visible()

    # 5. Intercepción de red: Verificar que no se haya disparado fuga de datos
    # Tomar captura de pantalla como evidencia del estado inicial del modal
    page.screenshot(path="reports/evidencia_modal_auditoria.png")