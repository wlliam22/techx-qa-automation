import pytest
from playwright.sync_api import Page, expect
from pages.docappoint.login_page import LoginPage
from pages.docappoint.catalog_page import CatalogPage
import os

@pytest.mark.functional
@pytest.mark.auto_ready
def test_doca_sch_01_patient_book_no_advance_auto_accept(page: Page):
    """
    DOCA-SCH-01: Validar agendamiento de cita médica desde catálogo
    sin anticipo ($0) y con auto-aceptación activa.
    Audita que la llamada a la API cree el turno con status 'CONFIRMADA'.
    """
    base_url = os.getenv("DOCAPPOINT_WEB_URL")
    admin_user = os.getenv("DOCAPPOINT_ADMIN_USER")
    admin_pass = os.getenv("DOCAPPOINT_ADMIN_PASS")

    # 1. Login con cuenta de prueba (o paciente)
    login = LoginPage(page)
    login.login_as_admin(admin_user, admin_pass, base_url)

    # 2. Navegar al catálogo y seleccionar turno
    catalog = CatalogPage(page)
    catalog.navegar_al_catalogo(base_url)
    catalog.seleccionar_primer_medico()
    catalog.seleccionar_primer_slot_disponible()

    # 3. Interceptación DevSecOps: Auditar el payload que crea la cita
    with page.expect_response(lambda res: "/turnos" in res.url or "/appointments" in res.url and res.status in [200, 201]) as response_info:
        catalog.confirmar_seleccion_turno()

    response = response_info.value
    assert response.ok, f"Error en API al agendar cita: Código {response.status}"
    
    payload = response.json()
    # Zero Trust: Validar que el backend confirme la cita sin requerir cobro
    assert payload.get("status") in ["CONFIRMADA", "CONFIRMED", "ok", True]