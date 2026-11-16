"""
Endpoint de Autenticación y Emisión de Tokens JWT
POST /auth/login
Permite a usuarios, operadores técnicos y administradores autenticarse
y obtener un token JWT con sus respectivos roles y permisos RBAC.
"""

import json
import hashlib
from typing import Dict, Any
try:
    from src.common.response import success, bad_request, unauthorized, server_error
    from src.common.jwt_utils import generate_token
    from src.common.models import UserRole
except ImportError:
    from common.response import success, bad_request, unauthorized, server_error
    from common.jwt_utils import generate_token
    from common.models import UserRole

# Cuentas demo preconfiguradas para pruebas y desarrollo
PRECONFIGURED_USERS = {
    "usuario@telecorp.com": {
        "password": "user123",
        "userId": "usr-1001",
        "role": UserRole.USUARIO.value,
        "name": "Carlos Mendoza (Cliente)",
        "phone": "+51987654321"
    },
    "operador@telecorp.com": {
        "password": "tech123",
        "userId": "tech-2001",
        "role": UserRole.OPERADOR.value,
        "name": "Ing. Sofía Vargas (Operaciones de Red)",
        "phone": "+51911223344"
    },
    "admin@telecorp.com": {
        "password": "admin123",
        "userId": "adm-3001",
        "role": UserRole.ADMINISTRADOR.value,
        "name": "Administrador General NOC",
        "phone": "+51999888777"
    }
}


def handler(event: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
    """Maneja peticiones POST /auth/login."""
    try:
        body_raw = event.get("body")
        if not body_raw:
            return bad_request("El cuerpo de la solicitud no puede estar vacío")

        body = json.loads(body_raw) if isinstance(body_raw, str) else body_raw
        username = body.get("username", "").strip().lower()
        password = body.get("password", "").strip()
        requested_role = body.get("role")

        if not username:
            return bad_request("El campo 'username' o 'email' es obligatorio")

        # 1. Verificar si es un usuario preconfigurado
        if username in PRECONFIGURED_USERS:
            user_data = PRECONFIGURED_USERS[username]
            # En entorno de hackathon/demo permitimos la contraseña predefinida o cualquier password si es demo
            if password != user_data["password"]:
                return unauthorized("Credenciales incorrectas")

            user_id = user_data["userId"]
            role = user_data["role"]
            email = username
        else:
            # 2. Generación dinámica para usuarios de prueba
            user_id = body.get("userId") or f"usr-{int(hashlib.md5(username.encode()).hexdigest(), 16) % 10000:04d}"
            email = username

            # Asignar rol solicitado si es válido, o default USUARIO
            role = UserRole.USUARIO.value  # sin elevar rol

        token = generate_token(
            user_id=user_id,
            role=role,
            email=email,
            extra_claims={"name": body.get("name", username)}
        )

        return success({
            "token": token,
            "tokenType": "Bearer",
            "expiresIn": 86400 * 7,
            "user": {
                "userId": user_id,
                "email": email,
                "role": role
            }
        })

    except json.JSONDecodeError:
        return bad_request("Formato JSON inválido en el cuerpo de la petición")
    except Exception as e:
        return server_error(f"Error al procesar autenticación: {str(e)}")

