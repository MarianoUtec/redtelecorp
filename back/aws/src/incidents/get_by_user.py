"""
Servicio de Consulta de Reportes por Usuario
GET /incidents/my-reports
Cumple con RF-18, RF-22 y Sección 8.9 (RBAC) de SPECIFICATION.md.
"""

from typing import Dict, Any
try:
    from src.common.response import success, bad_request, unauthorized, server_error
    from src.common.db import db
    from src.common.models import UserRole
except ImportError:
    from common.response import success, bad_request, unauthorized, server_error
    from common.db import db
    from common.models import UserRole


def handler(event: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
    """Retorna las incidencias reportadas por el usuario autenticado."""
    try:
        auth_context = event.get("requestContext", {}).get("authorizer", {})
        jwt_user_id = auth_context.get("userId")
        user_role = auth_context.get("role", UserRole.USUARIO.value)

        # Si es operador o admin, puede consultar las de un usuario específico por query param
        params = event.get("queryStringParameters") or {}
        requested_user_id = params.get("userId") or params.get("user_id")

        if requested_user_id and user_role in (UserRole.OPERADOR.value, UserRole.ADMINISTRADOR.value):
            target_user_id = requested_user_id
        else:
            target_user_id = jwt_user_id

        if not target_user_id:
            # Fallback a parámetro si se ejecuta sin autorizador (modo pruebas o demo)
            target_user_id = params.get("userId") or params.get("user_id")

        if not target_user_id:
            return unauthorized("No se pudo determinar la identidad del usuario")

        incidents = db.query_incidents_by_user(target_user_id)

        return success({
            "userId": target_user_id,
            "total": len(incidents),
            "incidents": incidents
        })

    except Exception as e:
        return server_error(f"Error al consultar incidencias del usuario: {str(e)}")

