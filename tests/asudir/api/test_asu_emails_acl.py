import os
import pytest
import requests
from dotenv import load_dotenv

load_dotenv()

API_URL = os.getenv("ASU_API_URL")
TOKEN_ADMINISTRACION = os.getenv("ASU_JWT_ADMINISTRACION") # Superadmin, pero NO debe enviar correos
TOKEN_OPERADOR = os.getenv("ASU_JWT_OPERADOR") # El único que debe poder

HEADERS_ADMIN = {"Authorization": f"Bearer {TOKEN_ADMINISTRACION}", "Content-Type": "application/json"}
HEADERS_OPERADOR = {"Authorization": f"Bearer {TOKEN_OPERADOR}", "Content-Type": "application/json"}

# Endpoint inferido por convenciones de Strapi (Ajustar en trinchera si es diferente)
URL_INDIVIDUAL = f"{API_URL}/send-email" 

@pytest.mark.security
def test_asu_email_spoofing_blocked():
    """
    Objetivo: Validar que roles NO autorizados (incluyendo Administración) reciban 403 
    al intentar usar la cuenta oficial de Asudir.
    """
    assert API_URL and TOKEN_ADMINISTRACION
    
    payload = {
        "to": "qa_asudir@techx.com",
        "subject": "Mensaje Falso desde Asudir",
        "text": "Esto es un ataque de Spoofing simulado."
    }

    print("\n[+] Asalto de Correos (Spoofing / A01)...")
    r_admin = requests.post(URL_INDIVIDUAL, json=payload, headers=HEADERS_ADMIN)
    
    assert r_admin.status_code == 403, (
        f"🚨 CRÍTICO A01: El rol Administración logró evadir el bloqueo de correos. "
        f"Status: {r_admin.status_code}. Respuesta: {r_admin.text}"
    )
    print("✅ [APROBADO] Spoofing bloqueado exitosamente para roles ajenos a operación.")

@pytest.mark.business_logic
def test_asu_email_operador_allowed():
    """
    Objetivo: Validar que el Operador conserve el permiso de envío.
    """
    assert API_URL and TOKEN_OPERADOR
    
    payload = {
        "to": "qa_operaciones_asudir@techx.com",
        "subject": "[QA] Prueba de Envío Operador",
        "text": "Validación de regresión exitosa."
    }

    r_operador = requests.post(URL_INDIVIDUAL, json=payload, headers=HEADERS_OPERADOR)
    
    # Toleramos 200 (Enviado) o validación de Strapi si falta algún campo, pero NUNCA 403
    assert r_operador.status_code != 403, "🚨 Regresión: El Operador perdió el permiso de envío de correos."
    print("✅ [APROBADO] Operador retiene permisos de envío.")