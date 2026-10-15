import re
import pytest
from playwright.sync_api import Page, expect

# Constantes del entorno
DOCA_URL_PACIENTE = "https://docappoint-git-staging-tech-x.vercel.app/preregistro/f325ca2a" # Ajustar a una ruta válida de Staging
DOCA_URL_MEDICO = "https://docappoint-git-staging-tech-x.vercel.app/citas"
API_ENDPOINT = "**/getPreregistros*"

class TestPreregistroRateLimitUI:

    @pytest.fixture(autouse=True)
    def setup_vercel_bypass(self, page: Page):
        # Regla #4: Cruzar el firewall de Vercel para que el DOM cargue
        page.set_extra_http_headers({
            "x-vercel-protection-bypass": "oL9J8uCUbCOQkpLd85zYXdpe2YvPACSZ" # Ajustar según .env
        })

    def test_paciente_preregistro_rate_limit_alert_mock(self, page: Page):
        """
        Flujo: Paciente abre el pre-registro.
        Táctica: Secuestrar red, forzar 429, validar renderizado y redondeo matemático.
        """
        print("\n[Mock] Secuestrando red para simular ataque de Rate Limit (150 segundos)...")

        def handle_route(route):
            # Simulamos el backend bloqueando con el nuevo formato acordado
            route.fulfill(
                status=429,
                content_type="application/json",
                json={
                    "ok": False,
                    "code": "TOO_MANY_REQUESTS",
                    "msg": "Límite excedido",
                    "retryAfter": 150 # 150 segundos = 2.5 minutos -> Debe redondear a 3 en UI
                }
            )

        # Interceptamos la llamada
        page.route(API_ENDPOINT, handle_route)

        # Navegamos a la vista del paciente
        page.goto(DOCA_URL_PACIENTE)

        # Aserciones (Hooks de Automatización)
        # Exigimos a Emanuel que el contenedor del error tenga este data-testid
        alerta_bloqueo = page.locator('[data-testid="alert-rate-limit"]')
        
        expect(alerta_bloqueo).to_be_visible(timeout=5000)
        
        # Validar la regla de negocio del redondeo ("N redondeado hacia arriba")
        texto_alerta = alerta_bloqueo.text_content()
        assert "3 minutos" in texto_alerta, f"Error en redondeo matemático UI. Esperaba '3 minutos', frontend mostró: {texto_alerta}"
        assert "Demasiados intentos" in texto_alerta, "El copy del PO no coincide con la alerta."

        # Validar que el formulario sigue en pantalla (criterio de Maryel)
        formulario = page.locator('[data-testid="form-preregistro"]')
        expect(formulario).to_be_visible()

    def test_medico_cita_preregistro_rate_limit_alert_mock(self, page: Page):
        """
        Flujo: Médico abre una cita para ver el pre-registro bloqueado.
        Requiere: Estado de sesión del médico (auth_doctor.json).
        """
        print("\n[Mock] Validando UI del Médico ante Rate Limit (50 segundos)...")

        def handle_route(route):
            route.fulfill(
                status=429,
                content_type="application/json",
                json={
                    "retryAfter": 50 # 50 segundos -> Debe redondear a 1 minuto (nunca menor que 1)
                }
            )

        page.route(API_ENDPOINT, handle_route)
        
        # Asumiendo que Playwright inyectó la sesión previamente vía context
        page.goto(DOCA_URL_MEDICO)
        
        # Simular click en la primera tarjeta de cita para abrir el detalle
        page.locator('[data-testid="cita-card"]').first.click()

        # Aserción en la vista de detalle
        alerta_medico = page.locator('[data-testid="alert-rate-limit-medico"]')
        expect(alerta_medico).to_be_visible(timeout=5000)
        
        # Validar la regla "Nunca menor que 1"
        assert "1 minuto" in alerta_medico.text_content(), "El frontend no respetó el límite inferior de 1 minuto."