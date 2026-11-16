"""
Cliente de mensajería Pub/Sub con Amazon SNS para Red TeleCorp.
Publica eventos de incidencias, notificaciones automáticas y alertas operativas.
Incluye emulación en memoria para pruebas locales offline.
"""

import os
import json
from typing import Dict, Any, List, Optional
try:
    from src.common.response import json_dumps
    from src.common.db import is_mock_active
except ImportError:
    from common.response import json_dumps
    from common.db import is_mock_active

INCIDENTS_TOPIC_ARN = os.environ.get("INCIDENTS_SNS_TOPIC_ARN", "arn:aws:sns:us-east-1:123456789012:telecorp-incident-events-dev")
NOTIFICATIONS_TOPIC_ARN = os.environ.get("NOTIFICATIONS_SNS_TOPIC_ARN", "arn:aws:sns:us-east-1:123456789012:telecorp-user-notifications-dev")
COLLECTIVE_ALERTS_TOPIC_ARN = os.environ.get("COLLECTIVE_ALERTS_TOPIC_ARN", "arn:aws:sns:us-east-1:123456789012:telecorp-collective-alerts-dev")

# Historial de mensajes publicados para auditoría y aserciones de tests
_PUBLISHED_MESSAGES: List[Dict[str, Any]] = []


def reset_published_messages() -> None:
    """Limpia el registro de mensajes mock."""
    _PUBLISHED_MESSAGES.clear()


def get_published_messages() -> List[Dict[str, Any]]:
    """Devuelve los mensajes publicados en modo mock."""
    return list(_PUBLISHED_MESSAGES)


class SnsClient:
    """Cliente unificado para interactuar con Amazon SNS."""

    def __init__(self):
        self._sns = None
        if not is_mock_active():
            try:
                import boto3
                region = os.environ.get("AWS_REGION", "us-east-1")
                self._sns = boto3.client("sns", region_name=region)
            except Exception:
                self._sns = None

    def publish(
        self,
        topic_arn: str,
        message: Dict[str, Any],
        subject: Optional[str] = None
    ) -> Dict[str, Any]:
        """Publica un mensaje JSON en un tema SNS."""
        message_str = json_dumps(message)
        subj = subject or message.get("event", "TELECORP_EVENT")

        # Siempre guardar en buffer local para trazabilidad y testing
        record = {
            "topic_arn": topic_arn,
            "subject": subj,
            "message": message,
            "raw_message": message_str
        }
        _PUBLISHED_MESSAGES.append(record)

        if self._sns and topic_arn and not topic_arn.startswith("arn:aws:sns:us-east-1:123456789012"):
            try:
                response = self._sns.publish(
                    TopicArn=topic_arn,
                    Message=message_str,
                    Subject=subj[:100]
                )
                record["MessageId"] = response.get("MessageId")
                return response
            except Exception as e:
                # Loggear y continuar para evitar caídas críticas si SNS falla
                record["error"] = str(e)
                return {"MessageId": "mock-fallback-id", "error": str(e)}

        return {"MessageId": f"mock-msg-{len(_PUBLISHED_MESSAGES)}"}

    def publish_incident_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Publica un evento en el bus de incidentes (disparador de orquestación)."""
        return self.publish(
            topic_arn=INCIDENTS_TOPIC_ARN,
            message=event_data,
            subject=f"INCIDENT_EVENT: {event_data.get('event', 'NEW')}"
        )

    def publish_user_notification(self, notification_data: Dict[str, Any]) -> Dict[str, Any]:
        """Publica una notificación dirigida a usuarios afectados."""
        return self.publish(
            topic_arn=NOTIFICATIONS_TOPIC_ARN,
            message=notification_data,
            subject=f"USER_NOTIFICATION: {notification_data.get('event', 'UPDATE')}"
        )

    def publish_collective_alert(self, alert_data: Dict[str, Any]) -> Dict[str, Any]:
        """Publica una alerta operativa para personal técnico / soporte."""
        return self.publish(
            topic_arn=COLLECTIVE_ALERTS_TOPIC_ARN,
            message=alert_data,
            subject=f"COLLECTIVE_ALERT: {alert_data.get('event', 'ALERT')}"
        )


# Instancia singleton
sns = SnsClient()

