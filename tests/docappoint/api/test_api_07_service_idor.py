import os
import requests
import pytest
from colorama import Fore, Style

BASE_URL = "https://test-docappoint.techxmx.com"
ENDPOINT = "/nuevoTurnoCheckOut"

# ⚠️ INYECTA AQUÍ LOS DATOS DEL ATAQUE
DOCTOR_A_ID = "de5d2dea-8448-4fef-9086-f75b9bb7e0d0" # Tu ID de médico actual
SERVICE_B_ID = "7849172b-08f9-43a2-8d31-52a4bdc7b437" # Pega el ID del servicio del OTRO médico

class TestServiceAccessControl:

    def test_idor_cross_doctor_service(self):
        print(Fore.CYAN + f"\n=== [DOCA-SEC-02] AUDITORÍA IDOR (OWASP A01): POST {ENDPOINT} ===")
        
        # Payload de creación de cita para el Doctor A, pero inyectando el Servicio del Doctor B
        payload = {
            "consultorioId": None,
            "createdByDoctor": True,
            "doctor": {
                "id": DOCTOR_A_ID, 
                "name": "William",
                "lastName": "Parral"
            },
            "inviteIfMissing": False,
            "serviceId": SERVICE_B_ID,  # 🚨 INYECCIÓN DEL IDOR
            "slotTimezone": "America/Hermosillo",
            "turno": "2026-10-20 10:00", # Asegúrate de que sea una fecha futura/libre
            "type": "doctor",
            "user": {
                "email": "w.lliam01010@gmail.com",
                "id": "29d353a0-012a-4c68-bf29-93f05546703b"
            },
            "stateTurno": "pendiente"
        }
        
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "x-vercel-protection-bypass": os.getenv("VERCEL_DOCAPPOINT_BYPASS_SECRET", "oL9J8uCUbCOQkpLd85zYXdpe2YvPACSZ"),
            "authorization": f"Bearer {os.getenv('TEST_DOCTOR_JWT', 'TU_TOKEN_JWT_AQUI')}" # Token de William
        }
        
        url = f"{BASE_URL}{ENDPOINT}"
        response = requests.post(url, headers=headers, json=payload)
        
        # 🛡️ Criterios de Validación Zero Trust
        # El backend DEBE darse cuenta de que el SERVICE_B_ID no le pertenece al DOCTOR_A_ID.
        # Debe abortar la transacción con un 400 o 403.
        
        if response.status_code in [200, 201]:
            pytest.fail(Fore.RED + f"🚨 [FAIL] IDOR TRANSVERSAL EXITOSO. El backend guardó la cita con un servicio ajeno al médico. Respuesta: {response.text}")
            
        assert response.status_code in [400, 403, 404], Fore.RED + f"Error inesperado: {response.status_code}"
        
        print(Fore.GREEN + f"✅ [PASS] Arquitectura Zero Trust confirmada. El backend rechazó vincular un servicio ajeno al médico (Status: {response.status_code}).")