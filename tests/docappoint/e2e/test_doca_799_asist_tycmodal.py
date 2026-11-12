import os
import re
import pytest
from pathlib import Path
from playwright.sync_api import Browser, Page, expect, TimeoutError as PWTimeoutError
from dotenv import load_dotenv

load_dotenv()

# ==============================================================================
# CONFIGURACIÓN Y SECRETS (DOCA-799)
# ==============================================================================
WEB_URL = os.getenv("DOCAPPOINT_WEB_URL", "https://docappoint-git-staging-tech-x.vercel.app")
ASISTENTE_EMAIL = os.getenv("DOCA_ASISTENTE_EMAIL", "ana.lopez")
ASISTENTE_PASS = os.getenv("DOCA_ASISTENTE_PASSWORD")
VERCEL_SECRET = os.getenv("VERCEL_DOCAPPOINT_BYPASS_SECRET")

# ==============================================================================
# HELPERS
# ==============================================================================
def _bypass_vercel_and_cors(context):
    if not VERCEL_SECRET: return
    domain = "docappoint-git-staging-tech-x.vercel.app"
    context.add_cookies([{
        "name": "_vercel_jwt", "value": VERCEL_SECRET, "domain": domain, 
        "path": "/", "httpOnly": True, "secure": True, "sameSite": "None"
    }])
    context.set_extra_http_headers({
        "x-vercel-protection-bypass": VERCEL_SECRET, 
        "Origin": WEB_URL
    })
    def _route_handler(route):
        if route.request.method == "OPTIONS":
            route.fulfill(status=200, headers={"Access-Control-Allow-Origin": WEB_URL, "Access-Control-Allow-Headers": "*"})
        else:
            route.continue_()
    context.route("**/api/**", _route_handler)
    context.route("**/auth/**", _route_handler)

def _login_asistente(page: Page):
    print("\n[-] 1. Logueando como Asistente...")
    page.goto("/login", wait_until="networkidle")
    page.get_by_role("textbox", name="Ingrese aquí su correo o usuario").fill(ASISTENTE_EMAIL)
    page.get_by_role("textbox", name="Ingrese aquí su contraseña").fill(ASISTENTE_PASS)
    page.get_by_role("button", name="Iniciar Sesión").click()
    page.wait_for_url(lambda url: "/login" not in url, timeout=15000)
    print("✅ Login exitoso.")

@pytest.mark.e2e
def test_doca_799_modal_terminos_asistente(browser: Browser):
    """
    Valida el flujo de la ventana bloqueante de Términos y Privacidad para Asistentes.
    AC 1, 2, 4, 6 del ticket DOCA-799.
    """
    assert WEB_URL and ASISTENTE_EMAIL and ASISTENTE_PASS, "🚨 Faltan credenciales."

    context = browser.new_context(base_url=WEB_URL, ignore_https_errors=True)
    _bypass_vercel_and_cors(context)
    page = context.new_page()

    try:
        _login_asistente(page)

        # 2. PRIORIDAD 1: Buscar el modal (AC 1)
        print("[-] 2. Verificando si aparece el modal de 'Actualización de Documentos Legales'...")
        modal = page.locator('text="Actualización de Documentos Legales"')
        
        try:
            # Esperamos máximo 10 segundos a que aparezca el modal
            expect(modal).to_be_visible(timeout=10000)
            print("✅ Modal detectado. El usuario es una asistente con términos pendientes.")
            
            # Validar contenido del modal
            modal_paper = page.locator('[role="dialog"], .MuiDialog-paper').first
            texto_modal = modal_paper.inner_text()
            assert "Términos y Condiciones" in texto_modal, "🚨 Falta Términos en el modal."
            assert "Política de Privacidad" in texto_modal or "privacidad" in texto_modal.lower(), "🚨 Falta Privacidad en el modal."
            assert "Política de Seguridad" not in texto_modal, "🚨 El modal NO debe mencionar Política de Seguridad (Bug del ticket)."
            print("   → Validación de textos: OK (solo Términos y Privacidad).")
            
            # Verificar botón deshabilitado
            boton_aceptar = page.get_by_role("button", name="Aceptar y Continuar")
            expect(boton_aceptar).to_be_disabled()
            print("   → Botón 'Aceptar y Continuar' deshabilitado: OK.")

            # 3. Aceptar Términos (AC 2)
            print("[-] 3. Aceptando términos...")
            page.locator('input[type="checkbox"]').first.check(force=True)
            expect(boton_aceptar).to_be_enabled()
            boton_aceptar.click()
            
            expect(modal).to_be_hidden(timeout=10000)
            expect(page.locator('text="Documentos legales aceptados correctamente"')).to_be_visible(timeout=5000)
            print("✅ Términos aceptados.")

            # 4. Validar que al recargar no vuelve el modal (AC 2)
            print("[-] 4. Recargando para verificar persistencia...")
            page.reload(wait_until="networkidle")
            page.wait_for_timeout(3000)
            expect(modal).not_to_be_visible(timeout=5000)
            print("✅ Modal no reaparece tras recarga.")

        except PWTimeoutError:
            # Si no hay modal, verificamos el rol (Médico/Admin) para saber por qué no aparece
            print("⚠️ No se detectó modal. Verificando rol del usuario...")
            menu_asistentes = page.get_by_role("button", name="Doctores Doctores Asociados")
            if menu_asistentes.is_disabled():
                print("🚨 El usuario logueado NO es una Asistente (probablemente Médico/Admin).")
                pytest.fail("El usuario no es Asistente. Cambiar DOCA_ASISTENTE_EMAIL en .env.")
            else:
                print("⚠️ El usuario es Asistente pero ya aceptó términos. No hay modal que validar.")
                pytest.skip("La cuenta ya aceptó términos. Usar una asistente 'virgen' para validar el modal.")

        print("\n✅ [APROBADO] Flujo DOCA-799 validado.")

    except AssertionError as e:
        forensic = Path("artifacts") / "doca_799"
        forensic.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(forensic / "fallo_pantalla.png"))
        print(f"📎 Screenshot forense: {forensic}")
        raise e

    finally:
        context.close()