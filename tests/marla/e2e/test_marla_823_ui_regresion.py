import pytest
from playwright.sync_api import expect


@pytest.mark.e2e
def test_ac7_solo_cambio_titulo_sin_barra(admin_page):
    """AC 7: Cambiar solo el título en Editar video NO muestra barra de progreso."""
    pytest.skip("Requiere video pre-cargado. Validar manualmente.")


@pytest.mark.e2e
def test_ac11_sin_aviso_sin_subida(admin_page):
    """AC 11: Sin subida en curso, no aparece ningún aviso al navegar."""
    crear_curso_y_modulo(admin_page)
    
    # Navegar entre secciones sin subir nada
    admin_page.get_by_role("link", name="Volver a cursos").click()
    admin_page.wait_for_timeout(1000)
    
    # No debe aparecer "Hay un video subiendo"
    dialogo = admin_page.locator('text="Hay un video subiendo"')
    assert dialogo.count() == 0, "No debería mostrar diálogo sin subida"


@pytest.mark.e2e
def test_ac2_subida_real_2_6gb(admin_page):
    """AC 2: Subida real de 2.6 GB con barra de progreso (37 min)."""
    pytest.skip("Requiere 37 min y 2.6 GB real. Solo validable manualmente.")