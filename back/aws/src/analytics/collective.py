"""
Servicio de Consulta de Incidentes Colectivos
GET /collective-events
Permite al NOC y a las cuadrillas de campo supervisar las fallas colectivas
detectadas automáticamente por la plataforma (RF-28 a RF-31).
"""

from typing import Dict, Any
try:
    from src.common.response import success, server_error
    from src.common.db import db
except ImportError:
    from common.response import success, server_error
    from common.db import db


def handler(event: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
    """Lista los incidentes colectivos activos e históricos."""
    try:
        params = event.get("queryStringParameters") or {}
        zone_id = params.get("zone_id")
        active_only = params.get("active_only", "false").lower() in ("true", "1", "yes")

        events = db.list_collective_events(zone_id=zone_id, active_only=active_only)

        return success({
            "total": len(events),
            "collective_events": events
        })

    except Exception as e:
        return server_error(f"Error al listar incidentes colectivos: {str(e)}")

