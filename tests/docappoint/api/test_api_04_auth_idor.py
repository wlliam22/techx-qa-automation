import os
import requests
import pytest
from colorama import Fore, Style

BASE_URL = "https://test-docappoint.techxmx.com"
# ID ficticio simulando a una víctima (otro médico o paciente)
VICTIM_TARGET_ID = "884d10a7-b220-4e74-84f9-305725b36d80"

class TestAuthAccessControl:

    def test_password_change_idor_protection(self):
        print(Fore.CYAN + "\n=== [DOCA-SEC-045] AUDITORÍA ZERO TRUST: PATCH /password ===")
        
        # 1. Armamos el payload asumiendo que el atacante conoce su propia contraseña, 
        # pero inyecta el ID de la víctima en la URL.
        payload = {
            "currentPassword": "*************", 
            "newPassword": "HackedPassword123!"
        }
        
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "x-vercel-protection-bypass": os.getenv("VERCEL_DOCAPPOINT_BYPASS_SECRET", "sd"),
            "authorization": f"Bearer {os.getenv('TEST_DOCTOR_JWT', 'eyJhbGciOi')}"
        }
        
        # Simulamos la ruta vulnerable actual
        url = f"{BASE_URL}/users/{VICTIM_TARGET_ID}/password"
        
        response = requests.patch(url, headers=headers, json=payload)
        
        # 2. Criterio de Aceptación (Zero Trust)
        # El servidor debe arrojar 403 Forbidden o 401 Unauthorized INMEDIATAMENTE 
        # al detectar que el JWT no coincide con el ID de la URL (o porque la ruta ya no existe tras el refactor).
        # Si devuelve 400 (Bad Request por contraseña incorrecta), significa que el IDOR llegó hasta la base de datos.
        
        if response.status_code == 400:
            pytest.fail(Fore.RED + f"🚨 [FAIL] FALLA ZERO TRUST. El backend procesó el ID ajeno y llegó a la capa de validación de base de datos. Status: {response.status_code}")
            
        assert response.status_code in [401, 403, 404], Fore.RED + f"🚨 [FAIL] Posible vulnerabilidad IDOR expuesta. Status: {response.status_code}"
        
        print(Fore.GREEN + "✅ [PASS] El controlador rechazó la inyección de ID ajeno. Zero Trust respetado.")