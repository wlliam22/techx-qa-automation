import os
import requests
import pytest
from colorama import Fore, Style

# Definimos los campos tóxicos que NUNCA deben viajar a un cliente no autorizado
TOXIC_FIELDS = [
    "passwordResetExpires",
    "resetTokenId",
    #"weight",
    #"height",
    #"bloodType",
    "rfc",
    "emergencyContact",
    "clabe"
]

# Array de Endpoints a escanear (basado en la interceptación de Red)
# Tupla: (Método, Ruta, Payload_o_Params)
ENDPOINTS_TO_AUDIT = [
    ("POST", "/login", {"identifier": "williamparral93@gmail.com", "password": "Wm20745046."}), # Ajustar credenciales si es necesario
    ("GET", "/users/me/onboarding", None),
    ("GET", "/doctor/my-availability", None),
    ("POST", "/doctor-turnos", {"doctorId": "de5d2dea-8448-4fef-9086-f75b9bb7e0d0"}),
    ("GET", "/notifications", {"userId": "de5d2dea-8448-4fef-9086-f75b9bb7e0d0", "userType": "doctor"}),
    ("GET", "/conversations/user", {"userId": "de5d2dea-8448-4fef-9086-f75b9bb7e0d0"})
]

BASE_URL = "https://test-docappoint.techxmx.com"

class TestDataMinimizationAPI:

    @pytest.mark.parametrize("method, endpoint, data", ENDPOINTS_TO_AUDIT)
    def test_endpoint_data_minimization(self, method, endpoint, data):
        print(Fore.CYAN + f"\n=== [DOCA-SEC-044] AUDITORÍA DTO: {method} {endpoint} ===")
        
        # 1. Configurar Cabeceras Base (Zero Trust)
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json" if method == "POST" else None,
            "x-vercel-protection-bypass": os.getenv("VERCEL_DOCAPPOINT_BYPASS_SECRET", "oL9J8uCUbCOQkpLd85zYXdpe2YvPACSZ")
        }

        # NOTA: Para endpoints protegidos (todo excepto login), necesitamos inyectar el JWT real.
        # Aquí asumimos que conftest.py o un fixture provee el token, pero para la prueba directa 
        # inyectaremos el token estático del Doctor capturado (reemplazar por gestión dinámica en el futuro).
        if endpoint != "/login":
            # Extraemos el token puro, sin duplicar la palabra 'Bearer'
            token_estatico = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJwcm9maWxlX3BpY3R1cmVfdXJsIjoiaHR0cHM6Ly9kb2NhcHBvaW50LXN0YWdpbmcuczMuYW1hem9uYXdzLmNvbS9wdWJsaWMvcHJvZmlsZS1waWMvZGU1ZDJkZWEtODQ0OC00ZmVmLTkwODYtZjc1YjliYjdlMGQwLzE3OTA2OTI2Mzg4MzIud2VicCIsImF2YXRhcl91cmwiOiJodHRwczovL2RvY2FwcG9pbnQtc3RhZ2luZy5zMy5hbWF6b25hd3MuY29tL3B1YmxpYy9wcm9maWxlLWF2YXRhci9kZTVkMmRlYS04NDQ4LTRmZWYtOTA4Ni1mNzViOWJiN2UwZDAvMTc5MDY5MjY1NzQwMi53ZWJwIiwiY2VkdWxhX3VybCI6Imh0dHBzOi8vZG9jYXBwb2ludC1zdGFnaW5nLnMzLnVzLXdlc3QtMS5hbWF6b25hd3MuY29tL2NlZHVsYXMvZGU1ZDJkZWEtODQ0OC00ZmVmLTkwODYtZjc1YjliYjdlMGQwLzE3NzA5MDk5MDk5MDdfQmFja2xvZyUyMFByb3hpc18lMjBSdXRhJTIwQ3IlQzMlQUR0aWNhJTIwQ1BNLnBkZj9BV1NBY2Nlc3NLZXlJZD1BS0lBUlJQRE5GSlJGTE5KREc1SCZFeHBpcmVzPTE3OTIwOTI5ODYmU2lnbmF0dXJlPUxMUUIlMkJDQzklMkJRUHU0JTJCYlZaaSUyQjc1NWhCYUVnJTNEIiwiY2VkdWxhX2xhYm9yYXRvcmlvX3VybCI6bnVsbCwiaWQiOiJkZTVkMmRlYS04NDQ4LTRmZWYtOTA4Ni1mNzViOWJiN2UwZDAiLCJuYW1lIjoiV2lsbGlhbSIsImxhc3ROYW1lIjoiUGFycmFsIiwiYWdlIjoiMTk5My0wOC0yNyIsImVtYWlsIjoid2lsbGlhbXBhcnJhbDkzQGdtYWlsLmNvbSIsInBob25lIjoiKzU4NDI0MjE0MTI4MiIsImNvdW50cnkiOiJNw6l4aWNvIiwic3RhdGUiOiJTb25vcmEiLCJhZHJlc3MiOiJoZXJtb3NpbGxvIiwiY2l0eSI6Ikhlcm1vc2lsbG8iLCJjaXR5U2x1ZyI6Imhlcm1vc2lsbG8iLCJkZXNjcmlwdGlvbiI6IkxhIHNhbHVkIGVzIG51ZXN0cmEgYmFuZGVyYSB5IHR1IGJpbmVuZXN0YXIgbWkgcHJpb3JpZGFkLCBhZ2VuZGEgY29uIG5vc290cm9zIHkgbWFudGVuIG5pIGJpZW4gbWFzIGltcG9ydGFudGUgZW4gbGFzIG1lam9yZXMgbWFub3MuIiwiYmFubmVkIjpmYWxzZSwicHJpY2UiOjIwMDAsImNsYWJlIjpudWxsLCJiYW5rIjpudWxsLCJzdWJzY3JpcHRpb24iOnRydWUsImNlZHVsYVZlcmlmaWVkIjp0cnVlLCJhZG1pbiI6dHJ1ZSwiZW1haWxWZXJpZmllZCI6dHJ1ZSwidXNlclR5cGUiOiJkb2N0b3IiLCJjYXRlZ29yeSI6IkNhcmRpb2xvZ2lhIiwidXNlSW5kaXZpZHVhbENhbGVuZGFyIjp0cnVlLCJhdXRvQWNjZXB0QXBwb2ludG1lbnRzIjp0cnVlLCJ3YW50c0VtYWlsTm90aWZpY2F0aW9ucyI6dHJ1ZSwid2FudHNXaGF0c2FwcE5vdGlmaWNhdGlvbnMiOnRydWUsInNob3dJbkxpc3RpbmdzIjpmYWxzZSwiYmlydGhkYXlFbWFpbFNlbnRBdCI6bnVsbCwic3RhcnRUaW1lIjoiMDg6MDAiLCJlbmRUaW1lIjoiMTg6MDAiLCJpbnRlcnZhbCI6IjMwIiwiZGF5T2ZmIjoiU8OhYmFkbyxEb21pbmdvIiwidGltZXpvbmUiOiJBbWVyaWNhL0hlcm1vc2lsbG8iLCJzY2hlZHVsZUNvbmZpZyI6bnVsbCwiaW5kaXZpZHVhbEF2YWlsYWJpbGl0eUNvbmZpZ3VyZWQiOnRydWUsImxhYl9jYXRlZ29yeSI6bnVsbCwicmZjIjoiMTI2MzgwMjcxOTIiLCJnZW5kZXIiOiJtYXNjdWxpbm8iLCJibG9vZFR5cGUiOiJPKyIsImVtZXJnZW5jeUNvbnRhY3QiOiJNYWRyZSIsImVtZXJnZW5jeVBob25lIjoiMTIzNDU2Nzg5MTIzNDU3Njk4NzkiLCJ3ZWlnaHQiOjk1LCJoZWlnaHQiOjE2MCwiaXNEb2NhS2lkcyI6ZmFsc2UsIm1lZGljYWxMaWNlbnNlIjoiQUpYLTI1MjUiLCJvZmZpY2VBZGRyZXNzIjoiaGVybW9zaWxsbyIsIm9mZmljZV9sYXRpdHVkZSI6IjAuMDAwMDAwMDAiLCJvZmZpY2VfbG9uZ2l0dWRlIjoiMC4wMDAwMDAwMCIsInZlcmlmaWNhdGlvbkRvY3VtZW50cyI6bnVsbCwidW5pdmVyc2lkYWQiOiJVTkFNIiwiYW5vc0V4cGVyaWVuY2lhIjo1LCJyZXNldFRva2VuSWQiOiI1YTQxNjJiZi1mOTQwLTQ5MzctYmI2My1kMGJiN2NjOGM5NGEiLCJwYXNzd29yZFJlc2V0RXhwaXJlcyI6IjIwMjYtMDgtMTlUMTU6MzE6NTEuNTQ3WiIsInRlcm1zQWNjZXB0ZWQiOnRydWUsImVtYWlsVmVyaWZpY2F0aW9uVG9rZW4iOm51bGwsImVtYWlsVmVyaWZpY2F0aW9uRXhwaXJlcyI6bnVsbCwiZW1haWxWZXJpZmljYXRpb25MYXN0U2VudEF0IjpudWxsLCJ0ZXJtc0FjY2VwdGVkQXQiOiIyMDI2LTEwLTA3VDE5OjUwOjM4LjY5NloiLCJ0ZXJtc1ZlcnNpb24iOiIxLjMiLCJpZFRlcm1zIjoiMDg3YjNiZGItNjFiZC00MTE0LTk0NTQtNTc0NzU3ZWNmN2IyIiwicG9saWNpZXNBY2NlcHRlZCI6dHJ1ZSwicG9saWNpZXNBY2NlcHRlZEF0IjoiMjAyNi0xMC0wN1QyMjozNjowOS43NzRaIiwicG9saWNpZXNWZXJzaW9uIjoiMS40IiwiaWRQb2xpY2llcyI6IjExM2U3YTQwLTQzYTQtNDNiYy1hMmU2LWJhMjk5N2EyOTNlMCIsInNlY3VyaXR5QWNjZXB0ZWQiOnRydWUsInNlY3VyaXR5QWNjZXB0ZWRBdCI6IjIwMjYtMTAtMDhUMTk6NTg6NDYuODM4WiIsInNlY3VyaXR5VmVyc2lvbiI6IjEuNCIsImlkU2VjdXJpdHkiOiJjNGMwNThmMy00YjgxLTRmMzgtYmRhMC01ZWMzYjBlZGZiZjMiLCJ1c2VySWQiOm51bGwsImp0aSI6IjY5YTdkZTM3LWQ4YmItNDliZi1iNWNhLTNjMGU2YWJjMzY1MSIsImlhdCI6MTc5MjA4OTM4NiwiZXhwIjoxNzkyNTIxMzg2fQ.d_um9b-N3u0IMccXqNqivxA1XPHPk1eVAlEy9M5_faE" # Pega aquí tu token puro
            headers["authorization"] = f"Bearer {os.getenv('TEST_DOCTOR_JWT', token_estatico)}"
        url = f"{BASE_URL}{endpoint}"
        
        # 2. Ejecutar Petición
        if method == "GET":
            response = requests.get(url, headers=headers, params=data)
        else:
            response = requests.post(url, headers=headers, json=data)

        # Si el endpoint devuelve 403 o 401 por falta de token válido, saltamos la validación de payload
        if response.status_code in [401, 403]:
            pytest.skip(f"Acceso denegado ({response.status_code}) - Se requiere token fresco para auditar payload.")

        assert response.status_code in [200, 201], f"Fallo de conexión: {response.status_code} - {response.text}"
        
        response_text = response.text

        # 3. Escaneo de Campos Tóxicos (String Matching para mayor agresividad contra anidaciones)
        fugas_detectadas = []
        for field in TOXIC_FIELDS:
            if f'"{field}"' in response_text:
                fugas_detectadas.append(field)

        if fugas_detectadas:
            pytest.fail(Fore.RED + f"🚨 [FAIL] OVER-FETCHING DETECTADO. El endpoint filtró datos prohibidos: {fugas_detectadas}")
        else:
            print(Fore.GREEN + f"✅ [PASS] Endpoint limpio. Arquitectura DTO respetada.")