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

# Rutas locales (Criterio: Cliente 35 años, Imagina Ser 10 Pagos)
PATH_PDF_IMAS = "tests/impulsa/adjuntos/Imagina Ser 10 pagos/Cotización Imagina Ser 10 Pagos.pdf"
PATH_PDF_PENS = "tests/impulsa/adjuntos/Imagina Ser 10 pagos/Pensiones Imagina Ser 10 Pagos.pdf"

# 🛡️ Cabeceras Clonadas Exactas (Sin Bearer, con Anti-WAF User-Agent)
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
@pytest.mark.security
def test_imp_672_regla3y4_nota_umas_inmutable_y_correcta():
    """
    Objetivo: (Criterios 8 y 9) Validar que el archivo Excel generado para 
    Retiro -> Imagina Ser -> 10 Pagos contenga la nota fiscal de 5 UMAS con el 
    año correcto (2026), monto exacto ($213,973.20), y que sea Texto estático (no fórmula).
    """
    assert API_URL and TOKEN_AGENTE, "Faltan variables de entorno esenciales (IMP_API_URL, IMP_JWT_TOKEN_AGENTE)."
    assert os.path.exists(PATH_PDF_IMAS), f"CRÍTICO: No se encontró el PDF Imagina Ser en: {PATH_PDF_IMAS}"
    assert os.path.exists(PATH_PDF_PENS), f"CRÍTICO: No se encontró el PDF Pensiones en: {PATH_PDF_PENS}"
    
    url_upload = f"{API_URL}/chasis/3/IS10/dual"
    
    print(f"\n[+] 1. Disparando Petición Multipart (Dual PDF) al backend: {url_upload}...")
    
    # Inyectamos el payload exacto (file y file2)
    with open(PATH_PDF_IMAS, "rb") as pdf_imas, open(PATH_PDF_PENS, "rb") as pdf_pens:
        files = {
            "file": ("Cotización Imagina Ser 10 Pagos.pdf", pdf_imas, "application/pdf"),
            "file2": ("Pensiones Imagina Ser 10 Pagos.pdf", pdf_pens, "application/pdf")
        }
        
        # Agregamos timeout explícito para que no se quede colgado si el WAF vuelve a bloquear
        response = requests.post(url_upload, headers=HEADERS, files=files, timeout=30)
        
    assert response.status_code in [200, 201], f"Fallo en Upload Dual. Código HTTP: {response.status_code}. Respuesta: {response.text}"
    
    print("[+] 2. Interceptando Binario (XLSX) de respuesta en memoria RAM...")
    workbook = openpyxl.load_workbook(BytesIO(response.content), data_only=False)
    sheet = workbook.active

    print("[+] 3. Auditando Reglas 3, 4 y 5 (Zero Trust: Localización Dinámica de UMAS e Inmutabilidad)...")
    
    nota_umas_encontrada = False
    celda_objetivo = None
    texto_esperado = "El Monto Máximo para No Acumular Ingresos en 2026 Anual con tope de 5 UMAS = $213,973.20"
    texto_198 = "$198,031.80"
    
    for row in sheet.iter_rows(min_row=1, max_row=150, min_col=1, max_col=10):
        for cell in row:
            if cell.value and isinstance(cell.value, str):
                # Validación cruzada: Nos aseguramos de que no exista el valor viejo hardcodeado
                assert texto_198 not in cell.value, f"🚨 [ERROR DE NEGOCIO] Se encontró el monto viejo/estático {texto_198} en la celda {cell.coordinate}. El backend no actualizó la UMA."
                
                if "5 UMAS =" in cell.value and "Monto Máximo para No Acumular" in cell.value:
                    nota_umas_encontrada = True
                    celda_objetivo = cell
                    
    assert nota_umas_encontrada, "🚨 [ERROR DE NEGOCIO] No se encontró la nota de 'No Acumular Ingresos... 5 UMAS =' en el chasis generado."
    
    print(f"[-] Nota UMAS localizada en celda: {celda_objetivo.coordinate}")
    print(f"[-] Valor crudo de la celda: '{celda_objetivo.value}'")
    
    # Validamos Criterio 8: Texto Exacto (Regla 3)
    assert texto_esperado in celda_objetivo.value, (
        f"🚨 [REGRESIÓN] El texto de la nota UMAS no coincide.\n"
        f"Esperado (fragmento): {texto_esperado}\n"
        f"Actual: {celda_objetivo.value}"
    )
    
    # Validamos Criterio 9: Inmutabilidad (No es fórmula) (Regla 5)
    assert not str(celda_objetivo.value).startswith("="), (
        f"🚨 [CRÍTICO DE DATOS] La celda de UMAS ({celda_objetivo.coordinate}) es una fórmula: '{celda_objetivo.value}'. "
        "Debe ser texto estático ('String') para preservar el valor de la UMA histórica al abrir el Excel en el futuro."
    )
    
    print("✅ [APROBADO] El Excel inyecta las UMAS dinámicas de México como Texto Inmutable sin dejar rastros de montos obsoletos.")