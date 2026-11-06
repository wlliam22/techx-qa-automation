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

# Ruta local del PDF Orvi 99 10 Pagos (Cliente 35 años)
PATH_PDF_ORVI = "tests/impulsa/adjuntos/ahorro orvi 99 10 pagos/1.- Ahorro Orvi 99 10 pagos-2.pdf"

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
def test_imp_672_regla1_cierre_tabla_orvi99_ahorro():
    """
    Objetivo: (Criterio 1) Validar que el archivo Excel generado para 
    Ahorro -> Orvi 99 -> 10 Pagos cierre su tabla en la última fila (41) 
    con una línea inferior y no deje rastros en filas vacías.
    """
    assert API_URL and TOKEN_AGENTE, "Faltan variables de entorno esenciales (IMP_API_URL, IMP_JWT_TOKEN_AGENTE)."
    assert os.path.exists(PATH_PDF_ORVI), f"CRÍTICO: No se encontró el PDF Orvi 99 en: {PATH_PDF_ORVI}"
    
    url_upload = f"{API_URL}/chasis/2/O10"
    
    print(f"\n[+] 1. Disparando Petición Multipart al backend: {url_upload}...")
    
    with open(PATH_PDF_ORVI, "rb") as pdf_file:
        files = {
            "file": ("1.- Ahorro Orvi 99 10 pagos-2.pdf", pdf_file, "application/pdf")
        }
        
        response = requests.post(url_upload, headers=HEADERS, files=files, timeout=30)
        
    assert response.status_code in [200, 201], f"Fallo en Upload. Código HTTP: {response.status_code}. Respuesta: {response.text}"
    
    print("[+] 2. Interceptando Binario (XLSX) de respuesta en memoria RAM...")
    workbook = openpyxl.load_workbook(BytesIO(response.content), data_only=False)
    sheet = workbook.active

    print("[+] 3. Auditando Regla 1 (Cierre de Tabla en Fila 41)...")
    
    # El Criterio 1 dicta que para el cliente de 35 años la fila de cierre es la 41.
    fila_objetivo = 41
    
    celdas_evaluadas = 0
    celdas_con_borde_inferior = 0
    
    # Inspeccionamos las columnas de la A a la M (1 a 13) en la fila 41
    for col in range(1, 14): 
        cell = sheet.cell(row=fila_objetivo, column=col)
        
        # Validamos si la celda tiene asignado un estilo de borde inferior (thin, medium, etc.)
        if cell.border and cell.border.bottom and cell.border.bottom.style:
            celdas_con_borde_inferior += 1
            
        if cell.value is not None:
            celdas_evaluadas += 1

    print(f"[-] Celdas con datos en fila 41: {celdas_evaluadas}")
    print(f"[-] Celdas con borde inferior detectado: {celdas_con_borde_inferior}")

    # Aserción principal: La tabla debe estar cerrada
    assert celdas_con_borde_inferior > 0, (
        f"🚨 [REGRESIÓN UI] No se encontró ninguna línea inferior (borde) en la fila {fila_objetivo}. "
        "La tabla quedó abierta (defecto original no corregido)."
    )
    
    print("[+] 4. Verificando que no haya filas 'fantasma' (Líneas de cierre en fila 42)...")
    borde_basura = False
    for col in range(1, 14):
        cell_42 = sheet.cell(row=fila_objetivo+1, column=col)
        if cell_42.border and cell_42.border.bottom and cell_42.border.bottom.style:
            borde_basura = True
            break
            
    assert not borde_basura, (
        f"🚨 [ERROR DE FORMATO] Se encontró un borde de cierre remanente en una fila vacía "
        f"(Fila {fila_objetivo+1}). El recorte de Pandas/Openpyxl dejó basura visual."
    )
    
    print(f"✅ [APROBADO] La tabla de Orvi 99 Ahorro cierra correctamente de forma limpia en la fila {fila_objetivo}.")