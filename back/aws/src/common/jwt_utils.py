"""
Utilidades criptográficas para emisión y validación de tokens JWT
de acuerdo con la Sección 8.1 de SPECIFICATION.md.
"""

import os
import time
from typing import Dict, Any, Optional
import jwt

JWT_SECRET = os.environ.get("JWT_SECRET", "TelecorpSecretKey2026Jwt_SecureKey32BytesLong!")
JWT_ALGORITHM = "HS256"
DEFAULT_EXPIRATION_SECONDS = 86400 * 7  # 7 días para conveniencia en pruebas


class AuthError(Exception):
    """Excepción para errores de autenticación o validación de tokens."""
    def __init__(self, message: str, status_code: int = 401):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def generate_token(
    user_id: str,
    role: str = "USUARIO",
    email: str = "",
    expires_in_seconds: int = DEFAULT_EXPIRATION_SECONDS,
    extra_claims: Optional[Dict[str, Any]] = None
) -> str:
    """
    Genera un token JWT firmado criptográficamente con algoritmo HMAC-SHA256.
    """
    now = int(time.time())
    payload = {
        "sub": user_id,
        "userId": user_id,
        "role": role,
        "email": email,
        "iat": now,
        "exp": now + expires_in_seconds,
        "iss": "telecorp-auth-service"
    }
    if extra_claims:
        payload.update(extra_claims)

    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    # PyJWT 2+ devuelve string directamente
    return token if isinstance(token, str) else token.decode("utf-8")


def decode_token(token: str) -> Dict[str, Any]:
    """
    Decodifica y valida la firma y expiración de un token JWT.
    Lanza AuthError si el token ha expirado o tiene firma inválida.
    """
    if not token:
        raise AuthError("Token no proporcionado", 401)

    # Remover prefijo Bearer si viene incluido
    clean_token = token.strip()
    if clean_token.lower().startswith("bearer "):
        clean_token = clean_token[7:].strip()

    try:
        payload = jwt.decode(
            clean_token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM],
            options={"require": ["exp", "userId", "role"]}
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise AuthError("El token de autenticación ha expirado", 401)
    except jwt.InvalidTokenError as e:
        raise AuthError(f"Token de autenticación inválido: {str(e)}", 401)
