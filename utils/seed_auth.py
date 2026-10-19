import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

API_URL = os.getenv("DOCAPPOINT_API_URL", "https://test-docappoint.techxmx.com").rstrip("/")
WEB_URL = os.getenv("DOCAPPOINT_WEB_URL", "https://docappoint-git-staging-tech-x.vercel.app").rstrip("/")
BYPASS_SECRET = os.getenv("VERCEL_DOCAPPOINT_BYPASS_SECRET", " ")

ROLES = {
    "patient": {
        "email": os.getenv("DOCA_PATIENT_EMAIL", "w.lliam01010@gmail.com"),
        "password": os.getenv("DOCA_PATIENT_PASSWORD", "*************"),
        "output_path": "auth_patient.json"
    },
    "doctor": {
        "email": os.getenv("DOCA_DOCTOR_EMAIL", "williamparral93@gmail.com"),
        "password": os.getenv("DOCA_DOCTOR_PASSWORD", "*************"),
        "output_path": "auth_doctor.json"
    }
}


def generate_storage_state(role_key: str):
    config = ROLES[role_key]
    print(f"\n[SHIFT-LEFT AUTH] Autenticando rol '{role_key}' vía API: {config['email']}...")

    session = requests.Session()
    login_url = f"{API_URL}/login"
    payload = {"email": config["email"], "password": config["password"]}

    res = session.post(login_url, json=payload, headers={"Content-Type": "application/json"})
    
    if res.status_code != 200:
        print(f"❌ Error HTTP {res.status_code} al autenticar: {res.text}")
        return False

    body = res.json()
    token = body.get("token") or body.get("accessToken") or body.get("data", {}).get("token")
    user_data = body.get("user") or body.get("data", {}).get("user") or {}

    print(f"✅ Autenticación exitosa (HTTP 200). Generando storage_state Playwright...")

    # Cookies extraídas del backend + cookie de bypass de Vercel
    cookies = []
    for c in session.cookies:
        cookies.append({
            "name": c.name,
            "value": c.value,
            "domain": c.domain or ".techxmx.com",
            "path": c.path or "/",
            "expires": -1,
            "httpOnly": c.has_nonstandard_attr("HttpOnly"),
            "secure": c.secure,
            "sameSite": "Lax"
        })

    # Inyección de la cookie de bypass para navegación headless limpia en Vercel
    cookies.append({
        "name": "_vercel_jwt",
        "value": BYPASS_SECRET,
        "domain": ".vercel.app",
        "path": "/",
        "expires": -1,
        "httpOnly": False,
        "secure": True,
        "sameSite": "Lax"
    })

    # Almacenamiento local de la SPA
    local_storage = []
    if token:
        local_storage.append({"name": "token", "value": token})
        local_storage.append({"name": "jwt", "value": token})
    if user_data:
        local_storage.append({"name": "user", "value": json.dumps(user_data)})

    storage_state = {
        "cookies": cookies,
        "origins": [
            {
                "origin": WEB_URL,
                "localStorage": local_storage
            }
        ]
    }

    # Persistencia en disco
    target_path = os.path.join(os.getcwd(), config["output_path"])
    with open(target_path, "w", encoding="utf-8") as f:
        json.dump(storage_state, f, indent=2)

    # También guardamos auth.json genérico si es paciente
    if role_key == "patient":
        with open("auth.json", "w", encoding="utf-8") as f:
            json.dump(storage_state, f, indent=2)

    print(f"📁 Estado de sesión exportado a: {target_path}")
    return True


if __name__ == "__main__":
    generate_storage_state("patient")