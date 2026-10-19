import requests
import urllib3
from colorama import init, Fore, Style

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
init(autoreset=True)

API_URL = "https://test-docappoint.techxmx.com/getPreregistros"
PARAMS = {"citaId": "f325ca2a-d358-4d18-9bd2-79cbf0280084"}

def auditar_ip_spoofing():
    print(Fore.CYAN + "=== [DOCA-SEC-04] AUDITORÍA DEVSECOPS: IP SPOOFING (OWASP A05) ===")
    print(Fore.YELLOW + "Tu IP real está bloqueada. Inyectando IP falsa (203.0.113.99) en cabeceras X-Forwarded-For...")

    # Payload de Evasión: Simulamos ser otro cliente detrás de un proxy
    spoofed_headers = {
        "Accept": "application/json",
        "X-Forwarded-For": "203.0.113.99",
        "X-Real-IP": "203.0.113.99"
    }

    try:
        response = requests.get(API_URL, params=PARAMS, headers=spoofed_headers, verify=False, timeout=10)
        
        print("\n" + Fore.WHITE + Style.BRIGHT + "--- RESPUESTA DEL SERVIDOR ---")
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print(Fore.RED + Style.BRIGHT + "🚨 [FAIL] VULNERABILIDAD CRÍTICA (OWASP A05).")
            print(Fore.RED + "El backend confió en la cabecera X-Forwarded-For inyectada por el cliente.")
            print(Fore.RED + "El atacante acaba de saltarse el Rate Limit. Rechazo Inmediato a Juan.")
        elif response.status_code == 429:
            print(Fore.GREEN + Style.BRIGHT + "✅ [PASS] INFRAESTRUCTURA BLINDADA.")
            print(Fore.GREEN + "Vercel o Express ignoraron la IP falsa y mantuvieron el bloqueo basado en tu IP TCP real.")
        else:
            print(Fore.YELLOW + f"⚠️ Código inesperado: {response.status_code}")

    except Exception as e:
        print(Fore.RED + f"Error de conexión: {e}")

if __name__ == "__main__":
    auditar_ip_spoofing()