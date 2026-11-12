import io
import pytest
import requests
from requests.exceptions import ConnectionError as ReqConnectionError, ChunkedEncodingError
from tests.marla.conftest import API_URL, headers_api, make_sparse_bytes


@pytest.mark.api
def test_ac5_api_video_mayor_3gb_rechazado(admin_token, curso_modulo_api):
    """AC 5: Backend rechaza video > 3 GB (HTTP 400 o socket reset)."""
    chapter_id = curso_modulo_api["chapter_id"]
    data = {"chapterId": chapter_id, "title": "Video 3.3 GB", "description": "", "isFreePreview": "false"}
    files = {"video": ("video_3.3gb.mp4", make_sparse_bytes(3_321_225_473), "video/mp4")}
    
    try:
        r = requests.post(f"{API_URL}/api/videos",
            headers=headers_api(admin_token, is_multipart=True),
            data=data, files=files, timeout=120)
        assert r.status_code == 400, f"Se esperaba 400, se obtuvo {r.status_code}"
    except (ReqConnectionError, ChunkedEncodingError):
        pass  # Socket reset = rechazo válido


@pytest.mark.api
def test_ac5_api_miniatura_mayor_10mb(admin_token, curso_modulo_api):
    """Miniatura > 10 MB rechazada en backend."""
    chapter_id = curso_modulo_api["chapter_id"]
    data = {"chapterId": chapter_id, "title": "Video + miniatura", "description": "", "isFreePreview": "false"}
    files = {
        "video": ("video.mp4", io.BytesIO(b"x" * (1024 * 1024)), "video/mp4"),
        "thumbnail": ("thumb.jpg", io.BytesIO(b"x" * (12 * 1024 * 1024)), "image/jpeg"),
    }
    r = requests.post(f"{API_URL}/api/videos",
        headers=headers_api(admin_token, is_multipart=True),
        data=data, files=files, timeout=30)
    assert r.status_code == 400


@pytest.mark.api
def test_ac17_permisos_solo_admin(admin_token, curso_modulo_api):
    """AC 17: Comprador no puede subir videos (403)."""
    import os
    comp_email = os.getenv("MARLA_COMPRADOR_EMAIL")
    comp_pass = os.getenv("MARLA_COMPRADOR_PASSWORD")
    if not comp_email:
        pytest.skip("Sin credenciales de comprador")
    
    r = requests.post(f"{API_URL}/api/auth/signin",
        json={"email": comp_email, "password": comp_pass},
        headers=headers_api(), timeout=15)
    assert r.status_code == 200
    token = r.json().get("token") or r.json().get("jwt")
    
    chapter_id = curso_modulo_api["chapter_id"]
    data = {"chapterId": chapter_id, "title": "Prohibido", "description": "", "isFreePreview": "false"}
    files = {"video": ("video.mp4", io.BytesIO(b"x" * (1024 * 1024)), "video/mp4")}
    
    r = requests.post(f"{API_URL}/api/videos",
        headers=headers_api(token, is_multipart=True),
        data=data, files=files, timeout=30)
    assert r.status_code == 403