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
    ("POST", "/login", {"identifier": "williamparral93@gmail.com", "password": "*************"}), # Ajustar credenciales si es necesario
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
            "x-vercel-protection-bypass": os.getenv("VERCEL_DOCAPPOINT_BYPASS_SECRET", "sd")
        }

        # NOTA: Para endpoints protegidos (todo excepto login), necesitamos inyectar el JWT real.
        # Aquí asumimos que conftest.py o un fixture provee el token, pero para la prueba directa 
        # inyectaremos el token estático del Doctor capturado (reemplazar por gestión dinámica en el futuro).
        if endpoint != "/login":
            # Extraemos el token puro, sin duplicar la palabra 'Bearer'
            token_estatico = "" # Pega aquí tu token puro
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