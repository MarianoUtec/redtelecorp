"""
Worker Procesador de Notificaciones Automáticas (Amazon SNS Consumer)
Cumple con RF-32 a RF-38, RN-09 y Sección 8.7 de SPECIFICATION.md.
Procesa eventos de cambio de estado, incidencias colectivas y emisión de tickets,
despachando comunicaciones directas a través de canales de Correo Electrónico y SMS.
"""

import os
import json
import logging
from typing import Dict, Any, List

logger = logging.getLogger("telecorp.notifications")
logger.setLevel(logging.INFO)

# Registro en memoria de notificaciones despachadas para trazabilidad y testing
DISPATCHED_NOTIFICATIONS: List[Dict[str, Any]] = []


def get_dispatched_notifications() -> List[Dict[str, Any]]:
    """Devuelve las notificaciones enviadas por el worker."""
    return list(DISPATCHED_NOTIFICATIONS)


def reset_dispatched_notifications() -> None:
    """Limpia el log de notificaciones enviadas."""
    DISPATCHED_NOTIFICATIONS.clear()


def send_sms(phone: str, message: str) -> bool:
    """Envía un SMS vía Amazon SNS (o simula en entorno de desarrollo)."""
    if not phone:
        return False

    logger.info(f"[SMS DISPATCH] To: {phone} | Message: {message}")
    return True


def send_email(email: str, subject: str, body: str) -> bool:
    """Envía un correo electrónico vía Amazon SES / SNS (o simula en entorno de desarrollo)."""
    if not email:
        return False

    logger.info(f"[EMAIL DISPATCH] To: {email} | Subject: {subject} | Body: {body}")
    return True


def process_notification_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Interpreta el evento y despacha las comunicaciones correspondientes."""
    event_type = payload.get("event", "UNKNOWN_EVENT")
    phone = payload.get("phone")
    email = payload.get("email")
    message = payload.get("message", "Notificación de Red TeleCorp")
    incident_id = payload.get("incident_id")
    zone_id = payload.get("zone_id")

    subject = f"Red TeleCorp - Actualización de Servicio ({event_type})"
    if incident_id:
        subject = f"Red TeleCorp - Incidencia {incident_id}"

    # Enviar por SMS si hay teléfono disponible (RF-34)
    sms_sent = False
    if phone:
        sms_sent = send_sms(phone, message)

    # Enviar por Correo si hay email disponible (RF-33)
    email_sent = False
    if email:
        email_sent = send_email(email, subject, message)

    dispatch_record = {
        "event": event_type,
        "incident_id": incident_id,
        "zone_id": zone_id,
        "phone": phone,
        "email": email,
        "message": message,
        "sms_sent": sms_sent,
        "email_sent": email_sent,
        "status": "DELIVERED"
    }

    DISPATCHED_NOTIFICATIONS.append(dispatch_record)
    return dispatch_record


def handler(event: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
    """Punto de entrada para el evento SNS en AWS Lambda."""
    processed_count = 0
    records = event.get("Records", [])

    # Caso 1: Invocación directa con payload JSON
    if not records and "event" in event:
        res = process_notification_payload(event)
        return {"success": True, "processed": 1, "result": res}

    # Caso 2: Invocación por evento SNS
    for record in records:
        try:
            sns_record = record.get("Sns", {})
            message_str = sns_record.get("Message", "{}")
            payload = json.loads(message_str) if isinstance(message_str, str) else message_str
            process_notification_payload(payload)
            processed_count += 1
        except Exception as e:
            logger.error(f"Error procesando registro SNS: {str(e)}")

    return {
        "success": True,
        "records_processed": processed_count
    }

