import os
import requests
import pytest
from colorama import Fore, Style

BASE_URL = "https://test-docappoint.techxmx.com"
ENDPOINT = "/nuevoTurnoCheckOut"

class TestAppointmentIntegrity:

    def test_appointment_state_and_price_tampering(self):
        print(Fore.CYAN + f"\n=== [DOCA-SEC-01/02] AUDITORÍA ZERO TRUST: POST {ENDPOINT} ===")
        
        # 1. Armamos el payload envenenado basado en la captura de red real.
        # Intencionalmente alteramos el estado e inyectamos variables financieras prohibidas.
        payload = {
            "consultorioId": None,
            "createdByDoctor": True,
            "doctor": {
                "id": "de5d2dea-8448-4fef-9086-f75b9bb7e0d0",
                "lastName": "Parral",
                "name": "William",
                "phone": "+584242141282"
            },
            "inviteIfMissing": False,
            "serviceId": "02bff261-4526-49fd-b172-5bf8e86d8828",
            "slotTimezone": "America/Hermosillo",
            "turno": "2026-10-16 12:00",
            "type": "doctor",
            "user": {
                "email": "w.lliam01010@gmail.com",
                "id": "29d353a0-012a-4c68-bf29-93f05546703b",
                "lastName": "parral",
                "name": "william",
                "phone": "+584242141282"
            },
            # 🚨 PAYLOADS ENVENENADOS INYECTADOS 🚨
            "stateTurno": "aprobada",  # Intento de State Tampering
            "precio": 0.01,            # Intento de Mass Assignment (Price Tampering)
            "price": 0.01,
            "monto": 0.01
        }
        
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "x-vercel-protection-bypass": os.getenv("VERCEL_DOCAPPOINT_BYPASS_SECRET", "oL9J8uCUbCOQkpLd85zYXdpe2YvPACSZ"),
            "authorization": f"Bearer {os.getenv('TEST_DOCTOR_JWT', 'eyJhbGciOi')}"
        }
        
        url = f"{BASE_URL}{ENDPOINT}"
        response = requests.post(url, headers=headers, json=payload)
        
        assert response.status_code in [200, 201], f"La creación de cita falló: {response.text}"
        
        response_json = response.json()
        
        # 2. Criterios de Aceptación (Zero Trust)
        # Extraemos el objeto de la cita creada desde la respuesta de la BD
        cita_creada = response_json.get("cita", response_json.get("data", response_json))
        
        # ASERCIÓN 1: El estado de la cita DEBE ser 'pendiente', ignorando el 'aprobada' que enviamos.
        estado_final = cita_creada.get("stateTurno") or cita_creada.get("estado")
        if estado_final == "aprobada":
            pytest.fail(Fore.RED + "🚨 [FAIL] STATE TAMPERING EXITOSO (OWASP A08). El backend confió en el estado 'aprobada' enviado por el cliente.")
            
        # ASERCIÓN 2: El precio de la cita NO debe ser 0.01 (debe tomarlo de la BD usando el serviceId)
        precio_final = str(cita_creada.get("precio", cita_creada.get("price", "")))
        if "0.01" in precio_final:
            pytest.fail(Fore.RED + "🚨 [FAIL] MASS ASSIGNMENT EXITOSO (OWASP A04). El backend guardó el precio manipulado.")
            
        print(Fore.GREEN + f"✅ [PASS] Arquitectura íntegra. El backend ignoró el estado '{estado_final}' e inyecciones de precio.")