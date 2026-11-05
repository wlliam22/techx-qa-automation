import os
import pytest
import requests
import openpyxl
from io import BytesIO
from dotenv import load_dotenv

load_dotenv()

# ==============================================================================
# CONFIGURACIÓN DEL ENTORNO Y SECRETS
# ==============================================================================
API_URL = os.getenv("IMP_API_URL")
TOKEN_AGENTE = os.getenv("IMP_JWT_TOKEN_AGENTE")
PATH_PDF_MARTHA = os.getenv("IMP_PATH_PDF_MARTHA")

HEADERS = {"authorization": TOKEN_AGENTE}

@pytest.mark.business_logic
def test_imp_480_certify_martha_math():
    """
    Objetivo: Certificar la corrección de IMP-BUG-188 validando que el backend 
    inyecte dinámicamente las primas anuales en las fórmulas del Excel.
    Arquitectura confirmada: Flujo One-Shot (PDF In -> Excel Out).
    """
    assert API_URL, "CRÍTICO: IMP_API_URL no configurado."
    assert PATH_PDF_MARTHA, "CRÍTICO: IMP_PATH_PDF_MARTHA no configurado."
    
    url_upload = f"{API_URL}/chasis/2/VM"
    
    print(f"\n[+] 1. Disparando PDF al backend (One-Shot): {url_upload}...")
    with open(PATH_PDF_MARTHA, "rb") as pdf_file:
        files = {"file": ("prueba480.PDF", pdf_file, "application/pdf")}
        response = requests.post(url_upload, headers=HEADERS, files=files)
        
    assert response.status_code == 200, f"Fallo en Upload. Código HTTP: {response.status_code}"
    
    print("[+] 2. Interceptando Binario (XLSX) directo de la respuesta HTTP...")
    # Pasamos el binario crudo directo al parser de Excel
    workbook = openpyxl.load_workbook(BytesIO(response.content))
    sheet = workbook.active

    print("[+] 3. Auditando FÓRMULAS inyectadas en memoria (BUG-188)...")
    col_aportacion_pesos = 'N' 
    fila_y1 = 17
    fila_y11 = 27 
    celda_formula_recuperacion = 'S39' 

    formula_y1 = sheet[f"{col_aportacion_pesos}{fila_y1}"].value
    formula_y11 = sheet[f"{col_aportacion_pesos}{fila_y11}"].value
    formula_recuperacion = sheet[celda_formula_recuperacion].value

    # ASERCIONES FINANCIERAS (Verificación del Parche)
    print(f"Fórmula Año 1 (Esperada con 2300.0) -> Obtenida: {formula_y1}")
    assert "2300.0" in str(formula_y1), "🚨 [REGRESIÓN] El backend no inyectó la prima del Año 1 en la fórmula."

    print(f"Fórmula Año 11 (Esperada con 2314.0) -> Obtenida: {formula_y11}")
    assert "2314.0" in str(formula_y11), "🚨 [BUG-188 VIVO] El backend sigue inyectando prima estática en Año 11."
    
    print(f"Fórmula Total Recuperación -> Obtenida: {formula_recuperacion}")
    assert "SUM(" in str(formula_recuperacion), "🚨 Falla en inyección de fórmula de sumatoria total."

    print("✅ [CERTIFICADO] Arquitectura One-Shot validada. La matemática inyectada es íntegra.")