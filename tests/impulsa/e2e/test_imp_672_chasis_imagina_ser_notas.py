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

# Matriz de Pruebas Parametrizada para Imagina Ser (Criterio 10 / Regla 3)
# [Plazo ID / Endpoint Suffix, Ruta Carpeta Adjuntos, Nombre Archivo Cotización, Nombre Archivo Pensiones]
CASOS_ESTUDIO_IMAGINA = [
    (
        "IS10", 
        "tests/impulsa/adjuntos/Imagina Ser 10 pagos", 
        "Cotización Imagina Ser 10 Pagos.pdf", 
        "Pensiones Imagina Ser 10 Pagos.pdf"
    ),
    (
        "IS15", 
        "tests/impulsa/adjuntos/Imagina Ser 15 pagos", 
        "Cotización Imagina Ser 15 Pagos.pdf", 
        "Pensiones Imagina Ser 15 pagos.pdf"
    ),
    (
        "ISTP", 
        "tests/impulsa/adjuntos/Imagina Ser Todos Los Pagos", 
        "Cotización Imagina Ser Todos Los Pagos.pdf", 
        "Pensiones Imagina Ser Todos Los Pagos.pdf"
    )
]

@pytest.mark.business_logic
@pytest.mark.parametrize("plazo_id, folder_path, pdf_cot, pdf_pens", CASOS_ESTUDIO_IMAGINA)
def test_imp_672_criterio10_legibilidad_notas_imagina_ser(plazo_id, folder_path, pdf_cot, pdf_pens):
    """
    Objetivo: (Criterio 10 / Regla 3) Validar que en Retiro -> Imagina Ser 
    (10, 15 y Todos los pagos - ISTP), la última nota regulatoria inyecte 
    el texto completo, inmutable y correcto con el monto de UMAS de 2026.
    """
    assert API_URL and TOKEN_AGENTE, "Faltan variables de entorno esenciales (IMP_API_URL, IMP_JWT_TOKEN_AGENTE)."
    
    path_cot = os.path.join(folder_path, pdf_cot)
    path_pens = os.path.join(folder_path, pdf_pens)
    
    assert os.path.exists(path_cot), f"CRÍTICO [{plazo_id}]: No se encontró el PDF de cotización en: {path_cot}"
    assert os.path.exists(path_pens), f"CRÍTICO [{plazo_id}]: No se encontró el PDF de pensiones en: {path_pens}"
    
    # Endpoint backend corregido con ISTP para todos los pagos
    url_upload = f"{API_URL}/chasis/3/{plazo_id}/dual"
    
    print(f"\n[+] 1. [{plazo_id}] Disparando Petición Multipart (Dual) al backend: {url_upload}...")
    
    with open(path_cot, "rb") as f_cot, open(path_pens, "rb") as f_pens:
        files = {
            "file": (pdf_cot, f_cot, "application/pdf"),
            "file2": (pdf_pens, f_pens, "application/pdf")
        }
        response = requests.post(url_upload, headers=HEADERS, files=files, timeout=45)
        
    assert response.status_code in [200, 201], f"Fallo en Upload [{plazo_id}]. HTTP: {response.status_code}. Respuesta: {response.text}"
    
    print(f"[+] 2. [{plazo_id}] Interceptando Binario (XLSX) de respuesta en memoria RAM...")
    workbook = openpyxl.load_workbook(BytesIO(response.content), data_only=False)
    sheet = workbook.active
    
    print(f"[+] 3. [{plazo_id}] Auditando legibilidad y contenido de la nota UMA...")
    
    nota_encontrada = False
    coordenada_nota = None
    texto_nota = ""
    
    # Escaneo amplio en la sección inferior de notas (Filas 70 a 110, Columnas A a E)
    for row in sheet.iter_rows(min_row=70, max_row=110, min_col=1, max_col=5):
        for cell in row:
            if isinstance(cell.value, str) and "Monto Máximo" in cell.value:
                nota_encontrada = True
                coordenada_nota = cell.coordinate
                texto_nota = cell.value.strip()
                break
        if nota_encontrada:
            break
            
    assert nota_encontrada, f"🚨 [{plazo_id}] No se encontró la nota de UMAS ('Monto Máximo') en la sección inferior del Excel."
    
    print(f"[-] [{plazo_id}] Nota localizada en celda: {coordenada_nota}")
    print(f"[-] [{plazo_id}] Contenido crudo: {texto_nota}")
    
    # Texto oficial inyectado por el backend para deducción del 10% con tope de 5 UMAS (2026)
    texto_esperado = "* El Monto Máximo a Deducir es 10% de Ingreso Anual con tope de 5 UMAS = $213,973.20."
    
    # Validaciones de Integridad y Legibilidad
    assert texto_nota == texto_esperado, (
        f"🚨 [{plazo_id}] Discrepancia en la nota de UMAS.\n"
        f"Esperado: {texto_esperado}\n"
        f"Obtenido: {texto_nota}"
    )
    
    # Validación de punto final (Legibilidad y completitud)
    assert texto_nota.endswith("."), f"🚨 [{plazo_id}] La nota está incompleta o truncada (no termina con punto final): {texto_nota}"
    
    print(f"✅ [{plazo_id}] APROBADO: La nota de Imagina Ser se lee completa, con formato inmutable y puntuación correcta.")