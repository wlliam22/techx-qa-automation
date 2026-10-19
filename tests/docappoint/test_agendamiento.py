import pytest
from playwright.sync_api import Page, expect
from pages.docappoint.catalog_page import CatalogPage


@pytest.mark.functional
@pytest.mark.auto_ready
def test_doca_sch_01_patient_book_no_advance_auto_accept(patient_page: Page, base_url: str):
    """
    DOCA-SCH-01: Validar agendamiento exitoso de cita sin cobro de anticipo
    y verificar persistencia real en la API (POST /nuevoTurnoCheckOut).
    """
    catalog = CatalogPage(patient_page)

    catalog.navegar_al_catalogo(base_url)
    catalog.seleccionar_primer_medico()
    catalog.seleccionar_primer_slot_disponible()

    # Interceptar la llamada de red que persiste la reserva en Backend
    with patient_page.expect_response(
        lambda response: "/nuevoTurnoCheckOut" in response.url and response.request.method == "POST"
    ) as response_info:
        catalog.confirmar_seleccion_turno()

    # 1. Validación de Payload (Payload-First / Shift-Left)
    res = response_info.value
    assert res.status in [200, 201], f"Fallo en API al agendar turno: Status {res.status} - {res.text()}"
    
    data = res.json()
    assert data.get("ok") is True, f"El backend devolvió error en agendamiento: {data}"
    
    # Validar que el turno se cree con un ID válido
    turno_creado = data.get("turno") or data.get("data") or {}
    assert "id" in turno_creado, "La respuesta del backend no retornó el identificador del turno creado"

    # 2. Validación de UI (Confirmación Visual)
    expect(patient_page.locator("text=/Turno creado|Cita agendada|éxito/i")).to_be_visible(timeout=7000)


@pytest.mark.security
@pytest.mark.auto_ready
def test_doca_sch_sec_01_price_tampering_prevention(patient_page: Page, base_url: str):
    """
    DOCA-SCH-SEC-01 (OWASP A04: Insecure Design):
    Verificar que inyectar un precio manipulado (precio: 1.00) en el payload
    de /nuevoTurnoCheckOut sea ignorado o sanitizado por el Backend.
    """
    catalog = CatalogPage(patient_page)

    catalog.navegar_al_catalogo(base_url)
    catalog.seleccionar_primer_medico()
    catalog.seleccionar_primer_slot_disponible()

    # Interceptar y mutar el payload saliente (Price Tampering Attack)
    def mutar_payload_precio(route):
        post_data = route.request.post_data_json or {}
        post_data["precio"] = 1.00
        post_data["costo"] = 1.00
        route.continue_(post_data=post_data)

    patient_page.route("**/nuevoTurnoCheckOut", mutar_payload_precio)

    with patient_page.expect_response(
        lambda response: "/nuevoTurnoCheckOut" in response.url and response.request.method == "POST"
    ) as response_info:
        catalog.confirmar_seleccion_turno()

    res = response_info.value
    data = res.json()
    
    # Limpiar el mock de red para evitar efectos secundarios
    patient_page.unroute("**/nuevoTurnoCheckOut")

    # Aserción Zero Trust: Si la cita se creó, su precio NO debe ser 1.00
    turno = data.get("turno") or data.get("data") or {}
    precio_guardado = turno.get("precio") or turno.get("costo")
    if precio_guardado is not None:
        assert float(precio_guardado) != 1.00, (
            f"VULNERABILIDAD CRÍTICA (OWASP A04): El backend aceptó el precio inyectado ($1.00) "
            f"en lugar de usar la tarifa oficial configurada por el médico."
        )