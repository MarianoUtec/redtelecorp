"""
Pruebas unitarias para el módulo de Incidencias de Usuarios.
Cumple con RF-10 a RF-24, RN-05 a RN-07 de SPECIFICATION.md.
"""

import json
import pytest

from src.common.models import IncidentStatus, ProblemType
from src.incidents.create import handler as create_handler
from src.incidents.get_by_user import handler as get_by_user_handler
from src.incidents.get_incident import handler as get_incident_handler
from src.incidents.list_incidents import handler as list_incidents_handler
from src.incidents.update_status import handler as update_status_handler
from src.common.sns_client import get_published_messages


def test_create_incident_success():
    """Valida la creación exitosa de una incidencia con código único y notificación."""
    event = {
        "requestContext": {
            "authorizer": {
                "userId": "usr-001",
                "email": "carlos@telecorp.com"
            }
        },
        "body": json.dumps({
            "service_number": "+51999111222",
            "problem_type": ProblemType.SIN_COBERTURA.value,
            "description": "Sin señal de red desde hace 2 horas en el distrito",
            "zone_id": "ZONA-SUR-01"
        })
    }

    res = create_handler(event)
    assert res["statusCode"] == 201

    body = json.loads(res["body"])["data"]
    assert body["incident_id"].startswith("INC#")
    assert body["status"] == IncidentStatus.REGISTRADA.value
    assert body["user_id"] == "usr-001"
    assert body["zone_id"] == "ZONA-SUR-01"
    assert len(body["history"]) == 1
    assert body["history"][0]["to_status"] == IncidentStatus.REGISTRADA.value

    # Verificar notificaciones despachadas a SNS
    msgs = get_published_messages()
    user_notifs = [m for m in msgs if m["message"].get("event") == "TICKET_CREATED"]
    assert len(user_notifs) == 1
    assert user_notifs[0]["message"]["incident_id"] == body["incident_id"]


def test_create_incident_validation_errors():
    """Valida el rechazo de peticiones con datos incompletos o inválidos."""
    # Falta número de teléfono / servicio
    res_no_phone = create_handler({
        "body": json.dumps({
            "user_id": "usr-1",
            "problem_type": ProblemType.SIN_COBERTURA.value,
            "description": "Test"
        })
    })
    assert res_no_phone["statusCode"] == 400

    # Tipo de problema no perteneciente al catálogo estandarizado
    res_bad_type = create_handler({
        "body": json.dumps({
            "user_id": "usr-1",
            "service_number": "999888777",
            "problem_type": "PROBLEMA_INVENTADO",
            "description": "Test"
        })
    })
    assert res_bad_type["statusCode"] == 400


def test_get_incidents_by_user():
    """Valida la consulta de incidencias reportadas por el usuario."""
    # Crear dos incidencias para el usuario
    for i in range(2):
        create_handler({
            "requestContext": {"authorizer": {"userId": "usr-client-A"}},
            "body": json.dumps({
                "service_number": "987654321",
                "problem_type": ProblemType.INTERNET_LENTO.value,
                "description": f"Reporte {i}",
                "zone_id": "ZONA-CENTRO-01"
            })
        })

    event = {
        "requestContext": {
            "authorizer": {
                "userId": "usr-client-A",
                "role": "USUARIO"
            }
        }
    }
    res = get_by_user_handler(event)
    assert res["statusCode"] == 200
    data = json.loads(res["body"])["data"]
    assert data["total"] == 2
    assert len(data["incidents"]) == 2


def test_update_incident_status_and_history():
    """Valida el ciclo de vida de estados, trazabilidad e historial (RN-06, RN-07)."""
    # 1. Crear incidencia inicial
    create_res = create_handler({
        "body": json.dumps({
            "user_id": "usr-test-lifecycle",
            "service_number": "911222333",
            "problem_type": ProblemType.FALLA_LLAMADAS.value,
            "description": "Llamadas se cortan",
            "zone_id": "ZONA-NORTE-01"
        })
    })
    inc_data = json.loads(create_res["body"])["data"]
    inc_id = inc_data["incident_id"]

    # 2. Transición válida: REGISTRADA -> EN_REVISION (por Operador)
    patch_res_1 = update_status_handler({
        "pathParameters": {"id": inc_id},
        "queryStringParameters": {"zone_id": "ZONA-NORTE-01"},
        "requestContext": {"authorizer": {"userId": "tech-01", "role": "OPERADOR"}},
        "body": json.dumps({
            "status": IncidentStatus.EN_REVISION.value,
            "note": "Asignado a cuadrilla técnica de campo"
        })
    })
    assert patch_res_1["statusCode"] == 200
    updated_1 = json.loads(patch_res_1["body"])["data"]
    assert updated_1["status"] == IncidentStatus.EN_REVISION.value
    assert len(updated_1["history"]) == 2

    # 3. Transición no permitida: EN_REVISION -> REGISTRADA (invalida retroceso)
    patch_res_invalid = update_status_handler({
        "pathParameters": {"id": inc_id},
        "queryStringParameters": {"zone_id": "ZONA-NORTE-01"},
        "requestContext": {"authorizer": {"userId": "tech-01", "role": "OPERADOR"}},
        "body": json.dumps({"status": IncidentStatus.REGISTRADA.value})
    })
    assert patch_res_invalid["statusCode"] == 400

    # 4. Transición a SOLUCIONADA
    patch_res_2 = update_status_handler({
        "pathParameters": {"id": inc_id},
        "queryStringParameters": {"zone_id": "ZONA-NORTE-01"},
        "requestContext": {"authorizer": {"userId": "tech-01", "role": "OPERADOR"}},
        "body": json.dumps({
            "status": IncidentStatus.SOLUCIONADA.value,
            "note": "Reemplazo de módulo transceptor exitoso"
        })
    })
    assert patch_res_2["statusCode"] == 200

    # Verificar que se emitió notificación de restablecimiento
    msgs = get_published_messages()
    restore_notifs = [m for m in msgs if m["message"].get("event") == "SERVICE_RESTORED"]
    assert len(restore_notifs) == 1

