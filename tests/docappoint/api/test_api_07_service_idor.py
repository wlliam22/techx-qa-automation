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
            "authorization": f"Bearer {os.getenv('TEST_DOCTOR_JWT', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJwcm9maWxlX3BpY3R1cmVfdXJsIjoiaHR0cHM6Ly9kb2NhcHBvaW50LXN0YWdpbmcuczMuYW1hem9uYXdzLmNvbS9wdWJsaWMvcHJvZmlsZS1waWMvMjlkMzUzYTAtMDEyYS00YzY4LWJmMjktOTNmMDU1NDY3MDNiLzE3OTA2OTIxNzgxMjkud2VicCIsImF2YXRhcl91cmwiOiJodHRwczovL2RvY2FwcG9pbnQtc3RhZ2luZy5zMy5hbWF6b25hd3MuY29tL3B1YmxpYy9wcm9maWxlLWF2YXRhci8yOWQzNTNhMC0wMTJhLTRjNjgtYmYyOS05M2YwNTU0NjcwM2IvMTc4MjMzNjMyNjczMi53ZWJwIiwiY2VkdWxhX3VybCI6bnVsbCwiY2VkdWxhX2xhYm9yYXRvcmlvX3VybCI6bnVsbCwiaWQiOiIyOWQzNTNhMC0wMTJhLTRjNjgtYmYyOS05M2YwNTU0NjcwM2IiLCJuYW1lIjoid2lsbGlhbSIsImxhc3ROYW1lIjoicGFycmFsIiwiYWdlIjoiMTk5My0wOC0yNSIsImVtYWlsIjoidy5sbGlhbTAxMDEwQGdtYWlsLmNvbSIsInBob25lIjoiKzU4NDI0MjE0MTI4MiIsImNvdW50cnkiOiJNZXhpY28iLCJzdGF0ZSI6IlNvbm9yYSIsImFkcmVzcyI6bnVsbCwiY2l0eSI6bnVsbCwiY2l0eVNsdWciOm51bGwsImRlc2NyaXB0aW9uIjpudWxsLCJiYW5uZWQiOmZhbHNlLCJwcmljZSI6bnVsbCwiY2xhYmUiOm51bGwsImJhbmsiOm51bGwsInN1YnNjcmlwdGlvbiI6ZmFsc2UsImNlZHVsYVZlcmlmaWVkIjpmYWxzZSwiYWRtaW4iOmZhbHNlLCJlbWFpbFZlcmlmaWVkIjp0cnVlLCJ1c2VyVHlwZSI6InBhdGllbnQiLCJjYXRlZ29yeSI6bnVsbCwidXNlSW5kaXZpZHVhbENhbGVuZGFyIjp0cnVlLCJhdXRvQWNjZXB0QXBwb2ludG1lbnRzIjpmYWxzZSwid2FudHNFbWFpbE5vdGlmaWNhdGlvbnMiOnRydWUsIndhbnRzV2hhdHNhcHBOb3RpZmljYXRpb25zIjp0cnVlLCJzaG93SW5MaXN0aW5ncyI6dHJ1ZSwiYmlydGhkYXlFbWFpbFNlbnRBdCI6bnVsbCwic3RhcnRUaW1lIjoiMDg6MDAiLCJlbmRUaW1lIjoiMTY6MDAiLCJpbnRlcnZhbCI6IjMwIiwiZGF5T2ZmIjpudWxsLCJ0aW1lem9uZSI6IkFtZXJpY2EvQ2FyYWNhcyIsInNjaGVkdWxlQ29uZmlnIjpudWxsLCJpbmRpdmlkdWFsQXZhaWxhYmlsaXR5Q29uZmlndXJlZCI6ZmFsc2UsImxhYl9jYXRlZ29yeSI6bnVsbCwicmZjIjpudWxsLCJnZW5kZXIiOiJtYXNjdWxpbm8iLCJibG9vZFR5cGUiOiJPLSIsImVtZXJnZW5jeUNvbnRhY3QiOiJFc3Bvc2EiLCJlbWVyZ2VuY3lQaG9uZSI6Iis1ODQyNDIxNDEyODIiLCJ3ZWlnaHQiOjk0LCJoZWlnaHQiOjE2MywiaXNEb2NhS2lkcyI6ZmFsc2UsIm1lZGljYWxMaWNlbnNlIjpudWxsLCJvZmZpY2VBZGRyZXNzIjpudWxsLCJvZmZpY2VfbGF0aXR1ZGUiOm51bGwsIm9mZmljZV9sb25naXR1ZGUiOm51bGwsInZlcmlmaWNhdGlvbkRvY3VtZW50cyI6bnVsbCwidW5pdmVyc2lkYWQiOm51bGwsImFub3NFeHBlcmllbmNpYSI6bnVsbCwicmVzZXRUb2tlbklkIjpudWxsLCJwYXNzd29yZFJlc2V0RXhwaXJlcyI6bnVsbCwidGVybXNBY2NlcHRlZCI6dHJ1ZSwiZW1haWxWZXJpZmljYXRpb25Ub2tlbiI6bnVsbCwiZW1haWxWZXJpZmljYXRpb25FeHBpcmVzIjpudWxsLCJlbWFpbFZlcmlmaWNhdGlvbkxhc3RTZW50QXQiOm51bGwsInRlcm1zQWNjZXB0ZWRBdCI6IjIwMjYtMTAtMDlUMTQ6NTQ6MDkuMzEzWiIsInRlcm1zVmVyc2lvbiI6IjEuMyIsImlkVGVybXMiOiIwODdiM2JkYi02MWJkLTQxMTQtOTQ1NC01NzQ3NTdlY2Y3YjIiLCJwb2xpY2llc0FjY2VwdGVkIjp0cnVlLCJwb2xpY2llc0FjY2VwdGVkQXQiOiIyMDI2LTEwLTA5VDE0OjU0OjA5Ljg3MFoiLCJwb2xpY2llc1ZlcnNpb24iOiIxLjQiLCJpZFBvbGljaWVzIjoiMTEzZTdhNDAtNDNhNC00M2JjLWEyZTYtYmEyOTk3YTI5M2UwIiwic2VjdXJpdHlBY2NlcHRlZCI6dHJ1ZSwic2VjdXJpdHlBY2NlcHRlZEF0IjoiMjAyNi0xMC0wOVQxNDo1NDoxMC4yOTVaIiwic2VjdXJpdHlWZXJzaW9uIjoiMS40IiwiaWRTZWN1cml0eSI6ImM0YzA1OGYzLTRiODEtNGYzOC1iZGEwLTVlYzNiMGVkZmJmMyIsInVzZXJJZCI6bnVsbCwianRpIjoiYjQ1YjI0NDMtYTgwNS00N2VlLWFmNGQtOWQwNGIwZDVmNzA0IiwiaWF0IjoxNzkyMDk4MzE0LCJleHAiOjE3OTI1MzAzMTR9.8XmIlVcR5FoR8t0EIwxi5iLPIiGyFq-4U1SaLsNuZNA')}" # Token de William
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