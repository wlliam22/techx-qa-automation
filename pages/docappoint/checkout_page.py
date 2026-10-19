import os
from playwright.sync_api import Page, Locator, expect
from pages.base_page import BasePage


class CheckoutPage(BasePage):
    """Page Object para el flujo de Checkout y Confirmación de Citas en Docappoint."""

    def __init__(self, page: Page):
        super().__init__(page)
        # Selectores principales del checkout / agendamiento
        self.btn_confirmar = (
            page.get_by_role("button", name="Confirmar Cita", exact=False)
            .or_(page.get_by_role("button", name="Agendar", exact=False))
            .or_(page.locator("button[data-testid='btn-confirmar-cita']"))
            .or_(page.locator("button:has-text('Confirmar')"))
        )
        self.btn_pagar = (
            page.get_by_role("button", name="Pagar", exact=False)
            .or_(page.locator("button[data-testid='btn-pagar']"))
        )
        self.input_monto = (
            page.locator("input[name='monto'], input[name='price'], input[data-testid='input-monto']")
        )
        self.modal_exito = (
            page.locator(".modal-success, [data-testid='booking-success-modal']")
            .or_(page.get_by_text("Cita agendada con éxito", exact=False))
        )
        self.alerta_error = (
            page.locator(".toast-error, .alert-danger, [data-testid='toast-error']")
        )

    def confirmar_reserva(self) -> None:
        """Confirma la reserva esperando la respuesta de red de Express."""
        self.btn_confirmar.first.wait_for(state="visible", timeout=10000)
        self.click_element(self.btn_confirmar.first)

    def alterar_monto_payload(self, nuevo_monto: str) -> None:
        """Modifica el campo de monto en el DOM para pruebas de Price Tampering (OWASP A04)."""
        self.input_monto.first.wait_for(state="visible", timeout=5000)
        self.fill_input(self.input_monto.first, nuevo_monto)

    def verificar_confirmacion(self) -> bool:
        """Valida que la cita haya quedado registrada en la UI."""
        return self.modal_exito.first.is_visible(timeout=8000)