"""
Servicio de Actualización de Estado e Historial de Incidencias
PATCH /incidents/{id}/status
Cumple con RF-19, RF-21, RF-23, RF-24, RN-06, RN-07 y Sección 8.7 de SPECIFICATION.md.
"""

import json
from datetime import datetime, timezone
from typing import Dict, Any
from urllib.parse import unquote

try:
    from src.common.response import success, bad_request, not_found, forbidden, server_error
    from src.common.models import IncidentStatus, UserRole
    from src.common.db import db
    from src.common.sns_client import sns
except ImportError:
    from common.response import success, bad_request, not_found, forbidden, server_error
    from common.models import IncidentStatus, UserRole
    from common.db import db
    from common.sns_client import sns


def handler(event: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
    """Maneja cambios de estado y registro histórico de incidencias."""
    try:
        path_params = event.get("pathParameters") or {}
        incident_id = unquote(path_params.get("id") or "")
        if not incident_id:
            return bad_request("El parámetro 'id' es obligatorio")

        body_raw = event.get("body")
        if not body_raw:
            return bad_request("El cuerpo de la petición no puede estar vacío")

        body = json.loads(body_raw) if isinstance(body_raw, str) else body_raw
        new_status = body.get("status")
        note = body.get("note", "").strip()

        valid_statuses = [s.value for s in IncidentStatus]
        if not new_status or new_status not in valid_statuses:
            return bad_request(f"Estado '{new_status}' inválido. Debe ser uno de: {valid_statuses}")

        # Identidad y permisos RBAC
        auth_context = event.get("requestContext", {}).get("authorizer", {})
        requester_id = auth_context.get("userId", "operador-sistema")
        requester_role = auth_context.get("role", UserRole.OPERADOR.value)

        # Buscar la incidencia actual
        query_params = event.get("queryStringParameters") or {}
        zone_id = query_params.get("zone_id")
        incident = db.get_incident(incident_id, zone_id=zone_id)

        if not incident:
            return not_found(f"Incidencia con ID '{incident_id}' no encontrada")

        current_status = incident.get("status", IncidentStatus.REGISTRADA.value)
        actual_zone_id = incident.get("zone_id")

        # Validación de permisos: un usuario sólo puede cerrar una incidencia ya solucionada
        if requester_role == UserRole.USUARIO.value:
            if incident.get("user_id") != requester_id:
                return forbidden("No tiene permiso para modificar esta incidencia")
            if current_status != IncidentStatus.SOLUCIONADA.value or new_status != IncidentStatus.CERRADA.value:
                return forbidden("Los usuarios únicamente pueden confirmar y cerrar incidencias solucionadas")

        # Validación de flujo de estados (RN-06)
        if not IncidentStatus.is_valid_transition(current_status, new_status):
            return bad_request(
                f"Transición de estado no permitida: de '{current_status}' a '{new_status}'"
            )

        now_iso = datetime.now(timezone.utc).isoformat()

        # Construir entrada para historial cronológico (RF-23, RF-24, RN-07)
        history_entry = {
            "from_status": current_status,
            "to_status": new_status,
            "timestamp": now_iso,
            "author": requester_id,
            "role": requester_role,
            "note": note or f"Cambio de estado de {current_status} a {new_status}"
        }

        updated_history = incident.get("history", [])
        updated_history.append(history_entry)

        updates = {
            "status": new_status,
            "updated_at": now_iso,
            "history": updated_history
        }

        updated_incident = db.update_incident_record(actual_zone_id, incident_id, updates)

        # Notificación automática al usuario afectado (RF-35 a RF-38, RN-09)
        event_name = "STATUS_UPDATED"
        notif_msg = f"Red TeleCorp: Su incidencia {incident_id} ha cambiado de estado a: {new_status}."

        if new_status == IncidentStatus.SOLUCIONADA.value:
            event_name = "SERVICE_RESTORED"
            notif_msg = f"Red TeleCorp: El servicio ha sido restablecido. Su incidencia {incident_id} ha sido marcada como SOLUCIONADA."
        elif new_status == IncidentStatus.EN_REVISION.value:
            notif_msg = f"Red TeleCorp: Su inconveniente {incident_id} está siendo evaluado por nuestros especialistas."
        elif new_status == IncidentStatus.SIENDO_ATENDIDA.value:
            notif_msg = f"Red TeleCorp: Nuestro personal técnico se encuentra atendiendo la incidencia {incident_id} en su sector."

        sns.publish_user_notification({
            "event": event_name,
            "incident_id": incident_id,
            "user_id": incident.get("user_id"),
            "old_status": current_status,
            "new_status": new_status,
            "phone": incident.get("phone"),
            "email": incident.get("email"),
            "zone_id": actual_zone_id,
            "message": notif_msg
        })

        return success(updated_incident or updates)

    except json.JSONDecodeError:
        return bad_request("El cuerpo de la petición contiene un JSON inválido")
    except Exception as e:
        return server_error(f"Error al actualizar estado de la incidencia: {str(e)}")

