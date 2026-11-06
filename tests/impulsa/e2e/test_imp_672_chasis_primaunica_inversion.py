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

# Rutas locales de Prima Única
PATH_PDF_ISPU = "tests/impulsa/adjuntos/inversiones Imagina Ser Prima Unica/Cotización Imagina Ser Prima Unica.pdf"
PATH_PDF_PENS = "tests/impulsa/adjuntos/inversiones Imagina Ser Prima Unica/Pensiones Imagina Ser Prima Unica.pdf"

# 🛡️ Cabeceras Clonadas Exactas (Anti-WAF)
HEADERS = {
    "authorization": TOKEN_AGENTE, 
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:159.0) Gecko/20100101 Firefox/159.0",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "es-ES,es;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Origin": "https://aseguradora-impulsa-git-staging-tech-x.vercel.app",
    "Connection": "keep-alive"
}

@pytest.mark.business_logic
def test_imp_672_regla6_eliminacion_aportacion_udis_prima_unica():
    """
    Objetivo: (Criterio 11) Validar que en Inversión -> Imagina Ser (Prima Única) 
    la columna 'Aport. en udis' sea completamente eliminada del archivo (no solo oculta) 
    y que las tablas inferiores (Pensión/UDIS) no se descuadren o corrompan.
    """
    assert API_URL and TOKEN_AGENTE, "Faltan variables de entorno esenciales."
    assert os.path.exists(PATH_PDF_ISPU), f"CRÍTICO: No se encontró el PDF en: {PATH_PDF_ISPU}"
    assert os.path.exists(PATH_PDF_PENS), f"CRÍTICO: No se encontró el PDF en: {PATH_PDF_PENS}"
    
    url_upload = f"{API_URL}/chasis/6/ISPU/dual"
    
    print(f"\n[+] 1. Disparando Petición Multipart (Dual) al backend: {url_upload}...")
    
    with open(PATH_PDF_ISPU, "rb") as pdf_ispu, open(PATH_PDF_PENS, "rb") as pdf_pens:
        files = {
            "file": ("Cotización Imagina Ser Prima Unica.pdf", pdf_ispu, "application/pdf"),
            "file2": ("Pensiones Imagina Ser Prima Unica.pdf", pdf_pens, "application/pdf")
        }
        response = requests.post(url_upload, headers=HEADERS, files=files, timeout=30)
        
    assert response.status_code in [200, 201], f"Fallo en Upload. HTTP: {response.status_code}. Respuesta: {response.text}"
    
    print("[+] 2. Interceptando Binario (XLSX) de respuesta en memoria RAM...")
    workbook = openpyxl.load_workbook(BytesIO(response.content), data_only=False)
    sheet = workbook.active
    
    print("[+] 3. Auditando Regla 6 (Eliminación Absoluta y Cero Corrupción)...")
    
    columna_encontrada = False
    errores_encontrados = []
    
    # Escaneo profundo de todo el documento (Filas 1-150, Columnas 1-30)
    for row in sheet.iter_rows(min_row=1, max_row=150, min_col=1, max_col=30):
        for cell in row:
            if isinstance(cell.value, str):
                # 3.1 Data Integrity: Buscar errores estructurales en tablas inferiores
                if "#¡REF!" in cell.value or "#¡VALOR!" in cell.value or "#DIV/0!" in cell.value:
                    errores_encontrados.append(f"[{cell.coordinate}: {cell.value}]")
                    
                # 3.2 Buscar la columna prohibida (usamos .lower() para evitar bypass por casing)
                if "aport. en udis" in cell.value.lower() or "aportación en udis" in cell.value.lower():
                    columna_encontrada = True
                    print(f"🚨 [REGRESIÓN] Columna prohibida hallada en la celda: {cell.coordinate}")
    
    # Inspeccionar columnas ocultas (Warning DevSecOps)
    columnas_ocultas = [col for col, dim in sheet.column_dimensions.items() if dim.hidden]
    if columnas_ocultas:
        print(f"[-] ADVERTENCIA: Se detectaron columnas ocultas en la hoja: {columnas_ocultas}. El script validó que ninguna contenga el texto prohibido.")
    
    # Validaciones Finales
    assert not columna_encontrada, (
        "🚨 [ERROR DE NEGOCIO] La columna 'Aport. en udis' sigue existiendo en el archivo Excel. "
        "El desarrollador no la eliminó (probablemente solo aplicó un estilo visual o la dejó intacta)."
    )
    
    assert len(errores_encontrados) == 0, (
        f"🚨 [CRÍTICO] Eliminar la columna corrompió las tablas inferiores (Pensión/UDIS). "
        f"Se encontraron errores de referencia en cadena: {', '.join(errores_encontrados)}"
    )
    
    print("✅ [APROBADO] La columna 'Aport. en udis' fue purgada físicamente del documento sin descabezar ni corromper las tablas adyacentes.")