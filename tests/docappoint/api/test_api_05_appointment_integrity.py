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
            "authorization": f"Bearer {os.getenv('TEST_DOCTOR_JWT', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJwcm9maWxlX3BpY3R1cmVfdXJsIjoiaHR0cHM6Ly9kb2NhcHBvaW50LXN0YWdpbmcuczMuYW1hem9uYXdzLmNvbS9wdWJsaWMvcHJvZmlsZS1waWMvZGU1ZDJkZWEtODQ0OC00ZmVmLTkwODYtZjc1YjliYjdlMGQwLzE3OTA2OTI2Mzg4MzIud2VicCIsImF2YXRhcl91cmwiOiJodHRwczovL2RvY2FwcG9pbnQtc3RhZ2luZy5zMy5hbWF6b25hd3MuY29tL3B1YmxpYy9wcm9maWxlLWF2YXRhci9kZTVkMmRlYS04NDQ4LTRmZWYtOTA4Ni1mNzViOWJiN2UwZDAvMTc5MDY5MjY1NzQwMi53ZWJwIiwiY2VkdWxhX3VybCI6Imh0dHBzOi8vZG9jYXBwb2ludC1zdGFnaW5nLnMzLnVzLXdlc3QtMS5hbWF6b25hd3MuY29tL2NlZHVsYXMvZGU1ZDJkZWEtODQ0OC00ZmVmLTkwODYtZjc1YjliYjdlMGQwLzE3NzA5MDk5MDk5MDdfQmFja2xvZyUyMFByb3hpc18lMjBSdXRhJTIwQ3IlQzMlQUR0aWNhJTIwQ1BNLnBkZj9BV1NBY2Nlc3NLZXlJZD1BS0lBUlJQRE5GSlJGTE5KREc1SCZFeHBpcmVzPTE3OTIxMDEwMzImU2lnbmF0dXJlPUhZQXFrOERqWDdTYnVIbGpwTXUlMkZjcFB4MWdFJTNEIiwiY2VkdWxhX2xhYm9yYXRvcmlvX3VybCI6bnVsbCwiaWQiOiJkZTVkMmRlYS04NDQ4LTRmZWYtOTA4Ni1mNzViOWJiN2UwZDAiLCJuYW1lIjoiV2lsbGlhbSIsImxhc3ROYW1lIjoiUGFycmFsIiwiYWdlIjoiMTk5My0wOC0yNyIsImVtYWlsIjoid2lsbGlhbXBhcnJhbDkzQGdtYWlsLmNvbSIsInBob25lIjoiKzU4NDI0MjE0MTI4MiIsImNvdW50cnkiOiJNw6l4aWNvIiwic3RhdGUiOiJTb25vcmEiLCJhZHJlc3MiOiJoZXJtb3NpbGxvIiwiY2l0eSI6Ikhlcm1vc2lsbG8iLCJjaXR5U2x1ZyI6Imhlcm1vc2lsbG8iLCJkZXNjcmlwdGlvbiI6IkxhIHNhbHVkIGVzIG51ZXN0cmEgYmFuZGVyYSB5IHR1IGJpbmVuZXN0YXIgbWkgcHJpb3JpZGFkLCBhZ2VuZGEgY29uIG5vc290cm9zIHkgbWFudGVuIG5pIGJpZW4gbWFzIGltcG9ydGFudGUgZW4gbGFzIG1lam9yZXMgbWFub3MuIiwiYmFubmVkIjpmYWxzZSwicHJpY2UiOjIwMDAsImNsYWJlIjpudWxsLCJiYW5rIjpudWxsLCJzdWJzY3JpcHRpb24iOnRydWUsImNlZHVsYVZlcmlmaWVkIjp0cnVlLCJhZG1pbiI6dHJ1ZSwiZW1haWxWZXJpZmllZCI6dHJ1ZSwidXNlclR5cGUiOiJkb2N0b3IiLCJjYXRlZ29yeSI6IkNhcmRpb2xvZ2lhIiwidXNlSW5kaXZpZHVhbENhbGVuZGFyIjp0cnVlLCJhdXRvQWNjZXB0QXBwb2ludG1lbnRzIjp0cnVlLCJ3YW50c0VtYWlsTm90aWZpY2F0aW9ucyI6dHJ1ZSwid2FudHNXaGF0c2FwcE5vdGlmaWNhdGlvbnMiOnRydWUsInNob3dJbkxpc3RpbmdzIjpmYWxzZSwiYmlydGhkYXlFbWFpbFNlbnRBdCI6bnVsbCwic3RhcnRUaW1lIjoiMDg6MDAiLCJlbmRUaW1lIjoiMTg6MDAiLCJpbnRlcnZhbCI6IjMwIiwiZGF5T2ZmIjoiU8OhYmFkbyxEb21pbmdvIiwidGltZXpvbmUiOiJBbWVyaWNhL0hlcm1vc2lsbG8iLCJzY2hlZHVsZUNvbmZpZyI6bnVsbCwiaW5kaXZpZHVhbEF2YWlsYWJpbGl0eUNvbmZpZ3VyZWQiOnRydWUsImxhYl9jYXRlZ29yeSI6bnVsbCwicmZjIjoiMTI2MzgwMjcxOTIiLCJnZW5kZXIiOiJtYXNjdWxpbm8iLCJibG9vZFR5cGUiOiJPKyIsImVtZXJnZW5jeUNvbnRhY3QiOiJNYWRyZSIsImVtZXJnZW5jeVBob25lIjoiMTIzNDU2Nzg5MTIzNDU3Njk4NzkiLCJ3ZWlnaHQiOjk1LCJoZWlnaHQiOjE2MCwiaXNEb2NhS2lkcyI6ZmFsc2UsIm1lZGljYWxMaWNlbnNlIjoiQUpYLTI1MjUiLCJvZmZpY2VBZGRyZXNzIjoiaGVybW9zaWxsbyIsIm9mZmljZV9sYXRpdHVkZSI6IjAuMDAwMDAwMDAiLCJvZmZpY2VfbG9uZ2l0dWRlIjoiMC4wMDAwMDAwMCIsInZlcmlmaWNhdGlvbkRvY3VtZW50cyI6bnVsbCwidW5pdmVyc2lkYWQiOiJVTkFNIiwiYW5vc0V4cGVyaWVuY2lhIjo1LCJyZXNldFRva2VuSWQiOiI1YTQxNjJiZi1mOTQwLTQ5MzctYmI2My1kMGJiN2NjOGM5NGEiLCJwYXNzd29yZFJlc2V0RXhwaXJlcyI6IjIwMjYtMDgtMTlUMTU6MzE6NTEuNTQ3WiIsInRlcm1zQWNjZXB0ZWQiOnRydWUsImVtYWlsVmVyaWZpY2F0aW9uVG9rZW4iOm51bGwsImVtYWlsVmVyaWZpY2F0aW9uRXhwaXJlcyI6bnVsbCwiZW1haWxWZXJpZmljYXRpb25MYXN0U2VudEF0IjpudWxsLCJ0ZXJtc0FjY2VwdGVkQXQiOiIyMDI2LTEwLTA3VDE5OjUwOjM4LjY5NloiLCJ0ZXJtc1ZlcnNpb24iOiIxLjMiLCJpZFRlcm1zIjoiMDg3YjNiZGItNjFiZC00MTE0LTk0NTQtNTc0NzU3ZWNmN2IyIiwicG9saWNpZXNBY2NlcHRlZCI6dHJ1ZSwicG9saWNpZXNBY2NlcHRlZEF0IjoiMjAyNi0xMC0wN1QyMjozNjowOS43NzRaIiwicG9saWNpZXNWZXJzaW9uIjoiMS40IiwiaWRQb2xpY2llcyI6IjExM2U3YTQwLTQzYTQtNDNiYy1hMmU2LWJhMjk5N2EyOTNlMCIsInNlY3VyaXR5QWNjZXB0ZWQiOnRydWUsInNlY3VyaXR5QWNjZXB0ZWRBdCI6IjIwMjYtMTAtMDhUMTk6NTg6NDYuODM4WiIsInNlY3VyaXR5VmVyc2lvbiI6IjEuNCIsImlkU2VjdXJpdHkiOiJjNGMwNThmMy00YjgxLTRmMzgtYmRhMC01ZWMzYjBlZGZiZjMiLCJ1c2VySWQiOm51bGwsImp0aSI6Ijg3ZjI3ODBjLTFmNTAtNDg4MC04ODEzLTBhNWIzZTkwMzM4MiIsImlhdCI6MTc5MjA5NzQzMiwiZXhwIjoxNzkyNTI5NDMyfQ.erYvxFqb0MTvFvVrb773cYuGMpQGk38PK4bodCV0SUo')}"
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