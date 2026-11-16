"""
Pruebas unitarias para Detección de Incidentes Colectivos,
Correlación Espacio-Temporal con Antenas y Matriz de Priorización.
Cumple con RF-25 a RF-31, RF-39 a RF-43, RF-52, RF-53, RN-08, RN-10
y Secciones 8.4 y 8.6 de SPECIFICATION.md.
"""

import json
from datetime import datetime, timezone
import pytest

from src.common.models import (
    ProblemType,
    AntennaStatus,
    Priority,
    ZoneCriticality,
    calculate_incident_priority
)
from src.incidents.create import handler as create_handler
from src.antennas.ingest import handler as ingest_handler
from src.analytics.evaluate_group import evaluate_zone_collective_incidents, handler as evaluate_handler
from src.common.db import db
from src.common.sns_client import get_published_messages


def test_prioritization_matrix_rules():
    """Valida exhaustivamente la matriz de priorización P1 a P4 (Sección 8.4)."""
    # 1. Antena inhabilitada (0 GB/min) en zona crítica o alta siempre es P1
    assert calculate_incident_priority(1, ZoneCriticality.CRITICA.value, AntennaStatus.INHABILITADA.value) == Priority.P1.value
    assert calculate_incident_priority(1, ZoneCriticality.ALTA.value, AntennaStatus.INHABILITADA.value) == Priority.P1.value

    # 2. Colectivo (>= 10 usuarios)
    # En zona Crítica o Alta -> P1
    assert calculate_incident_priority(10, ZoneCriticality.CRITICA.value) == Priority.P1.value
    assert calculate_incident_priority(15, ZoneCriticality.ALTA.value) == Priority.P1.value
    # En zona Estándar -> P2
    assert calculate_incident_priority(10, ZoneCriticality.ESTANDAR.value) == Priority.P2.value
    assert calculate_incident_priority(25, ZoneCriticality.ESTANDAR.value) == Priority.P2.value

    # 3. Múltiples usuarios (5 a 9)
    # En zona Crítica -> P2
    assert calculate_incident_priority(5, ZoneCriticality.CRITICA.value) == Priority.P2.value
    assert calculate_incident_priority(9, ZoneCriticality.CRITICA.value) == Priority.P2.value
    # En zona Alta o Estándar -> P3
    assert calculate_incident_priority(7, ZoneCriticality.ESTANDAR.value) == Priority.P3.value

    # 4. Incidentes menores (2 a 4 usuarios) -> P3
    assert calculate_incident_priority(2, ZoneCriticality.ESTANDAR.value) == Priority.P3.value
    assert calculate_incident_priority(4, ZoneCriticality.CRITICA.value) == Priority.P3.value

    # 5. Aislado (1 usuario) -> P4
    assert calculate_incident_priority(1, ZoneCriticality.ESTANDAR.value) == Priority.P4.value


def test_collective_threshold_detection_and_correlation():
    """
    Simula 9 reportes (sin colectivo) y luego el 10mo reporte de usuario distinto
    para disparar el incidente colectivo y correlacionarlo con la antena caída (RN-08, RF-28).
    """
    zone_id = "ZONA-HOSP-01"  # Zona de criticidad CRITICA

    # 1. Registrar una métrica de antena CAÍDA en la zona (RF-52)
    ingest_handler({
        "body": json.dumps({
            "antenna_id": "ANT-201",
            "traffic_gb_min": 25.0,  # Menos de 60 -> CAIDA
            "zone_id": zone_id
        })
    })

    # 2. Registrar 9 usuarios diferentes en la misma zona
    for i in range(1, 10):
        create_handler({
            "body": json.dumps({
                "user_id": f"user-{i:03d}",
                "service_number": f"9000000{i:02d}",
                "problem_type": ProblemType.SIN_COBERTURA.value,
                "description": f"Falla de red usuario {i}",
                "zone_id": zone_id
            })
        })

    # Evaluar: Con 9 usuarios aún NO debe ser colectivo
    eval_9 = evaluate_zone_collective_incidents(zone_id)
    assert eval_9["isCollective"] is False
    assert eval_9["affectedUsersCount"] == 9

    # 3. Registrar el décimo (10) usuario diferente
    create_handler({
        "body": json.dumps({
            "user_id": "user-010",
            "service_number": "900000010",
            "problem_type": ProblemType.SIN_COBERTURA.value,
            "description": "Falla de red usuario 10",
            "zone_id": zone_id
        })
    })

    # Evaluar: Con 10 usuarios se alcanza el umbral de incidente colectivo (RN-08)
    eval_10 = evaluate_zone_collective_incidents(zone_id)
    assert eval_10["isCollective"] is True
    assert eval_10["affectedUsersCount"] == 10
    # Al ser zona crítica con >= 10 usuarios, la prioridad debe ser P1
    assert eval_10["priority"] == Priority.P1.value
    # Correlación con antena ANT-201 caída
    assert eval_10["rootCauseConfirmed"] is True
    assert eval_10["relatedAntennaId"] == "ANT-201"
    assert eval_10["antennaStatus"] == AntennaStatus.CAIDA.value
    assert eval_10["collectiveId"].startswith("COL#")

    # 4. Verificar que las incidencias individuales fueron vinculadas al collective_id (RF-31)
    individual_reports = db.query_incidents_by_zone(zone_id)
    for rep in individual_reports:
        assert rep.get("collective_id") == eval_10["collectiveId"]


def test_duplicate_user_reports_count_once():
    """Valida que múltiples reportes del mismo usuario en la misma zona cuenten como 1 solo (RF-27)."""
    zone_id = "ZONA-SUR-01"

    # El mismo usuario envía 5 reportes
    for i in range(5):
        create_handler({
            "body": json.dumps({
                "user_id": "user-recurrent-same",
                "service_number": "911911911",
                "problem_type": ProblemType.INTERNET_LENTO.value,
                "description": f"Reclamo repetido {i}",
                "zone_id": zone_id
            })
        })

    eval_res = evaluate_zone_collective_incidents(zone_id)
    assert eval_res["affectedUsersCount"] == 1
    assert eval_res["isCollective"] is False

