"""
Servicio de Consulta Detallada de una Incidencia
GET /incidents/{id}
Cumple con RF-18, RF-22, RF-24 y RF-31 de SPECIFICATION.md.
"""

from typing import Dict, Any
from urllib.parse import unquote
try:
    from src.common.response import success, not_found, forbidden, bad_request, server_error
    from src.common.db import db
    from src.common.models import UserRole
except ImportError:
    from common.response import success, not_found, forbidden, bad_request, server_error
    from common.db import db
    from common.models import UserRole


def handler(event: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
    """Retorna una incidencia por su ID incluyendo historial completo y contexto colectivo."""
    try:
        path_params = event.get("pathParameters") or {}
        incident_id = unquote(path_params.get("id") or "")

        if not incident_id:
            return bad_request("El parámetro 'id' es requerido en la ruta")

        # Contexto de autorización
        auth_context = event.get("requestContext", {}).get("authorizer", {})
        jwt_user_id = auth_context.get("userId")
        user_role = auth_context.get("role", UserRole.USUARIO.value)

        # Buscar en DynamoDB
        query_params = event.get("queryStringParameters") or {}
        zone_id = query_params.get("zone_id")
        incident = db.get_incident(incident_id, zone_id=zone_id)

        if not incident:
            return not_found(f"No se encontró la incidencia con ID '{incident_id}'")

        # Validación de permisos RBAC: usuarios estándar solo ven sus propias incidencias
        if user_role == UserRole.USUARIO.value and jwt_user_id:
            if incident.get("user_id") != jwt_user_id:
                return forbidden("No tiene permisos para consultar este reporte")

        # Si está vinculada a un incidente colectivo, enriquecer respuesta (RF-31)
        collective_id = incident.get("collective_id")
        collective_info = None
        if collective_id:
            collective_info = db.get_collective_event(incident.get("zone_id", ""), collective_id)

        response_data = {
            **incident,
            "collective_details": collective_info
        }

        return success(response_data)

    except Exception as e:
        return server_error(f"Error al obtener detalle de la incidencia: {str(e)}")

