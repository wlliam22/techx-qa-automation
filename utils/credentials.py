import os
from enum import Enum
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

class UserRole(str, Enum):
    ADMIN = "admin"
    DOCTOR = "doctor"
    PATIENT = "patient"
    LAB = "lab"

@dataclass(frozen=True)
class UserCredential:
    email: str
    password: str
    role: UserRole
    auth_state_path: str

class CredentialManager:
    @staticmethod
    def get_credentials(role: UserRole) -> UserCredential:
        role_map = {
            UserRole.ADMIN: (
                os.getenv("DOCA_ADMIN_EMAIL", ""),
                os.getenv("DOCA_ADMIN_PASSWORD", ""),
            ),
            UserRole.DOCTOR: (
                os.getenv("DOCA_DOCTOR_EMAIL", ""),
                os.getenv("DOCA_DOCTOR_PASSWORD", ""),
            ),
            UserRole.PATIENT: (
                os.getenv("DOCA_PATIENT_EMAIL", ""),
                os.getenv("DOCA_PATIENT_PASSWORD", ""),
            ),
            UserRole.LAB: (
                os.getenv("DOCA_LAB_EMAIL", ""),
                os.getenv("DOCA_LAB_PASSWORD", ""),
            ),
        }

        email, password = role_map[role]
        if not email or not password:
            raise ValueError(f"Credenciales no configuradas en .env para el rol: {role.value}")

        # Archivo de sesión único por rol para evitar polución de cookies
        os.makedirs(".auth", exist_ok=True)
        auth_state_path = f".auth/state_{role.value}.json"

        return UserCredential(
            email=email,
            password=password,
            role=role,
            auth_state_path=auth_state_path
        )