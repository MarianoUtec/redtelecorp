"""
Formateador estándar de respuestas HTTP para AWS API Gateway
con soporte CORS y serialización de tipos DynamoDB (Decimal, datetime).
"""

import json
from decimal import Decimal
from datetime import datetime, date
from typing import Any, Dict, Optional


class CustomJSONEncoder(json.JSONEncoder):
    """Encoder JSON que maneja tipos comunes de DynamoDB y Python estándar."""
    def default(self, obj: Any) -> Any:
        if isinstance(obj, Decimal):
            # Si no tiene decimales, convertir a int, de lo contrario float
            if obj % 1 == 0:
                return int(obj)
            return float(obj)
        elif isinstance(obj, (datetime, date)):
            return obj.isoformat()
        elif isinstance(obj, set):
            return list(obj)
        return super().default(obj)


def json_dumps(data: Any) -> str:
    """Serializa un objeto a JSON utilizando el encoder personalizado."""
    return json.dumps(data, cls=CustomJSONEncoder, ensure_ascii=False)


def build_response(
    status_code: int,
    body: Any,
    headers: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """Construye un diccionario de respuesta compatible con API Gateway."""
    default_headers = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Credentials": "true",
        "Access-Control-Allow-Methods": "GET,POST,PUT,PATCH,DELETE,OPTIONS",
        "Access-Control-Allow-Headers": "Authorization,Content-Type,X-Amz-Date,X-Api-Key,X-Amz-Security-Token"
    }
    if headers:
        default_headers.update(headers)

    body_str = json_dumps(body) if not isinstance(body, str) else body

    return {
        "statusCode": status_code,
        "headers": default_headers,
        "body": body_str
    }


def success(data: Any, status_code: int = 200) -> Dict[str, Any]:
    """Respuesta exitosa estándar."""
    return build_response(status_code, {"success": True, "data": data})


def created(data: Any) -> Dict[str, Any]:
    """Respuesta 201 Created."""
    return build_response(201, {"success": True, "data": data})


def error(message: str, status_code: int = 400, details: Any = None) -> Dict[str, Any]:
    """Respuesta de error con código HTTP y mensaje explicativo."""
    body = {
        "success": False,
        "error": {
            "code": status_code,
            "message": message
        }
    }
    if details is not None:
        body["error"]["details"] = details
    return build_response(status_code, body)


def bad_request(message: str = "Solicitud incorrecta", details: Any = None) -> Dict[str, Any]:
    return error(message, 400, details)


def unauthorized(message: str = "No autorizado", details: Any = None) -> Dict[str, Any]:
    return error(message, 401, details)


def forbidden(message: str = "Acceso denegado", details: Any = None) -> Dict[str, Any]:
    return error(message, 403, details)


def not_found(message: str = "Recurso no encontrado", details: Any = None) -> Dict[str, Any]:
    return error(message, 404, details)


def server_error(message: str = "Error interno del servidor", details: Any = None) -> Dict[str, Any]:
    return error(message, 500, details)

