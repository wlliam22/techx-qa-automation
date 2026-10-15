import requests
import json
import urllib3
from colorama import init, Fore, Style

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
init(autoreset=True)

# 1. Pivotamos al dominio de Vercel (Proxy Reverso) basándonos en la evidencia de la UI
API_URL = "https://asudir-front-git-staging-tech-x.vercel.app/api/ciclos"

# Token de SUPERADMIN proporcionado
SUPERADMIN_JWT = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6MjIxLCJ0b2tlblZlcnNpb24iOjAsInRva2VuQ2xhc3MiOiJzdGFuZGFyZCIsImlhdCI6MTc5MjAwMDgxMiwiZXhwIjoxNzkyMDQ0MDEyfQ.Z3BxFFGbYcYYwhKCuiHatRbWQOetigYtg4akW8t-xug"
VERCEL_BYPASS = "oL9J8uCUbCOQkpLd85zYXdpe2YvPACSZ" # Reutilizado del entorno Docappoint, ajusta si Asudir usa otro

def test_asu_sec_02_bypass():
    print(Fore.CYAN + "=== [ASU-SEC-02] AUDITORÍA DEVSECOPS: BYPASS DE VALIDACIÓN FRONTEND (OWASP A04) ===")
    print(Fore.YELLOW + f"Disparando payload POST camuflado hacia {API_URL}...")

    # Spoofing de cabeceras para evadir WAF y cruzar Vercel Protection
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {SUPERADMIN_JWT}",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "x-vercel-protection-bypass": VERCEL_BYPASS
    }

    payload = {
        "data": {
            "nombre": "Ciclo Hackeado 9999", 
            "fechaInicio": "2028-10-01",
            "fechaFin": "2029-09-30",
            "estado": "planificado",
            "precio_servicio_riego": 20.00,
            "precio_adicional": 0,
            "precio_excedente": 25.00
        }
    }

    try:
        response = requests.post(API_URL, json=payload, headers=headers, verify=False, timeout=15)
        
        print("\n" + Fore.WHITE + Style.BRIGHT + "--- RESPUESTA DEL SERVIDOR ---")
        print(f"Status Code: {response.status_code}")
        
        try:
            print(json.dumps(response.json(), indent=2))
        except json.JSONDecodeError:
            print(response.text[:500] + "\n... [Cuerpo truncado]")

        print("\n" + Fore.WHITE + Style.BRIGHT + "--- VEREDICTO DEVSECOPS ---")
        
        if response.status_code in [200, 201]:
            print(Fore.RED + Style.BRIGHT + "🚨 [FAIL] VULNERABILIDAD A04 CONFIRMADA: AUSENCIA DE VALIDACIÓN EN BACKEND.")
            print(Fore.RED + "Strapi permitió crear un ciclo con un nombre inválido. El schema.json carece de Regex.")
        elif response.status_code in [400, 422]:
            print(Fore.GREEN + Style.BRIGHT + "✅ [PASS] ARQUITECTURA ZERO TRUST CONFIRMADA.")
            print(Fore.GREEN + "Strapi rechazó el payload por formato inválido en el schema.")
        elif response.status_code in [401, 403]:
            print(Fore.YELLOW + "⚠️ [ERROR DE AUTH] El token de Superadmin caducó o Vercel bloqueó la petición.")
        elif response.status_code == 404:
            print(Fore.YELLOW + "⚠️ [NOT FOUND] La ruta de Vercel no admite POST o no está configurada como proxy para mutaciones.")

    except Exception as e:
        print(Fore.RED + f"Error persistente: {e}")

if __name__ == "__main__":
    test_asu_sec_02_bypass()