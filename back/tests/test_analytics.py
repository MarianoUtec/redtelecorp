"""
Pruebas unitarias para Analítica, Resumen Ejecutivo y Eventos Colectivos.
Cumple con RF-44 a RF-51 de SPECIFICATION.md.
"""

import json
from src.common.models import ProblemType
from src.incidents.create import handler as create_handler
from src.antennas.ingest import handler as ingest_handler
from src.analytics.summary import handler as summary_handler
from src.analytics.collective import handler as collective_handler
from src.analytics.evaluate_group import evaluate_zone_collective_incidents


def test_analytics_summary_endpoints():
    """Valida la generación de estadísticas agregadas, rankings y alertas."""
    # 1. Crear algunas incidencias con diferentes problemas y zonas
    create_handler({
        "body": json.dumps({
            "user_id": "u1", "service_number": "111",
            "problem_type": ProblemType.SIN_COBERTURA.value,
            "description": "desc", "zone_id": "ZONA-CENTRO-01"
        })
    })
    create_handler({
        "body": json.dumps({
            "user_id": "u2", "service_number": "222",
            "problem_type": ProblemType.SIN_COBERTURA.value,
            "description": "desc", "zone_id": "ZONA-CENTRO-01"
        })
    })
    create_handler({
        "body": json.dumps({
            "user_id": "u3", "service_number": "333",
            "problem_type": ProblemType.INTERNET_LENTO.value,
            "description": "desc", "zone_id": "ZONA-SUR-01"
        })
    })

    # Ingestar métrica anómala
    ingest_handler({
        "body": json.dumps({"antenna_id": "ANT-101", "traffic_gb_min": 150.0, "zone_id": "ZONA-CENTRO-01"})
    })

    res = summary_handler({})
    assert res["statusCode"] == 200

    data = json.loads(res["body"])["data"]
    overview = data["overview"]
    assert overview["total_incidents"] == 3
    assert overview["total_affected_users"] == 3

    # ZONA-CENTRO-01 debe liderar el ranking por tener 2 reportes (RF-44)
    top_zone = data["zones_ranking"][0]
    assert top_zone["zone_id"] == "ZONA-CENTRO-01"
    assert top_zone["total_incidents"] == 2

    # SIN_COBERTURA debe ser el tipo de inconveniente más reportado (RF-46)
    top_problem = data["problem_types_breakdown"][0]
    assert top_problem["problem_type"] == ProblemType.SIN_COBERTURA.value
    assert top_problem["count"] == 2


def test_collective_events_listing():
    """Valida la consulta de incidentes colectivos activos."""
    # Crear 10 usuarios para generar un colectivo
    for i in range(10):
        create_handler({
            "body": json.dumps({
                "user_id": f"u-col-{i}", "service_number": f"9000{i}",
                "problem_type": ProblemType.SIN_COBERTURA.value,
                "description": "falla", "zone_id": "ZONA-IND-01"
            })
        })

    evaluate_zone_collective_incidents("ZONA-IND-01")

    res = collective_handler({"queryStringParameters": {"active_only": "true"}})
    assert res["statusCode"] == 200

    data = json.loads(res["body"])["data"]
    assert data["total"] >= 1
    col = data["collective_events"][0]
    assert col["zone_id"] == "ZONA-IND-01"
    assert col["affected_users_count"] == 10

