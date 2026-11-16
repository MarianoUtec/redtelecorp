"""
Servicio de Registro de Incidencias de Usuarios
POST /incidents
Cumple con RF-10 a RF-20, RN-05 a RN-07, Sección 8.2 y 8.3 de SPECIFICATION.md.
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Dict, Any

try:
    from src.common.response import created, bad_request, server_error
    from src.common.models import IncidentStatus, ProblemType
    from src.common.zones import resolve_zone, get_zone
    from src.common.db import db
    from src.common.sns_client import sns
except ImportError:
    from common.response import created, bad_request, server_error
    from common.models import IncidentStatus, ProblemType
    from common.zones import resolve_zone, get_zone
    from common.db import db
    from common.sns_client import sns


def handler(event: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
    """Maneja la creación de una incidencia individual."""
    try:
        # Extraer identidad desde el autorizador JWT si está presente
        auth_context = event.get("requestContext", {}).get("authorizer", {})
        jwt_user_id = auth_context.get("userId")
        jwt_email = auth_context.get("email")

        body_raw = event.get("body")
        if not body_raw:
            return bad_request("El cuerpo de la petición no puede estar vacío")

        body = json.loads(body_raw) if isinstance(body_raw, str) else body_raw

        user_id = jwt_user_id or body.get("user_id") or body.get("identification")
        if not user_id:
            return bad_request("La identificación del usuario ('user_id') es obligatoria (RF-11)")

        phone = body.get("phone") or body.get("service_number")
        if not phone:
            return bad_request("El número asociado al servicio ('phone' o 'service_number') es obligatorio (RF-12)")

        email = body.get("email") or jwt_email or f"{user_id}@telecorp-cliente.com"

        problem_type = body.get("problem_type")
        valid_problems = [p.value for p in ProblemType]
        if not problem_type or problem_type not in valid_problems:
            return bad_request(
                f"El tipo de problema '{problem_type}' es inválido (RF-15). Debe ser uno de: {valid_problems}"
            )

        description = body.get("description", "").strip()
        if not description:
            return bad_request("La descripción del inconveniente es obligatoria (RF-16)")

        # Ubicación aproximada (RF-13 y Sección 8.2)
        lat = body.get("latitude") or body.get("lat")
        lng = body.get("longitude") or body.get("lng")
        zone_id = resolve_zone(lat=lat, lng=lng, provided_zone_id=body.get("zone_id"))

        # Fechas y código único (RF-14 y RF-17)
        now_dt = datetime.now(timezone.utc)
        now_iso = now_dt.isoformat()
        date_prefix = now_dt.strftime("%Y%m%d")
        short_id = uuid.uuid4().hex[:6].upper()
        incident_id = f"INC#{date_prefix}-{short_id}"

        # Historial cronológico inicial (RF-20, RF-24)
        initial_history = [
            {
                "from_status": None,
                "to_status": IncidentStatus.REGISTRADA.value,
                "timestamp": now_iso,
                "author": user_id,
                "note": "Incidencia registrada exitosamente por el usuario en el portal."
            }
        ]

        incident_item: Dict[str, Any] = {
            "zone_id": zone_id,
            "incident_id": incident_id,
            "user_id": user_id,
            "phone": str(phone),
            "email": str(email),
            "problem_type": problem_type,
            "description": description,
            "status": IncidentStatus.REGISTRADA.value,
            "collective_id": None,
            "latitude": float(lat) if lat is not None else None,
            "longitude": float(lng) if lng is not None else None,
            "created_at": now_iso,
            "updated_at": now_iso,
            "history": initial_history
        }

        # Guardar en DynamoDB (RF-10, RN-05)
        db.put_incident(incident_item)

        # Publicar evento de alta de incidencia en SNS (Sección 3.3)
        sns.publish_incident_event({
            "event": "INCIDENT_CREATED",
            "incident_id": incident_id,
            "zone_id": zone_id,
            "user_id": user_id,
            "problem_type": problem_type,
            "timestamp": now_iso
        })

        # Notificación automática de confirmación de ticket al usuario (RF-32, RF-33, RF-34, Sección 8.7)
        sns.publish_user_notification({
            "event": "TICKET_CREATED",
            "incident_id": incident_id,
            "user_id": user_id,
            "phone": str(phone),
            "email": str(email),
            "zone_id": zone_id,
            "status": IncidentStatus.REGISTRADA.value,
            "message": f"Red TeleCorp: Su incidencia {incident_id} ha sido registrada. Nuestro equipo técnico la está evaluando. Zona: {zone_id}."
        })

        # Evaluación reactiva de umbral de incidente colectivo en la zona
        try:
            try:
                from src.analytics.evaluate_group import evaluate_zone_collective_incidents
            except ImportError:
                from analytics.evaluate_group import evaluate_zone_collective_incidents
            evaluate_zone_collective_incidents(zone_id)
        except Exception:
            # La evaluación reactiva es desacoplada y no debe interrumpir la respuesta del POST
            pass

        return created(incident_item)

    except json.JSONDecodeError:
        return bad_request("El cuerpo de la petición contiene un JSON inválido")
    except Exception as e:
        return server_error(f"Error al registrar la incidencia: {str(e)}")

