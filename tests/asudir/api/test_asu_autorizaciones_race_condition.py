import os
import json
import pytest
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

# ==============================================================================
# CONFIGURACIÓN DEL ENTORNO Y SECRETS (Zero Trust)
# ==============================================================================
TOKEN = os.getenv("STAGING_JWT_TOKEN")
VERCEL_BYPASS = os.getenv("VERCEL_ASUDIR_BYPASS_SECRET")

API_URL = "https://back-staging.asudir051.com/api/autorizaciones-de-riego"

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json",
    "x-vercel-protection-bypass": VERCEL_BYPASS
}

# Payload base inyectado por QA
PAYLOAD = {
    "data": {
        "fecha": "2026-10-21",
        "pozo": None,
        "bateria": None,
        "ciclo_agricola": "s4h2vobk1iukm91azkf968nr",
        "subciclo": "OTOÑO-INVIERNO",
        "cultivos": "[{\"NombreCultivo\":\"SANDIA\",\"selectedCultivoId\":\"bf98pvbpyj3fo62ukmbxz9mm\",\"superficie\":\"1\",\"lamina\":\"40\",\"tipoCultivo\":\"anuales\",\"tipoRiego\":\"goteo\"}]",
        "volumen_demanda": 4000,
        "pozos_asignados": "[{\"pozoId\":438,\"documentId\":\"ni0260n805ey0to9ur4gxox0\",\"numeropozo\":\"4514\",\"volumen\":731660,\"vol_adicional\":0,\"vol_cedido\":0,\"vol_transmitido_en_proceso\":0,\"extraccion\":0,\"vol_comprometido\":0,\"disponible_neto\":731660,\"orden\":1,\"volumen_asignado\":4000},{\"pozoId\":437,\"documentId\":\"gnts32zbutxqj89blw91ngcb\",\"numeropozo\":\"4405\",\"volumen\":665000,\"vol_adicional\":0,\"vol_cedido\":0,\"vol_transmitido_en_proceso\":0,\"extraccion\":0,\"vol_comprometido\":0,\"disponible_neto\":665000,\"orden\":2,\"volumen_asignado\":0},{\"pozoId\":439,\"documentId\":\"xcxf2ud7q583azr6gtwlu8yd\",\"numeropozo\":\"4526\",\"volumen\":665000,\"vol_adicional\":0,\"vol_cedido\":0,\"vol_transmitido_en_proceso\":0,\"extraccion\":0,\"vol_comprometido\":0,\"disponible_neto\":665000,\"orden\":3,\"volumen_asignado\":0}]",
        "autorizar_a": "GRUPO AGROPECUARIO EL DIAMANTE S.A. DE C.V.",
        "nombre_predio": "SANTA PATRICIA",
        "localizacion": "BLVD. GARCÍA MORALES #54 COL. LA MANGA",
        "representante": "ixo1t4hvfqe7w3k1r6npwt9e",
        "vigente": True,
        "encargado_nombre": "ING. DAMIÁN LÓPEZ DÓRAME"
    }
}

def send_post_request():
    """Ejecuta un request POST individual y retorna la respuesta."""
    try:
        response = requests.post(API_URL, headers=HEADERS, json=PAYLOAD, timeout=10)
        return response
    except Exception as e:
        return str(e)

@pytest.mark.smoke
def test_asu_sec_01_race_condition_folios():
    """
    Objetivo: Validar que el backend maneje concurrencia sin duplicar folios.
    Vulnerabilidad objetivo: OWASP A04 (Race Condition).
    """
    assert TOKEN, "CRÍTICO: STAGING_JWT_TOKEN no configurado en el .env"

    num_concurrent_requests = 5
    responses = []

    # 1. Ejecución concurrente (Ataque)
    print(f"\n[+] Disparando {num_concurrent_requests} peticiones POST concurrentes hacia {API_URL}...")
    with ThreadPoolExecutor(max_workers=num_concurrent_requests) as executor:
        futures = [executor.submit(send_post_request) for _ in range(num_concurrent_requests)]
        for future in as_completed(futures):
            responses.append(future.result())

    # 2. Análisis de respuestas y recolección de Folios
    successful_folios = []
    
    for idx, response in enumerate(responses):
        if isinstance(response, str):
            pytest.fail(f"Falla de red en el hilo {idx}: {response}")
            
        print(f"Respuesta {idx + 1}: HTTP {response.status_code}")

        if response.status_code in [200, 201]:
            data = response.json()
            try:
                if "attributes" in data.get("data", {}):
                    folio = data["data"]["attributes"].get("folio")
                else:
                    folio = data.get("data", {}).get("folio") or data.get("folio")
                    
                assert folio is not None, "El backend devolvió 200 OK pero no retornó el folio en el response."
                successful_folios.append(folio)
            except Exception as e:
                pytest.fail(f"Error al parsear el JSON de respuesta para buscar el folio: {e}")
                
        elif response.status_code in [400, 409, 422, 500]:
            print(f"[-] Petición rechazada o fallida (Comportamiento aceptable si previene duplicidad): {response.text}")

    # ==============================================================================
    # 3. Aserción Zero Trust: Unicidad Matemática
    # ==============================================================================
    print(f"\n[+] Folios exitosos generados en la ráfaga: {successful_folios}")
    
    assert len(successful_folios) > 0, (
        f"🚨 [FALLO CRÍTICO] El servidor no asignó NINGÚN folio exitosamente. "
        f"Respuestas HTTP: {[r.status_code if not isinstance(r, str) else r for r in responses]}"
    )
    
    unique_folios = set(successful_folios)
    duplicados = len(successful_folios) - len(unique_folios)
    
    assert len(successful_folios) == len(unique_folios), (
        f"🚨 [OWASP A04 FALLIDO] ¡Race Condition Crítica Detectada!\n"
        f"Se generaron {duplicados} folio(s) duplicado(s).\n"
        f"Folios devueltos: {successful_folios}\n"
        f"El backend de Juan NO tiene un 'Unique Constraint' por ciclo ni bloqueos transaccionales."
    )
    
    print("✅ [APROBADO] La base de datos y el controlador resistieron la concurrencia. No hay folios duplicados.")