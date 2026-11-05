import os
import pytest
import requests
from dotenv import load_dotenv

load_dotenv()

# ==============================================================================
# CONFIGURACIÓN DEL ENTORNO Y SECRETS (Zero Trust)
# ==============================================================================
API_URL = os.getenv("ASU_API_URL") # Asegúrate de que esta exista
TOKEN_USUARIO_AGUA = os.getenv("STAGING_JWT_AGUA_TOKEN") 
TOKEN_CAPTURADOR = os.getenv("STAGING_JWT_CAPTURADOR")
ID_TICKET_AJENO = os.getenv("ASU_ID_TICKET_POZO_205") # Necesitas agregar esta
ID_TICKET_PROPIO = os.getenv("ASU_ID_TICKET_POZO_101") # Necesitas agregar esta

HEADERS_AGUA = {"Authorization": f"Bearer {TOKEN_USUARIO_AGUA}", "Content-Type": "application/json"}
HEADERS_CAPTURADOR = {"Authorization": f"Bearer {TOKEN_CAPTURADOR}", "Content-Type": "application/json"}

@pytest.mark.security
def test_asu_tickets_usuario_agua_forbidden():
    """
    Objetivo: Validar que el Usuario de Agua recibe 403 en todas las operaciones de Tickets.
    Vulnerabilidad objetivo: OWASP A01 (Broken Access Control).
    """
    assert API_URL and TOKEN_USUARIO_AGUA and ID_TICKET_AJENO and ID_TICKET_PROPIO
    url_base = f"{API_URL}/tickets"

    print("\n[+] Asalto de Permisos (Usuario de Agua) en Tickets...")

    # 1. GET (Listar)
    r_list = requests.get(url_base, headers=HEADERS_AGUA)
    assert r_list.status_code == 403, f"🚨 Falla BOLA: Usuario de Agua puede listar tickets. HTTP {r_list.status_code}"

    # 2. GET (Ver Ajeno y Propio)
    r_ver_ajeno = requests.get(f"{url_base}/{ID_TICKET_AJENO}", headers=HEADERS_AGUA)
    assert r_ver_ajeno.status_code == 403, f"🚨 Falla BOLA: Usuario de Agua puede ver ticket ajeno. HTTP {r_ver_ajeno.status_code}"
    
    r_ver_propio = requests.get(f"{url_base}/{ID_TICKET_PROPIO}", headers=HEADERS_AGUA)
    assert r_ver_propio.status_code == 403, f"🚨 Regla de Negocio Rota: Usuario de Agua no debe ver ni su propio ticket por API. HTTP {r_ver_propio.status_code}"

    # 3. POST (Crear)
    payload_crear = {"numero": "PRUEBA-UA-001", "pozoId": 101, "fecha": "2026-11-03"}
    r_crear = requests.post(url_base, json=payload_crear, headers=HEADERS_AGUA)
    assert r_crear.status_code == 403, f"🚨 Falla BOLA: Usuario de Agua puede crear tickets. HTTP {r_crear.status_code}"

    # 4. PUT (Cambiar Estado)
    payload_cambiar = {"estado": "procesado"}
    r_cambiar = requests.put(f"{url_base}/{ID_TICKET_AJENO}", json=payload_cambiar, headers=HEADERS_AGUA)
    assert r_cambiar.status_code == 403, f"🚨 CRÍTICO A08: Usuario de Agua puede manipular estado de ticket ajeno. HTTP {r_cambiar.status_code}"

    # 5. DELETE (Borrar)
    r_borrar = requests.delete(f"{url_base}/{ID_TICKET_AJENO}", headers=HEADERS_AGUA)
    assert r_borrar.status_code == 403, f"🚨 CRÍTICO A01: Usuario de Agua puede borrar tickets ajenos. HTTP {r_borrar.status_code}"

    print("✅ [APROBADO] El Usuario de Agua está completamente bloqueado (403).")

@pytest.mark.business_logic
def test_asu_tickets_capturador_allowed():
    """
    Objetivo: Validar que los roles internos (ej. Capturador) NO fueron bloqueados (Regresión).
    """
    assert API_URL and TOKEN_CAPTURADOR
    url_base = f"{API_URL}/tickets"

    print("\n[+] Validando Regresión: Rol Interno (Capturador)...")
    r_list = requests.get(url_base, headers=HEADERS_CAPTURADOR)
    
    assert r_list.status_code == 200, f"🚨 Regresión: Capturador perdió acceso a la lista de tickets. HTTP {r_list.status_code}"
    print("✅ [APROBADO] Rol interno conserva acceso.")