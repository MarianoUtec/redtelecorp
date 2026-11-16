"""
Lambda Authorizer en Python para AWS API Gateway
Valida tokens JWT de forma stateless y emite políticas IAM dinámicas (Allow/Deny)
con contexto inyectado (userId, role, email) para los microservicios aguas abajo.
Referencia: Sección 8.1 de SPECIFICATION.md y Sección 3.1 de ARCHITECTURE.md.
"""

from typing import Dict, Any
try:
    from src.common.jwt_utils import decode_token, AuthError
except ImportError:
    from common.jwt_utils import decode_token, AuthError


def generate_policy(
    principal_id: str,
    effect: str,
    resource: str,
    context: Dict[str, Any] = None
) -> Dict[str, Any]:
    """Genera la política IAM requerida por API Gateway."""
    # Para permitir invocar cualquier método del API en este stage si se pasa un arn específico
    resource_arn = resource
    if resource and "/" in resource:
        parts = resource.split("/")
        # arn:aws:execute-api:region:account:apiId/stage/*/*
        if len(parts) >= 2:
            resource_arn = f"{parts[0]}/{parts[1]}/*/*"

    policy: Dict[str, Any] = {
        "principalId": principal_id,
        "policyDocument": {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Action": "execute-api:Invoke",
                    "Effect": effect,
                    "Resource": resource_arn
                }
            ]
        }
    }

    if context:
        # Los valores en context deben ser primitivos (str, int, bool)
        policy["context"] = {
            str(k): str(v) for k, v in context.items()
        }

    return policy


def handler(event: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
    """
    Punto de entrada del Lambda Authorizer.
    Compatible con formato TOKEN (event['authorizationToken'])
    y formato REQUEST (event['headers']['Authorization']).
    """
    token = None
    method_arn = event.get("methodArn", "*")

    # Extraer token según tipo de autorizador
    if "authorizationToken" in event:
        token = event.get("authorizationToken")
    elif "headers" in event and event["headers"]:
        headers = event["headers"]
        token = headers.get("Authorization") or headers.get("authorization")

    if not token:
        # Denegar si no hay token
        return generate_policy("anonymous", "Deny", method_arn)

    try:
        payload = decode_token(token)
        principal_id = payload.get("userId") or payload.get("sub", "user")

        auth_context = {
            "userId": principal_id,
            "role": payload.get("role", "USUARIO"),
            "email": payload.get("email", "")
        }

        return generate_policy(principal_id, "Allow", method_arn, auth_context)

    except AuthError:
        return generate_policy("unauthorized", "Deny", method_arn)
    except Exception:
        return generate_policy("error", "Deny", method_arn)

