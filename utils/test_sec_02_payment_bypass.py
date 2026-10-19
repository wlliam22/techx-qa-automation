import os
import json
import requests
from colorama import init, Fore, Style

init(autoreset=True)

# 1. Configuración del Entorno
API_URL = "https://test-docappoint.techxmx.com/nuevoTurnoCheckOut"
AUTH_FILE = "auth_patient.json"

def ejecutar_auditoria():
    print(Fore.CYAN + "=== [DOCA-SEC-01] AUDITORÍA DEVSECOPS: BYPASS DE PASARELA ===")
    
    # 2. Extracción Shift-Left del JWT
    if not os.path.exists(AUTH_FILE):
        print(Fore.RED + f"❌ Archivo {AUTH_FILE} no encontrado. Ejecuta seed_auth.py primero.")
        return

    with open(AUTH_FILE, "r", encoding="utf-8") as f:
        auth_data = json.load(f)
        
    token = None
    # Buscar el token en el localStorage guardado por Playwright
    origins = auth_data.get("origins", [])
    if origins:
        for item in origins[0].get("localStorage", []):
            if item["name"] in ["token", "jwt"]:
                token = item["value"]
                break

    if not token:
        print(Fore.RED + "❌ No se encontró un token JWT válido en el estado de sesión.")
        return

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }

    # 3. Construcción del Payload Malicioso (Zero Trust Test)
    # Basado en la evidencia forense: Médico d2153d92... exige pago (servicePrice: 1000)
    payload = {
        "doctorId": "d2153d92-b6aa-432f-b326-f0d6feaa9bea",
        "patientId": "29d353a0-012a-4c68-bf29-93f05546703b",
        "serviceId": None,
        "fecha": "2026-10-30", # Fecha futura para evitar colisiones
        "horaInicio": "14:00", # Slot arbitrario
        "advancePaymentId": None # Inyección de bypass: Omitimos el token de Stripe
    }

    print(Fore.YELLOW + f"🚀 Disparando payload POST contra {API_URL}")
    print(Fore.YELLOW + f"   Target Doctor: {payload['doctorId']}")
    print(Fore.YELLOW + f"   Vulnerabilidad a probar: Inyección de advancePaymentId = Null en médico de pago.")

    # 4. Ejecución de la Petición
    response = requests.post(API_URL, json=payload, headers=headers)

    print("\n" + Fore.WHITE + Style.BRIGHT + "--- RESPUESTA DEL SERVIDOR (EXPRESS) ---")
    print(f"Status Code: {response.status_code}")
    
    try:
        print(json.dumps(response.json(), indent=2))
    except json.JSONDecodeError:
        print(response.text)

    print("\n" + Fore.WHITE + Style.BRIGHT + "--- VEREDICTO DEVSECOPS ---")
    
    # 5. Evaluación de Criterios de Aceptación (OWASP A04)
    if response.status_code in [200, 201]:
        print(Fore.RED + Style.BRIGHT + "🚨 [FAIL] VULNERABILIDAD CRÍTICA CONFIRMADA (OWASP A04).")
        print(Fore.RED + "El backend agendó la cita sin requerir el ID de pago de Stripe para un médico que exige anticipo.")
        print(Fore.RED + "Acción: Levantar ticket de rechazo (Plantilla 2) a Juan inmediatamente.")
    elif response.status_code in [400, 402, 403]:
        print(Fore.GREEN + Style.BRIGHT + "✅ [PASS] ARQUITECTURA ZERO TRUST CONFIRMADA.")
        print(Fore.GREEN + "El backend rechazó el payload manipulado por falta de comprobante de pago.")
    elif response.status_code == 409:
        print(Fore.YELLOW + "⚠️ [REINTENTO] Conflicto de horario. El slot 14:00 ya está ocupado. Cambia 'horaInicio' en el script y vuelve a lanzar.")
    else:
        print(Fore.YELLOW + "⚠️ [INDETERMINADO] Analizar el cuerpo de la respuesta para determinar la causa del fallo (ej. formato de fecha, validación de DTO).")

if __name__ == "__main__":
    ejecutar_auditoria()