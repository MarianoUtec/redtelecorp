"""
Servicio de Listado y Búsqueda de Incidencias con Filtros
GET /incidents
Permite a personal operativo y administradores consultar, filtrar y ordenar
los reportes registrados (RF-18, RF-19, RF-43).
"""

from typing import Dict, Any
try:
    from src.common.response import success, forbidden, server_error
    from src.common.db import db
    from src.common.models import UserRole
except ImportError:
    from common.response import success, forbidden, server_error
    from common.db import db
    from common.models import UserRole


def handler(event: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
    """Lista las incidencias registradas con soporte de filtros."""
    try:
        auth_context = event.get("requestContext", {}).get("authorizer", {})
        user_role = auth_context.get("role", UserRole.OPERADOR.value)

        # Si el usuario es de rol USUARIO, redirigir a sus propios reportes
        if user_role == UserRole.USUARIO.value:
            jwt_user_id = auth_context.get("userId")
            if jwt_user_id:
                incidents = db.query_incidents_by_user(jwt_user_id)
                return success({"total": len(incidents), "incidents": incidents})

        params = event.get("queryStringParameters") or {}
        zone_id = params.get("zone_id")
        status = params.get("status")
        problem_type = params.get("problem_type")

        incidents = db.list_all_incidents(
            zone_id=zone_id,
            status=status,
            problem_type=problem_type
        )

        return success({
            "total": len(incidents),
            "filters": {
                "zone_id": zone_id,
                "status": status,
                "problem_type": problem_type
            },
            "incidents": incidents
        })

    except Exception as e:
        return server_error(f"Error al listar incidencias: {str(e)}")

