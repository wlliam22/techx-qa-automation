from playwright.sync_api import Page, Locator, Response
from typing import Callable, Optional, Literal
import json

class BasePage:
    def __init__(self, page: Page):
        self.page = page

    def navigate(
        self, 
        url: str, 
        wait_until: Literal["commit", "domcontentloaded", "load", "networkidle"] = "domcontentloaded"
    ) -> None:
        """
        Navega a la URL esperando domcontentloaded para evitar bloqueos
        por polling continuo en segundo plano.
        """
        self.page.goto(url, wait_until=wait_until, timeout=30000)

    def get_by_testid(self, test_id: str) -> Locator:
        """Selector prioritario exigido en protocolos QA."""
        return self.page.get_by_test_id(test_id)

    def click_element(self, locator: Locator) -> None:
        """Click con auto-wait nativo de Playwright."""
        locator.wait_for(state="visible", timeout=10000)
        locator.click()

    def fill_input(self, locator: Locator, text: str) -> None:
        """Limpieza y llenado de inputs de formulario."""
        locator.wait_for(state="visible", timeout=10000)
        locator.fill(text)

    def capture_api_response(self, url_pattern: str, trigger_action: Callable) -> Optional[dict]:
        """
        DevSecOps Utility: Intercepta la respuesta JSON de un endpoint
        durante una acción del usuario para auditar Data Bleeding (Zero Trust).
        """
        with self.page.expect_response(
            lambda response: url_pattern in response.url and response.status in [200, 201]
        ) as response_info:
            trigger_action()
        
        response: Response = response_info.value
        try:
            return response.json()
        except Exception:
            return None