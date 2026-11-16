"""
Pruebas unitarias para el Worker de Notificaciones Automáticas (Amazon SNS Consumer).
Cumple con RF-32 a RF-38, RN-09 y Sección 8.7 de SPECIFICATION.md.
"""

import json
from src.notifications.worker import (
    handler as notification_worker_handler,
    get_dispatched_notifications
)


def test_notification_worker_ticket_created_event():
    """Valida el procesamiento de notificación ante creación de ticket."""
    event = {
        "Records": [
            {
                "Sns": {
                    "Message": json.dumps({
                        "event": "TICKET_CREATED",
                        "incident_id": "INC#20261115-00100",
                        "user_id": "usr-555",
                        "phone": "+51988776655",
                        "email": "cliente@telecorp.com",
                        "zone_id": "ZONA-CENTRO-01",
                        "message": "Su reporte ha sido recibido y está siendo evaluado."
                    })
                }
            }
        ]
    }

    res = notification_worker_handler(event)
    assert res["success"] is True
    assert res["records_processed"] == 1

    dispatched = get_dispatched_notifications()
    assert len(dispatched) == 1
    assert dispatched[0]["event"] == "TICKET_CREATED"
    assert dispatched[0]["sms_sent"] is True
    assert dispatched[0]["email_sent"] is True


def test_notification_worker_collective_alert():
    """Valida la difusión de aviso de incidencia colectiva a usuarios."""
    event = {
        "Records": [
            {
                "Sns": {
                    "Message": json.dumps({
                        "event": "COLLECTIVE_INCIDENT_DETECTED",
                        "zone_id": "ZONA-HOSP-01",
                        "affectedUsers": 12,
                        "priority": "P1",
                        "message": "Se ha identificado una afectación general en su sector."
                    })
                }
            }
        ]
    }

    res = notification_worker_handler(event)
    assert res["success"] is True
    assert res["records_processed"] == 1

    dispatched = get_dispatched_notifications()
    assert len(dispatched) == 1
    assert dispatched[0]["event"] == "COLLECTIVE_INCIDENT_DETECTED"

