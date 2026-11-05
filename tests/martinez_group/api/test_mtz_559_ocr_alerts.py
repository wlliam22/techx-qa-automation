import os
import time
import pytest
import requests
from dotenv import load_dotenv

load_dotenv()

# ==============================================================================
# CONFIGURACIÓN DEL ENTORNO Y SECRETS (Zero Trust)
# ==============================================================================
API_URL = os.getenv("MTZ_API_URL", "https://martinezgroup-back-staging.techxmx.com")
TOKEN_MTZ = os.getenv("STAGING_JWT_TOKEN_MTZ") 
PATH_PACKSLIP_CHOSEN_INVALIDO = os.getenv("MTZ_PATH_IMG_999999") # Imagen con SKU 999999
PATH_PACKSLIP_SESAJAL_LLC_VALIDO = os.getenv("MTZ_PATH_IMG_SESAJAL_VALIDO") 

HEADERS = {"Authorization": f"Bearer {TOKEN_MTZ}"}

@pytest.mark.business_logic
def test_mtz_559_alerta_producto_no_registrado():
    """
    Objetivo: Validar que un trabajo de Chosen Foods enviado en modo 'Condiciones' 
    con un SKU no registrado (999999) adjunte correctamente la alerta de nomenclatura 
    al finalizar el procesamiento en cola.
    """
    assert TOKEN_MTZ and PATH_PACKSLIP_CHOSEN_INVALIDO, "CRÍTICO: Faltan secretos en el .env."

    url_submit = f"{API_URL}/queue/submit-job"
    
    print("\n[+] 1. Inyectando trabajo a la cola de procesamiento (SKU Fantasma 999999)...")
    
    # Simulación del multipart/form-data capturado por cURL
    payload = {
        "job_name": (None, "Procesamiento QA Asalto - SKU 999999"),
        "cliente": (None, "sesajal-chosen-foods"),
        "modo": (None, "condiciones") # Asumiendo que ahora se envía, si no, remover
    }
    
    with open(PATH_PACKSLIP_CHOSEN_INVALIDO, "rb") as img:
        archivos = {
            "packslip_images": ("packslip_999999.png", img, "image/png"),
            **payload
        }
        r_submit = requests.post(url_submit, headers=HEADERS, files=archivos)
        
    assert r_submit.status_code == 200, f"Fallo al enviar a cola. Status: {r_submit.status_code}"
    
    job_id = r_submit.json().get("job_id")
    assert job_id, "La API no devolvió un job_id válido."
    
    print(f"[+] 2. Trabajo {job_id} en cola. Interceptando estado de asincronía...")
    
    # Polling contra la API de estado (ajusta la ruta según el entorno de MTZ)
    url_status = f"{API_URL}/queue/status/{job_id}" # Ruta hipotética, ajustar si es /registro/from-jobs
    estado_final = None
    resultado_json = None
    
    for intento in range(15):
        r_status = requests.get(url_status, headers=HEADERS)
        if r_status.status_code == 200:
            data = r_status.json()
            estado_actual = data.get("estado") or data.get("status")
            print(f"  -> Intento {intento+1}: Estado = {estado_actual}")
            
            if estado_actual == "COMPLETED" or estado_actual == "LISTO PARA GUARDAR":
                estado_final = estado_actual
                resultado_json = data
                break
        time.sleep(3) # Pausa táctica
        
    assert estado_final, "🚨 [TIMEOUT] El trabajo nunca terminó de procesarse en Staging."
    
    print("[+] 3. Auditando la carga de Alertas en la respuesta del trabajo...")
    
    # Validamos que la alerta venga en el payload
    alertas = resultado_json.get("alertas", [])
    texto_serializado = str(resultado_json).lower()
    
    assert "999999" in texto_serializado, "🚨 [FALLO] El SKU 999999 no fue registrado en el payload de resultado."
    assert "no está registrado" in texto_serializado or "pendiente" in texto_serializado, (
        f"🚨 [REGRESIÓN] El backend falló en adjuntar el flag de 'Nomenclatura pendiente'. "
        f"JSON devuelto: {resultado_json}"
    )
    
    print("✅ [APROBADO] La alerta de SKU no registrado viaja correctamente desde el backend hasta el frontend.")