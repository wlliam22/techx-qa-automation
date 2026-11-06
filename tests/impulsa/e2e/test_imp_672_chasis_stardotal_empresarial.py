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

# Ruta local del PDF Empresarial Star Dotal 10 Pagos
PATH_PDF_SD_EMP = "tests/impulsa/adjuntos/Empresarial stardotal 10 pagos/1.- Empresarial STAR DOTAL 10-1.pdf"

# 🛡️ Cabeceras Clonadas Exactas (Anti-WAF y Autenticación Cruda)
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
def test_imp_672_regla2_desplazamiento_aportacion_total_empresarial():
    """
    Objetivo: (Criterio 7) Validar que en Empresarial -> Star Dotal -> 10 Pagos, 
    la corrección estructural ('Aportación Total' movida a la derecha)
    se propagó correctamente y no generó colapso de fórmulas (OWASP A08).
    """
    assert API_URL and TOKEN_AGENTE, "Faltan variables de entorno esenciales (IMP_API_URL, IMP_JWT_TOKEN_AGENTE)."
    assert os.path.exists(PATH_PDF_SD_EMP), f"CRÍTICO: No se encontró el PDF en: {PATH_PDF_SD_EMP}"
    
    # Endpoint interceptado para el flujo EMPRESARIAL (Familia 5)
    url_upload = f"{API_URL}/chasis/5/SD10"
    
    print(f"\n[+] 1. Disparando Petición Multipart al backend: {url_upload}...")
    
    with open(PATH_PDF_SD_EMP, "rb") as pdf_file:
        files = {
            "file": ("1.- Empresarial STAR DOTAL 10-1.pdf", pdf_file, "application/pdf")
        }
        
        response = requests.post(url_upload, headers=HEADERS, files=files, timeout=30)
        
    assert response.status_code in [200, 201], f"Fallo en Upload. Código HTTP: {response.status_code}. Respuesta: {response.text}"
    
    print("[+] 2. Interceptando Binario (XLSX) de respuesta en memoria RAM...")
    workbook = openpyxl.load_workbook(BytesIO(response.content), data_only=False)
    sheet = workbook.active

    print("[+] 3. Auditando Regla 2 (Propagación a Empresarial y Cero Errores)...")
    
    celda_aportacion = None
    errores_encontrados = []
    
    # Escaneo Zero Trust de la hoja (Filas 1-100, Columnas A-Z)
    for row in sheet.iter_rows(min_row=1, max_row=100, min_col=1, max_col=26):
        for cell in row:
            if isinstance(cell.value, str):
                # 3.1. Buscar errores matemáticos (Data Integrity OWASP A08)
                if "#¡REF!" in cell.value or "#¡VALOR!" in cell.value or "#DIV/0!" in cell.value:
                    errores_encontrados.append(f"[{cell.coordinate}: {cell.value}]")
                
                # 3.2. Localizar etiqueta dinámica
                if "Aportación Total" in cell.value:
                    celda_aportacion = cell

    # Validación 1: Prevención de Corrupción Matemática
    assert len(errores_encontrados) == 0, (
        f"🚨 [CRÍTICO] Mover la columna en el módulo EMPRESARIAL corrompió fórmulas. "
        f"Se encontraron errores de referencia: {', '.join(errores_encontrados)}"
    )
    
    # Validación 2: Presencia de la Etiqueta
    assert celda_aportacion, "🚨 [ERROR DE NEGOCIO] No se encontró la celda 'Aportación Total' en el chasis Empresarial."
    
    print(f"[-] 'Aportación Total' localizada en la celda: {celda_aportacion.coordinate}")
    
    # Validación 3: Radar de barrido horizontal para sortear celdas combinadas (Merged Cells)
    col_idx = celda_aportacion.column
    row_idx = celda_aportacion.row
    valor_adyacente = None
    columna_del_valor = None
    
    # Escaneamos hasta 6 columnas a la derecha buscando la fórmula/monto
    for offset in range(1, 7):
        celda_actual = sheet.cell(row=row_idx, column=col_idx + offset)
        if celda_actual.value is not None:
            valor_adyacente = celda_actual.value
            columna_del_valor = celda_actual.coordinate
            break
            
    print(f"[-] Valor extraído en {columna_del_valor}: {valor_adyacente}")
    assert valor_adyacente is not None, f"🚨 [ERROR DE FORMATO] No se pudo encontrar un valor numérico a la derecha de la coordenada {celda_aportacion.coordinate}."

    print("✅ [APROBADO] La corrección estructural de Star Dotal se propagó a Empresarial exitosamente y sin colapso matemático.")