"""
Pruebas unitarias para el módulo de Autenticación, JWT y Lambda Authorizer.
"""

import json
import pytest
from src.common.jwt_utils import generate_token, decode_token, AuthError
from src.auth.authorizer import handler as authorizer_handler
from src.auth.login import handler as login_handler


def test_jwt_generation_and_decode():
    """Valida la generación y decodificación correcta de un token JWT."""
    token = generate_token(user_id="usr-123", role="USUARIO", email="usr@test.com")
    payload = decode_token(token)

    assert payload["userId"] == "usr-123"
    assert payload["role"] == "USUARIO"
    assert payload["email"] == "usr@test.com"
    assert "exp" in payload


def test_jwt_expired_or_invalid():
    """Valida que un token expirado o alterado lance AuthError."""
    # Token expirado
    token_expired = generate_token(user_id="usr-123", role="USUARIO", expires_in_seconds=-10)
    with pytest.raises(AuthError) as exc_info:
        decode_token(token_expired)
    assert "expirado" in str(exc_info.value).lower()

    # Token con firma alterada
    with pytest.raises(AuthError):
        decode_token("eyJhbGciOiJIUzI1NiJ9.invalid.payload")


def test_lambda_authorizer_allow():
    """Valida que el autorizador emita una política Allow con claims en context."""
    token = generate_token(user_id="usr-999", role="OPERADOR", email="op@telecorp.com")
    event = {
        "type": "TOKEN",
        "authorizationToken": f"Bearer {token}",
        "methodArn": "arn:aws:execute-api:us-east-1:123456789012:api-id/dev/GET/incidents"
    }
    policy = authorizer_handler(event)

    assert policy["principalId"] == "usr-999"
    statements = policy["policyDocument"]["Statement"]
    assert statements[0]["Effect"] == "Allow"
    assert policy["context"]["userId"] == "usr-999"
    assert policy["context"]["role"] == "OPERADOR"


def test_lambda_authorizer_deny_on_invalid_token():
    """Valida que el autorizador emita Deny ante token inválido o ausente."""
    # Sin token
    policy_no_token = authorizer_handler({"methodArn": "arn:..."})
    assert policy_no_token["policyDocument"]["Statement"][0]["Effect"] == "Deny"

    # Token corrupto
    policy_bad_token = authorizer_handler({
        "authorizationToken": "Bearer bad-token",
        "methodArn": "arn:..."
    })
    assert policy_bad_token["policyDocument"]["Statement"][0]["Effect"] == "Deny"


def test_login_demo_users():
    """Valida el login exitoso de los usuarios de prueba."""
    # Cliente
    res_user = login_handler({
        "body": json.dumps({"username": "usuario@telecorp.com", "password": "user123"})
    })
    assert res_user["statusCode"] == 200
    data_user = json.loads(res_user["body"])["data"]
    assert "token" in data_user
    assert data_user["user"]["role"] == "USUARIO"

    # Operador Técnico
    res_tech = login_handler({
        "body": json.dumps({"username": "operador@telecorp.com", "password": "tech123"})
    })
    assert res_tech["statusCode"] == 200
    data_tech = json.loads(res_tech["body"])["data"]
    assert data_tech["user"]["role"] == "OPERADOR"

    # Administrador
    res_admin = login_handler({
        "body": json.dumps({"username": "admin@telecorp.com", "password": "admin123"})
    })
    assert res_admin["statusCode"] == 200
    data_admin = json.loads(res_admin["body"])["data"]
    assert data_admin["user"]["role"] == "ADMINISTRADOR"


def test_login_invalid_password():
    """Valida el rechazo ante contraseña incorrecta en cuentas demo."""
    res = login_handler({
        "body": json.dumps({"username": "admin@telecorp.com", "password": "wrongpassword"})
    })
    assert res["statusCode"] == 401

