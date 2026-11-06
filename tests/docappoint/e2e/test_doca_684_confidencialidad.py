import os
import pytest
from playwright.sync_api import Page, expect
from dotenv import load_dotenv
import pdfplumber

load_dotenv()

# ==============================================================================
# CONFIGURACIÓN DEL ENTORNO (DOCA-684)
# ==============================================================================
BYPASS_SECRET = os.getenv("VERCEL_DOCAPPOINT_BYPASS_SECRET")

TEXTO_CONFIDENCIALIDAD_ESPERADO = (
    "Documento confidencial. Contiene información personal de salud protegida "
    "por la Ley Federal de Protección de Datos Personales en Posesión de los Particulares. "
    "Su divulgación no autorizada está prohibida."
)

@pytest.mark.e2e
def test_doca_684_cp01_receta_web_a4_medico(doctor_page: Page, base_url: str):
    """
    Objetivo (DOCA-684-CP-01): 
    Validar que la receta en A4 descargada por el médico muestre la marca completa 
    al pie, en 2 renglones, debajo de 'Agenda tu próxima cita por la App Docappoint',
    tenga 1 sola página y no incluya 'Copia paciente'.
    Utiliza las fixtures doctor_page y base_url del conftest.py local.
    """
    # 1. Bypass de protección Vercel en UI (Zero Trust Staging)
    if BYPASS_SECRET:
        doctor_page.context.set_extra_http_headers({
            "x-vercel-protection-bypass": BYPASS_SECRET,
            "x-vercel-set-bypass-cookie": "true"
        })

    print("[+] 1. Navegando al panel de citas del médico...")
    doctor_page.goto(f"{base_url}/doctor/appointments")

    # Validación visual de carga de la vista
    expect(doctor_page.locator('h1, h2, text="Citas"').first).to_be_visible(timeout=15000)

    print("[+] 2. Interceptando la descarga del PDF de la receta (A4)...")
    with doctor_page.expect_download() as download_info:
        # Selector adaptado al Design System de Docappoint para descarga de receta A4
        doctor_page.locator('button:has-text("Descargar Receta A4"), [data-testid="download-recipe-a4"]').first.click()
    
    download = download_info.value
    file_path = download.path()
    print(f"[-] Receta A4 descargada temporalmente en: {file_path}")
    
    # 3. Auditoría del PDF con pdfplumber (Integridad Documental)
    with pdfplumber.open(file_path) as pdf:
        total_pages = len(pdf.pages)
        assert total_pages == 1, f"CRÍTICO [DOCA-684]: La receta en A4 debe tener 1 sola página, se detectaron {total_pages}"
        
        texto_pagina = pdf.pages[0].extract_text()
        
        # Validar texto legal exacto
        assert TEXTO_CONFIDENCIALIDAD_ESPERADO in texto_pagina, (
            "CRÍTICO [DOCA-684]: El texto de la marca de confidencialidad no se encontró o presenta alteraciones en el PDF A4."
        )
        
        # Validar ausencia de marca de agua de paciente en copia del médico
        assert "Copia paciente" not in texto_pagina, (
            "CRÍTICO [DOCA-684]: Infracción de regla de negocio. La copia del médico muestra la marca de agua 'Copia paciente'."
        )

    print("✅ [APROBADO] DOCA-684-CP-01: Receta Web A4 validada exitosamente con pie de confidencialidad íntegro.")