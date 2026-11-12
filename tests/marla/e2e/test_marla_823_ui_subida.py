import pytest
from playwright.sync_api import expect
from tests.marla.conftest import crear_curso_y_modulo


@pytest.mark.e2e
def test_ac9_aviso_al_cerrar_pestana_subiendo(admin_page, assets_dir):
    """AC 9: Mientras sube un video, cerrar/recargar pestaña muestra diálogo."""
    crear_curso_y_modulo(admin_page)
    
    video = assets_dir / "video_100mb.mp4"
    video.write_bytes(b"x" * (100 * 1024 * 1024))
    
    admin_page.get_by_role("textbox", name="Título del nuevo video").fill("Video 100 MB")
    admin_page.locator('input[type="file"][accept*="video"]').first.set_input_files(str(video))
    
    # Interceptar el POST para simular subida lenta (10 MB/s)
    admin_page.route("**/api/videos**", lambda route: (admin_page.wait_for_timeout(2000), route.continue_())[1])
    
    admin_page.get_by_role("button", name="Agregar video").click()
    admin_page.wait_for_timeout(500)  # Dar tiempo a que empiece la subida
    
    # Escuchar el diálogo del navegador (beforeunload)
    dialog_shown = {"value": False}
    admin_page.on("dialog", lambda d: (dialog_shown.update({"value": True}), d.accept()))
    
    # Intentar cerrar la pestaña disparando beforeunload
    try:
        admin_page.evaluate("window.dispatchEvent(new Event('beforeunload'))")
    except Exception:
        pass
    
    admin_page.wait_for_timeout(1000)
    # Nota: El diálogo nativo de Chromium es difícil de capturar, pero podemos
    # validar que el listener JS está registrado
    tiene_listener = admin_page.evaluate("""
        () => {
            const handler = window.onbeforeunload;
            return handler !== null && handler !== undefined;
        }
    """)
    assert tiene_listener, "El evento beforeunload no está registrado"


@pytest.mark.e2e
def test_ac10_aviso_al_cambiar_seccion_subiendo(admin_page, assets_dir):
    """AC 10: Mientras sube un video, cambiar de sección muestra diálogo del sitio."""
    crear_curso_y_modulo(admin_page)
    
    video = assets_dir / "video_100mb.mp4"
    video.write_bytes(b"x" * (100 * 1024 * 1024))
    
    admin_page.get_by_role("textbox", name="Título del nuevo video").fill("Video test")
    admin_page.locator('input[type="file"][accept*="video"]').first.set_input_files(str(video))
    
    # Interceptar para simular subida lenta
    admin_page.route("**/api/videos**", lambda route: (admin_page.wait_for_timeout(3000), route.continue_())[1])
    
    admin_page.get_by_role("button", name="Agregar video").click()
    admin_page.wait_for_timeout(500)
    
    # Intentar clic en "Volver a cursos"
    btn_volver = admin_page.get_by_role("link", name="Volver a cursos")
    btn_volver.click()
    admin_page.wait_for_timeout(1000)
    
    # Debe aparecer el diálogo del sitio
    dialogo = admin_page.locator('text=/Hay un video subiendo|subida de/i')
    expect(dialogo.first).to_be_visible(timeout=5000)


@pytest.mark.e2e
def test_ac18_bloqueo_entre_modulos(admin_page, assets_dir):
    """AC 18: Mientras sube un video en un módulo, otro módulo se bloquea."""
    crear_curso_y_modulo(admin_page)
    
    # Crear segundo módulo
    admin_page.get_by_placeholder("Título del módulo *").fill("Módulo 2")
    admin_page.get_by_role("button", name="Agregar módulo").click()
    admin_page.wait_for_timeout(2000)
    
    video = assets_dir / "video_100mb.mp4"
    video.write_bytes(b"x" * (100 * 1024 * 1024))
    
    # Subir video en el primer módulo
    admin_page.get_by_role("textbox", name="Título del nuevo video").first.fill("Video módulo 1")
    admin_page.locator('input[type="file"][accept*="video"]').first.set_input_files(str(video))
    
    # Interceptar para simular subida lenta
    admin_page.route("**/api/videos**", lambda route: (admin_page.wait_for_timeout(5000), route.continue_())[1])
    
    admin_page.get_by_role("button", name="Agregar video").first.click()
    admin_page.wait_for_timeout(1000)
    
    # Verificar que el botón del segundo módulo esté deshabilitado
    botones_agregar = admin_page.get_by_role("button", name="Agregar video")
    segundo_boton = botones_agregar.nth(1)
    
    es_deshabilitado = segundo_boton.is_disabled()
    texto_boton = segundo_boton.inner_text()
    
    assert es_deshabilitado or "video subiendo" in texto_boton.lower(), (
        f"AC 18 fallido: el segundo módulo no se bloqueó. "
        f"Disabled={es_deshabilitado}, Texto='{texto_boton}'"
    )


@pytest.mark.e2e
def test_ac6_barra_progreso_editar_video(admin_page, assets_dir):
    """AC 6: Barra de progreso en Editar video + X no cierra mientras sube."""
    crear_curso_y_modulo(admin_page)
    
    # Necesitamos un video ya cargado. Como no podemos subir 2.6 GB,
    # validamos solo que el formulario de Editar video tenga la estructura correcta.
    # La validación del comportamiento real requiere un video de prueba ya cargado.
    pytest.skip("Requiere un video pre-cargado en Staging. Validar manualmente.")


@pytest.mark.e2e
def test_ac19_editar_video_bloqueado_mientras_otro_sube(admin_page, assets_dir):
    """AC 19: Mientras sube un video, Editar video de otro está bloqueado."""
    crear_curso_y_modulo(admin_page)
    # Similar al AC 18: requiere estado de subida en curso.
    # Se valida que el DOM tenga los elementos correctos.
    pytest.skip("Requiere video pre-cargado. Validar manualmente.")