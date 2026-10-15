from playwright.sync_api import Page, expect
from pages.base_page import BasePage


class CatalogPage(BasePage):
    """Page Object para la navegación del Directorio y Perfil de Médico en Docappoint."""

    def __init__(self, page: Page):
        super().__init__(page)
        # Selectores del Directorio
        self.btn_ver_perfil = (
            page.get_by_role("link", name="Ver consultorio digital", exact=False)
            .or_(page.locator("a:has-text('Ver consultorio digital')"))
        )
        # Selectores de Agenda en Perfil
        self.slots_disponibles = (
            page.locator("button.slot-disponible")
            .or_(page.locator("[data-testid^='calendar-slot-']"))
            .or_(page.locator(".calendar-slot, button:has-text(':')"))
        )
        self.btn_agendar_cita = (
            page.get_by_role("button", name="Agendar Cita", exact=False)
            .or_(page.locator("button:has-text('Agendar')"))
        )

    def navegar_al_catalogo(self, base_url: str) -> None:
        """Navega a la raíz o vista de directorio."""
        self.navigate(f"{base_url}/directorio")
        self.page.wait_for_load_state("domcontentloaded")

    def seleccionar_primer_medico(self) -> None:
        """Accede al perfil del primer médico disponible controlando apertura de tabs."""
        self.btn_ver_perfil.first.wait_for(state="visible", timeout=10000)

        # Si el enlace tiene target="_blank", captura la nueva pestaña
        with self.page.context.expect_page() as new_page_info:
            self.click_element(self.btn_ver_perfil.first)
        
        try:
            # Si se abrió en nueva pestaña, reasignamos la página activa
            new_page = new_page_info.value
            new_page.wait_for_load_state("domcontentloaded")
            self.page = new_page
        except Exception:
            # Si navegó en la misma pestaña
            self.page.wait_for_load_state("domcontentloaded")

    def seleccionar_primer_slot_disponible(self) -> None:
        """Espera a que termine de resolver /availability y selecciona un horario libre."""
        # Espera que la llamada de disponibilidad termine antes de interactuar con el DOM
        try:
            self.page.wait_for_response(lambda res: "/availability" in res.url and res.status in (200, 304), timeout=8000)
        except Exception:
            pass

        self.slots_disponibles.first.wait_for(state="visible", timeout=10000)
        self.click_element(self.slots_disponibles.first)