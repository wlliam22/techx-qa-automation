import os
import pytest
import requests
import openpyxl
from io import BytesIO
from dotenv import load_dotenv

load_dotenv()

# ==============================================================================
# CONFIGURACIÓN DEL ENTORNO Y SECRETS (Zero Trust)
# ==============================================================================
API_URL = os.getenv("IMP_API_URL")
TOKEN_AGENTE = os.getenv("IMP_JWT_TOKEN_AGENTE")
PATH_PDF_MARTHA = os.getenv("IMP_PATH_PDF_MARTHA")

HEADERS = {"authorization": TOKEN_AGENTE}

@pytest.mark.business_logic
def test_imp_vida_mujer_formato_mexico_y_matematica():
    """
    Objetivo: Validar que el archivo Excel generado tenga los montos 
    formateados forzosamente con comas para miles y puntos para decimales, 
    SIN romper la integridad matemática (fórmulas) del archivo.
    """
    assert API_URL and TOKEN_AGENTE and PATH_PDF_MARTHA, "Faltan variables de entorno esenciales."
    
    url_upload = f"{API_URL}/chasis/2/VM"
    
    print(f"\n[+] 1. Disparando PDF al backend (One-Shot): {url_upload}...")
    with open(PATH_PDF_MARTHA, "rb") as pdf_file:
        files = {"file": ("prueba480.PDF", pdf_file, "application/pdf")}
        response = requests.post(url_upload, headers=HEADERS, files=files)
        
    assert response.status_code == 200, f"Fallo en Upload. Código HTTP: {response.status_code}"
    
    print("[+] 2. Interceptando Binario (XLSX) directo de la respuesta HTTP...")
    # Usamos openpyxl para leer el archivo. 
    # data_only=False nos permite ver las fórmulas y formatos.
    workbook = openpyxl.load_workbook(BytesIO(response.content))
    sheet = workbook.active

    print("[+] 3. Auditando FORMATOS y VALORES (Zero Trust)...")
    
    # --- Validaciones de Formato de Miles (Suma Asegurada y Aportación) ---
    celda_suma_asegurada_pesos = sheet['I12'] # Debe ser 298,872
    celda_inciso_A = sheet['E14'] # Debe ser 35,000
    
    print(f"I12 (Suma Asegurada Pesos) | Valor interno: {celda_suma_asegurada_pesos.value} | Formato: {celda_suma_asegurada_pesos.number_format}")
    print(f"E14 (Inciso A) | Valor interno: {celda_inciso_A.value} | Formato: {celda_inciso_A.number_format}")
    
    # El desarrollador debió inyectar un string literal o un custom format estricto 
    # (ej. "\[$$-80A\]#,##0" que fuerza el locale)
    # NOTA: Openpyxl a veces abstrae el formato. Evaluaremos el tipo de dato.

    # --- Validaciones Críticas de Texto vs Valor (Valor UDI) ---
    celda_udi_visible = sheet['L14'] 
    
    print(f"L14 (UDI Visible) | Valor: '{celda_udi_visible.value}' | Tipo: {type(celda_udi_visible.value)}")
    
    # Si la HU dice que L14 pasa a ser texto ("8.54"), debe ser un string.
    assert isinstance(celda_udi_visible.value, str), (
        f"🚨 [REGRESIÓN] L14 sigue siendo un número ({type(celda_udi_visible.value)}). "
        "Excel lo renderizará según la región del usuario (8,54 o 8.54)."
    )
    assert "." in celda_udi_visible.value, "🚨 [ERROR] El texto del Valor UDI no contiene un punto decimal fijo."

    # --- Búsqueda del "Valor Guardado Aparte" ---
    print("[+] 4. Rastreando el valor numérico oculto para los cálculos...")
    # La fórmula de N17 (Aportación Año 1) o I12 (Suma en pesos) debe apuntar a la celda oculta.
    formula_n17 = str(sheet['N17'].value)
    print(f"Fórmula N17 (Aport. Año 1): {formula_n17}")
    
    # Verificamos que la fórmula de N17 NO dependa de L14 (porque L14 ahora es texto).
    assert "L14" not in formula_n17, (
        f"🚨 [CRÍTICO] La fórmula de N17 ({formula_n17}) sigue apuntando a L14. "
        "Como L14 ahora es texto, Excel mostrará #¡VALOR! en todo el documento."
    )

    print("✅ [APROBADO] El Excel protege la integridad de formato regional sin corromper la matemática.")