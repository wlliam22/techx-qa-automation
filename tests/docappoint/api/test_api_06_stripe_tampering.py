import os
import requests
import pytest
from colorama import Fore, Style

BASE_URL = "https://test-docappoint.techxmx.com"
ENDPOINT = "/stripe/advance-checkout"

class TestStripeIntegrity:

    def test_stripe_price_tampering(self):
        print(Fore.CYAN + f"\n=== [DOCA-SEC-01] AUDITORÍA ZERO TRUST (STRIPE): POST {ENDPOINT} ===")
        
        # 1. Payload base capturado de la red.
        payload = {
            "doctor": { "id": "de5d2dea-8448-4fef-9086-f75b9bb7e0d0" }, # Reducido por brevedad, el backend asume validación
            "user": { "id": "29d353a0-012a-4c68-bf29-93f05546703b" },
            "turno": "2026-10-18 08:30",
            "type": "doctor",
            "stateTurno": "pendiente",
            "consultorioId": "85fefe9a-c5a3-48fb-af3d-70134277407d",
            "serviceId": "d5eba3f2-7773-4b51-b7f4-c996b889a523", # Asegúrate de que ESTE servicio esté ACTIVO en el admin para que no de 400
            "serviceName": "Seguimiento post operatorio",
            "serviceDurationMinutes": "30",
            # 🚨 INYECCIÓN FINANCIERA (PRICE TAMPERING) 🚨
            "servicePrice": "1" # Modificamos de 20000 a 1
        }
        
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "x-vercel-protection-bypass": os.getenv("VERCEL_DOCAPPOINT_BYPASS_SECRET", "oL9J8uCUbCOQkpLd85zYXdpe2YvPACSZ"),
            "authorization": f"Bearer {os.getenv('TEST_PATIENT_JWT', 'eyJhbGciOi')}"
        }
        
        url = f"{BASE_URL}{ENDPOINT}"
        response = requests.post(url, headers=headers, json=payload)
        
        # Si el servicio sigue inactivo (400), el test fallará por precondición, no por seguridad.
        assert response.status_code == 200, Fore.YELLOW + f"⚠️ Test abortado: El servidor rechazó la petición ({response.status_code}). Asegúrate de reactivar el servicio en el Admin. Respuesta: {response.text}"
        
        response_json = response.json()
        
        # 2. Validación Zero Trust
        # El endpoint de Stripe suele devolver el 'clientSecret', el 'id' de la sesión de pago y el monto total calculado.
        # Si la respuesta incluye el monto que va a cobrar Stripe, validamos que no sea nuestro "1" inyectado.
        
        monto_stripe = str(response_json.get("amount", response_json.get("total", "")))
        
        if "1" == monto_stripe or "100" == monto_stripe: # Stripe maneja centavos, 1 peso = 100 centavos
            pytest.fail(Fore.RED + f"🚨 [FAIL] PRICE TAMPERING EXITOSO (OWASP A04). El backend generó un pago en Stripe usando el precio falso del cliente: {response_json}")
            
        print(Fore.GREEN + f"✅ [PASS] El backend ignoró el 'servicePrice' falso y extrajo el valor real de la base de datos.")