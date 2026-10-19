import os
from playwright.sync_api import Page
from pages.base_page import BasePage
from utils.credentials import CredentialManager, UserRole


class LoginPage(BasePage):
    def __init__(self, page: Page):
        super().__init__(page)
        self.input_email = (
            page.get_by_label("Correo", exact=False)
            .or_(page.get_by_placeholder("correo", exact=False))
            .or_(page.locator("input[type='email'], input[name='email'], input[type='text']").first)
        )
        self.input_password = (
            page.get_by_label("Contraseña", exact=False)
            .or_(page.get_by_placeholder("contraseña", exact=False))
            .or_(page.locator("input[type='password']"))
        )
        self.btn_submit = (
            page.get_by_role("button", name="Iniciar sesión", exact=False)
            .or_(page.locator("button[type='submit']"))
        )

    def login_with_role(self, role: UserRole, base_url: str, save_state: bool = True) -> None:
        """Autentica según el rol especificado, diagnostica la red y persiste el estado."""
        cred = CredentialManager.get_credentials(role)

        # 1. Monitoreo Forense de Red y Consola en Vivo
        self.page.on("console", lambda msg: print(f"   [CONSOLE {msg.type.upper()}] {msg.text}"))
        self.page.on("request", lambda req: print(f"   [REQ OUT] {req.method} -> {req.url}"))
        self.page.on("response", lambda res: print(f"   [RES IN] {res.status} <- {res.url}"))
        self.page.on("requestfailed", lambda req: print(f"   [NET FAILED] {req.method} {req.url} -> Motivo: {req.failure}"))

        # 2. Navegación a la pantalla de Login
        self.navigate(f"{base_url}/login")

        # 3. Interacción con los inputs de formulario
        self.input_email.first.wait_for(state="visible", timeout=15000)
        self.fill_input(self.input_email.first, cred.email)

        self.input_password.first.wait_for(state="visible", timeout=5000)
        self.fill_input(self.input_password.first, cred.password)

        print(f"\n[AUTH ATTEMPT] Enviando credenciales para el rol: {role.value} ({cred.email})...")
        self.click_element(self.btn_submit.first)

        # 4. Espera de redirección tras autenticación exitosa
        self.page.wait_for_url(lambda url: "/login" not in url, timeout=15000)

        # 5. Persistencia de estado de sesión
        if save_state:
            self.page.context.storage_state(path=cred.auth_state_path)
            print(f"[AUTH SUCCESS] Estado persistido en {cred.auth_state_path}")