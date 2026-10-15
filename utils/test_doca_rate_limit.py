import os
import requests
import time
from concurrent.futures import ThreadPoolExecutor
from collections import Counter
from colorama import init, Fore, Style

init(autoreset=True)

# Configuración del Entorno
API_URL = "https://test-docappoint.techxmx.com/getPreregistros"
# Reemplazar por un UUID válido si es necesario, aunque para el Rate Limit un ID genérico sirve.
PARAMS = {"citaId": "f325ca2a-d358-4d18-9bd2-79cbf0280084"} 
TOTAL_REQUESTS = 130
MAX_WORKERS = 20 # Ráfaga concurrente para forzar Deadlocks

headers = {
    "Accept": "application/json",
    # Inyectar Vercel Bypass si el endpoint pasa por la capa de protección de Staging
    # "x-vercel-protection-bypass": os.getenv("VERCEL_DOCAPPOINT_BYPASS_SECRET", "")
}

def fetch_endpoint(req_id):
    try:
        response = requests.get(API_URL, params=PARAMS, headers=headers, timeout=10)
        return req_id, response.status_code, response.json() if response.status_code == 429 else None
    except Exception as e:
        return req_id, 000, str(e)

def auditar_rate_limit():
    print(Fore.CYAN + f"=== [DOCA-PROT-064] STRESS TEST: RATE LIMITER (OWASP A04) ===")
    print(Fore.YELLOW + f"Disparando {TOTAL_REQUESTS} peticiones concurrentes a {API_URL}...\n")

    results = []
    status_codes = Counter()

    start_time = time.time()
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(fetch_endpoint, i) for i in range(1, TOTAL_REQUESTS + 1)]
        for future in futures:
            req_id, status, data = future.result()
            results.append((req_id, status, data))
            status_codes[status] += 1

    elapsed = time.time() - start_time

    print(Fore.WHITE + Style.BRIGHT + "--- RESULTADOS DE LA RÁFAGA ---")
    print(f"Tiempo total: {elapsed:.2f} segundos")
    for code, count in status_codes.items():
        color = Fore.GREEN if code in [200, 429] else Fore.RED
        print(color + f"HTTP {code}: {count} peticiones")

    print("\n" + Fore.WHITE + Style.BRIGHT + "--- ANÁLISIS DE FALLOS (HTTP 500) ---")
    if status_codes[500] > 0:
        print(Fore.RED + Style.BRIGHT + f"🚨 [FAIL] VULNERABILIDAD A04 ACTIVA. Juan no solucionó el Auto-DoS.")
        print(Fore.RED + f"Se detectaron {status_codes[500]} errores HTTP 500. La base de datos o el hilo de Node.js sigue colapsando bajo concurrencia.")
        return # Abortar, el bug sigue vivo
    else:
        print(Fore.GREEN + "✅ Cero errores HTTP 500 detectados en la ráfaga.")

    print("\n" + Fore.WHITE + Style.BRIGHT + "--- ANÁLISIS DEL RETRY-AFTER DINÁMICO ---")
    # Extraer las peticiones 429 para evaluar el delta matemático
    rate_limited_reqs = [data for _, status, data in results if status == 429 and data]
    
    if rate_limited_reqs:
        print(Fore.YELLOW + "Petición 429 de prueba aislada...")
        time.sleep(3) # Pausa de 3 segundos
        _, status_test, data_test = fetch_endpoint(999)
        
        if status_test == 429 and data_test and 'retryAfter' in data_test:
            initial_retry = rate_limited_reqs[0].get('retryAfter')
            new_retry = data_test.get('retryAfter')
            
            print(f"RetryAfter Inicial: {initial_retry}s")
            print(f"RetryAfter tras 3s: {new_retry}s")
            
            if initial_retry == new_retry == 900:
                print(Fore.RED + Style.BRIGHT + "🚨 [FAIL] El retryAfter sigue siendo un 'hardcode' estático de 900s.")
            elif new_retry < initial_retry:
                print(Fore.GREEN + Style.BRIGHT + "✅ [PASS] El retryAfter es dinámico y calcula el remanente real.")
            else:
                print(Fore.YELLOW + "⚠️ Comportamiento anómalo en el cálculo de tiempo.")
        else:
             print(Fore.RED + "No se pudo extraer el JSON o el retryAfter del nuevo intento.")

if __name__ == "__main__":
    auditar_rate_limit()