import os
import json
import requests
import pytest
from jsonschema import validate, ValidationError
from colorama import Fore, Style

# Ruta al esquema congelado ("Deep Freeze")
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), '../../../schemas/docappoint/auth_login_schema.json')
API_URL = "https://test-docappoint.techxmx.com/login" # Ajustar a la ruta real de Staging

def load_schema():
    with open(SCHEMA_PATH, 'r') as file:
        return json.load(file)

class TestAuthAPIContract:
    
    def test_login_contract_deep_freeze(self):
        print(Fore.CYAN + "\n=== [DOCA-API-01] CONTRACT TEST: LOGIN SCHEMA (OWASP A02) ===")
        
        payload = {
            "email": "williamparral93@gmail.com", # Credencial estática de Staging
            "password": "Wm20745046."
        }
        
        headers = {
            "Accept": "application/json",
            "x-vercel-protection-bypass": os.getenv("VERCEL_DOCAPPOINT_BYPASS_SECRET", "oL9J8uCUbCOQkpLd85zYXdpe2YvPACSZ")
        }

        # 1. Ejecutar la llamada real a Staging
        response = requests.post(API_URL, json=payload, headers=headers)
        assert response.status_code == 200, f"El login falló: {response.text}"
        
        response_json = response.json()
        schema = load_schema()

        # 2. El "Deep Freeze": Validar la respuesta real contra el esquema óptimo
        try:
            validate(instance=response_json, schema=schema)
            print(Fore.GREEN + "✅ [PASS] El contrato de la API está intacto. No hay mutaciones en el DTO.")
        except ValidationError as e:
            pytest.fail(Fore.RED + f"🚨 [FAIL] MUTACIÓN DETECTADA EN EL CONTRATO DE LOGIN.\nDetalle: {e.message}")