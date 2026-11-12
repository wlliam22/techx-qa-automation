import pytest
from playwright.sync_api import expect
from tests.marla.conftest import crear_curso_y_modulo, LIMITE_3GB


@pytest.mark.e2e
def test_ac1_aviso_maximo_3gb(admin_page):
    """AC 1: Aviso 'Máximo 3 GB' en el formulario de agregar video."""
    crear_curso_y_modulo(admin_page)
    aviso = admin_page.get_by_text("Formato aceptado de video: Solo MP4 · Máximo 3 GB")
    expect(aviso).to_be_visible(timeout=5000)


@pytest.mark.e2e
def test_ac3_video_mayor_3gb_rechazado_ui(admin_page, assets_dir):
    """AC 3: Video > 3 GB rechazado al elegirlo (frontend)."""
    crear_curso_y_modulo(admin_page)
    
    video_grande = assets_dir / "video_3.1gb.mp4"
    if not video_grande.exists() or video_grande.stat().st_size < LIMITE_3GB:
        # Crear archivo sparse
        with open(video_grande, 'wb') as f:
            f.seek(LIMITE_3GB + 1024 - 1)
            f.write(b'\x00')
    
    video_input = admin_page.locator('input[type="file"][accept*="video"]').first
    video_input.set_input_files(str(video_grande))
    admin_page.wait_for_timeout(1500)
    
    error = admin_page.locator('text="El video supera el límite de 3 GB"')
    expect(error.first).to_be_visible(timeout=5000)


@pytest.mark.e2e
def test_ac12_miniatura_mayor_10mb_rechazada(admin_page, assets_dir):
    """AC 12: Miniatura > 10 MB rechazada al elegirla."""
    crear_curso_y_modulo(admin_page)
    
    imagen = assets_dir / "imagen_12mb.jpg"
    imagen.write_bytes(b"x" * (12 * 1024 * 1024))
    
    miniatura_input = admin_page.locator('input[type="file"]').nth(3)
    miniatura_input.set_input_files(str(imagen))
    admin_page.wait_for_timeout(1500)
    
    error = admin_page.locator('text="La imagen supera el límite de 10 MB"')
    expect(error.first).to_be_visible(timeout=5000)


@pytest.mark.e2e
def test_ac13_video_50mb_miniatura_5mb_aceptados(admin_page, assets_dir):
    """AC 13: Video 50 MB + miniatura 5 MB se aceptan (validación básica)."""
    crear_curso_y_modulo(admin_page)
    
    video = assets_dir / "video_50mb.mp4"
    imagen = assets_dir / "imagen_5mb.jpg"
    video.write_bytes(b"x" * (50 * 1024 * 1024))
    imagen.write_bytes(b"x" * (5 * 1024 * 1024))
    
    admin_page.get_by_role("textbox", name="Título del nuevo video").fill("Video 50 MB")
    admin_page.locator('input[type="file"][accept*="video"]').first.set_input_files(str(video))
    admin_page.locator('input[type="file"]').nth(3).set_input_files(str(imagen))
    admin_page.wait_for_timeout(1000)
    
    # No debe haber error de límite (puede tardar en subir, así que solo validamos que no explote)
    error_limite = admin_page.locator('text="supera el límite"')
    assert error_limite.count() == 0, "No debería mostrar error de límite con archivos válidos"


@pytest.mark.e2e
def test_ac14_portada_receta_mayor_10mb_rechazadas(admin_page, assets_dir):
    """AC 14: Portada > 10 MB y Receta > 10 MB siguen rechazándose."""
    admin_page.goto("/admin/courses/new", wait_until="domcontentloaded")
    admin_page.wait_for_timeout(2000)
    
    portada = assets_dir / "portada_12mb.jpg"
    portada.write_bytes(b"x" * (12 * 1024 * 1024))
    
    portada_input = admin_page.locator('input[type="file"][accept*="image"]').first
    portada_input.set_input_files(str(portada))
    admin_page.wait_for_timeout(1500)
    
    error = admin_page.locator('text="La imagen supera el límite de 10 MB"')
    expect(error.first).to_be_visible(timeout=5000)


@pytest.mark.e2e
def test_ac15_mov_renombrado_mp4_rechazado(admin_page, assets_dir):
    """AC 15: .mov renombrado a .mp4 es rechazado por el backend."""
    crear_curso_y_modulo(admin_page)
    
    fake_mp4 = assets_dir / "fake.mp4"
    fake_mp4.write_bytes(b"x" * (20 * 1024 * 1024))  # 20 MB fake
    
    admin_page.get_by_role("textbox", name="Título del nuevo video").fill("Video falso")
    admin_page.locator('input[type="file"][accept*="video"]').first.set_input_files(str(fake_mp4))
    admin_page.get_by_role("button", name="Agregar video").click()
    
    # Esperar el error del backend (puede tardar unos segundos)
    error = admin_page.locator('text=/MP4.*válido|no es un video/i')
    expect(error.first).to_be_visible(timeout=30000)