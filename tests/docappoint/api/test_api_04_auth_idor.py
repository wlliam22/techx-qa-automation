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
            "currentPassword": "Wm20745046.", 
            "newPassword": "HackedPassword123!"
        }
        
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "x-vercel-protection-bypass": os.getenv("VERCEL_DOCAPPOINT_BYPASS_SECRET", "oL9J8uCUbCOQkpLd85zYXdpe2YvPACSZ"),
            "authorization": f"Bearer {os.getenv('TEST_DOCTOR_JWT', 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJwcm9maWxlX3BpY3R1cmVfdXJsIjoiaHR0cHM6Ly9kb2NhcHBvaW50LXN0YWdpbmcuczMuYW1hem9uYXdzLmNvbS9wdWJsaWMvcHJvZmlsZS1waWMvZGU1ZDJkZWEtODQ0OC00ZmVmLTkwODYtZjc1YjliYjdlMGQwLzE3OTA2OTI2Mzg4MzIud2VicCIsImF2YXRhcl91cmwiOiJodHRwczovL2RvY2FwcG9pbnQtc3RhZ2luZy5zMy5hbWF6b25hd3MuY29tL3B1YmxpYy9wcm9maWxlLWF2YXRhci9kZTVkMmRlYS04NDQ4LTRmZWYtOTA4Ni1mNzViOWJiN2UwZDAvMTc5MDY5MjY1NzQwMi53ZWJwIiwiY2VkdWxhX3VybCI6Imh0dHBzOi8vZG9jYXBwb2ludC1zdGFnaW5nLnMzLnVzLXdlc3QtMS5hbWF6b25hd3MuY29tL2NlZHVsYXMvZGU1ZDJkZWEtODQ0OC00ZmVmLTkwODYtZjc1YjliYjdlMGQwLzE3NzA5MDk5MDk5MDdfQmFja2xvZyUyMFByb3hpc18lMjBSdXRhJTIwQ3IlQzMlQUR0aWNhJTIwQ1BNLnBkZj9BV1NBY2Nlc3NLZXlJZD1BS0lBUlJQRE5GSlJGTE5KREc1SCZFeHBpcmVzPTE3OTIwOTc4MjcmU2lnbmF0dXJlPUZBNmJGR0ZaZW01blhiTzh2bU5HejY1eTk5USUzRCIsImNlZHVsYV9sYWJvcmF0b3Jpb191cmwiOm51bGwsImlkIjoiZGU1ZDJkZWEtODQ0OC00ZmVmLTkwODYtZjc1YjliYjdlMGQwIiwibmFtZSI6IldpbGxpYW0iLCJsYXN0TmFtZSI6IlBhcnJhbCIsImFnZSI6IjE5OTMtMDgtMjciLCJlbWFpbCI6IndpbGxpYW1wYXJyYWw5M0BnbWFpbC5jb20iLCJwaG9uZSI6Iis1ODQyNDIxNDEyODIiLCJjb3VudHJ5IjoiTcOpeGljbyIsInN0YXRlIjoiU29ub3JhIiwiYWRyZXNzIjoiaGVybW9zaWxsbyIsImNpdHkiOiJIZXJtb3NpbGxvIiwiY2l0eVNsdWciOiJoZXJtb3NpbGxvIiwiZGVzY3JpcHRpb24iOiJMYSBzYWx1ZCBlcyBudWVzdHJhIGJhbmRlcmEgeSB0dSBiaW5lbmVzdGFyIG1pIHByaW9yaWRhZCwgYWdlbmRhIGNvbiBub3NvdHJvcyB5IG1hbnRlbiBuaSBiaWVuIG1hcyBpbXBvcnRhbnRlIGVuIGxhcyBtZWpvcmVzIG1hbm9zLiIsImJhbm5lZCI6ZmFsc2UsInByaWNlIjoyMDAwLCJjbGFiZSI6bnVsbCwiYmFuayI6bnVsbCwic3Vic2NyaXB0aW9uIjp0cnVlLCJjZWR1bGFWZXJpZmllZCI6dHJ1ZSwiYWRtaW4iOnRydWUsImVtYWlsVmVyaWZpZWQiOnRydWUsInVzZXJUeXBlIjoiZG9jdG9yIiwiY2F0ZWdvcnkiOiJDYXJkaW9sb2dpYSIsInVzZUluZGl2aWR1YWxDYWxlbmRhciI6dHJ1ZSwiYXV0b0FjY2VwdEFwcG9pbnRtZW50cyI6dHJ1ZSwid2FudHNFbWFpbE5vdGlmaWNhdGlvbnMiOnRydWUsIndhbnRzV2hhdHNhcHBOb3RpZmljYXRpb25zIjp0cnVlLCJzaG93SW5MaXN0aW5ncyI6ZmFsc2UsImJpcnRoZGF5RW1haWxTZW50QXQiOm51bGwsInN0YXJ0VGltZSI6IjA4OjAwIiwiZW5kVGltZSI6IjE4OjAwIiwiaW50ZXJ2YWwiOiIzMCIsImRheU9mZiI6IlPDoWJhZG8sRG9taW5nbyIsInRpbWV6b25lIjoiQW1lcmljYS9IZXJtb3NpbGxvIiwic2NoZWR1bGVDb25maWciOm51bGwsImluZGl2aWR1YWxBdmFpbGFiaWxpdHlDb25maWd1cmVkIjp0cnVlLCJsYWJfY2F0ZWdvcnkiOm51bGwsInJmYyI6IjEyNjM4MDI3MTkyIiwiZ2VuZGVyIjoibWFzY3VsaW5vIiwiYmxvb2RUeXBlIjoiTysiLCJlbWVyZ2VuY3lDb250YWN0IjoiTWFkcmUiLCJlbWVyZ2VuY3lQaG9uZSI6IjEyMzQ1Njc4OTEyMzQ1NzY5ODc5Iiwid2VpZ2h0Ijo5NSwiaGVpZ2h0IjoxNjAsImlzRG9jYUtpZHMiOmZhbHNlLCJtZWRpY2FsTGljZW5zZSI6IkFKWC0yNTI1Iiwib2ZmaWNlQWRkcmVzcyI6Imhlcm1vc2lsbG8iLCJvZmZpY2VfbGF0aXR1ZGUiOiIwLjAwMDAwMDAwIiwib2ZmaWNlX2xvbmdpdHVkZSI6IjAuMDAwMDAwMDAiLCJ2ZXJpZmljYXRpb25Eb2N1bWVudHMiOm51bGwsInVuaXZlcnNpZGFkIjoiVU5BTSIsImFub3NFeHBlcmllbmNpYSI6NSwicmVzZXRUb2tlbklkIjoiNWE0MTYyYmYtZjk0MC00OTM3LWJiNjMtZDBiYjdjYzhjOTRhIiwicGFzc3dvcmRSZXNldEV4cGlyZXMiOiIyMDI2LTA4LTE5VDE1OjMxOjUxLjU0N1oiLCJ0ZXJtc0FjY2VwdGVkIjp0cnVlLCJlbWFpbFZlcmlmaWNhdGlvblRva2VuIjpudWxsLCJlbWFpbFZlcmlmaWNhdGlvbkV4cGlyZXMiOm51bGwsImVtYWlsVmVyaWZpY2F0aW9uTGFzdFNlbnRBdCI6bnVsbCwidGVybXNBY2NlcHRlZEF0IjoiMjAyNi0xMC0wN1QxOTo1MDozOC42OTZaIiwidGVybXNWZXJzaW9uIjoiMS4zIiwiaWRUZXJtcyI6IjA4N2IzYmRiLTYxYmQtNDExNC05NDU0LTU3NDc1N2VjZjdiMiIsInBvbGljaWVzQWNjZXB0ZWQiOnRydWUsInBvbGljaWVzQWNjZXB0ZWRBdCI6IjIwMjYtMTAtMDdUMjI6MzY6MDkuNzc0WiIsInBvbGljaWVzVmVyc2lvbiI6IjEuNCIsImlkUG9saWNpZXMiOiIxMTNlN2E0MC00M2E0LTQzYmMtYTJlNi1iYTI5OTdhMjkzZTAiLCJzZWN1cml0eUFjY2VwdGVkIjp0cnVlLCJzZWN1cml0eUFjY2VwdGVkQXQiOiIyMDI2LTEwLTA4VDE5OjU4OjQ2LjgzOFoiLCJzZWN1cml0eVZlcnNpb24iOiIxLjQiLCJpZFNlY3VyaXR5IjoiYzRjMDU4ZjMtNGI4MS00ZjM4LWJkYTAtNWVjM2IwZWRmYmYzIiwidXNlcklkIjpudWxsLCJqdGkiOiJjY2IyNDJjNS05YTgzLTRlODMtOGUyNS1jNjEwZTg5OWQ2MDkiLCJpYXQiOjE3OTIwOTQyMjcsImV4cCI6MTc5MjUyNjIyN30.5-7Hh4mPgzNMNhOZE_GpcHL7jtSEQVMU1rMmIb2X8VU')}"
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