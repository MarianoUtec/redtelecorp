"""
Pruebas unitarias para el módulo de Antenas, Umbrales y Falla Estructural.
Cumple con RF-01 a RF-09, RN-01 a RN-04, RN-11 y Sección 8.5 de SPECIFICATION.md.
"""

import json
from datetime import datetime, timezone, timedelta
import pytest

from src.common.models import (
    AntennaStatus,
    classify_antenna_traffic,
    evaluate_structural_failure
)
from src.antennas.ingest import handler as ingest_handler
from src.antennas.list_antennas import handler as list_antennas_handler
from src.common.sns_client import get_published_messages


def test_classify_antenna_traffic_strict_thresholds():
    """Valida los umbrales exactos de clasificación de tráfico (RN-01 a RN-04)."""
    # Inhabilitada (0 GB/min)
    assert classify_antenna_traffic(0) == AntennaStatus.INHABILITADA.value
    assert classify_antenna_traffic(0.0) == AntennaStatus.INHABILITADA.value

    # Caída (< 60 GB/min, excepto 0)
    assert classify_antenna_traffic(0.1) == AntennaStatus.CAIDA.value
    assert classify_antenna_traffic(59.9) == AntennaStatus.CAIDA.value

    # Normal (60 a 129 GB/min inclusive)
    assert classify_antenna_traffic(60) == AntennaStatus.NORMAL.value
    assert classify_antenna_traffic(60.0) == AntennaStatus.NORMAL.value
    assert classify_antenna_traffic(95.5) == AntennaStatus.NORMAL.value
    assert classify_antenna_traffic(129.0) == AntennaStatus.NORMAL.value

    # Saturada (> 129 GB/min)
    assert classify_antenna_traffic(129.1) == AntennaStatus.SATURADA.value
    assert classify_antenna_traffic(250.0) == AntennaStatus.SATURADA.value

    # Error ante valores negativos o inválidos
    with pytest.raises(ValueError):
        classify_antenna_traffic(-5)


def test_ingest_antenna_metrics_api():
    """Valida el endpoint de ingesta de métricas vía POST /antennas/metrics."""
    event = {
        "body": json.dumps({
            "antenna_id": "ANT-101",
            "traffic_gb_min": 45.0,
            "zone_id": "ZONA-CENTRO-01"
        })
    }
    response = ingest_handler(event)
    assert response["statusCode"] == 201

    body = json.loads(response["body"])["data"]
    assert body["antenna_id"] == "ANT-101"
    assert body["traffic_gb_min"] == 45.0
    assert body["status"] == AntennaStatus.CAIDA.value

    # Se debe haber emitido un evento de anomalía en SNS
    messages = get_published_messages()
    assert len(messages) >= 1
    anomaly_events = [m for m in messages if m["message"].get("event") == "ANTENNA_ANOMALY_DETECTED"]
    assert len(anomaly_events) == 1
    assert anomaly_events[0]["message"]["antenna_id"] == "ANT-101"


def test_structural_failure_recurrence_criterion_a():
    """Valida la detección de falla estructural: 3 o más anomalías en 7 días (Sección 8.5)."""
    now = datetime.now(timezone.utc)
    # 3 anomalías en los últimos 4 días
    history = [
        {"timestamp": (now - timedelta(days=1)).isoformat(), "status": AntennaStatus.CAIDA.value},
        {"timestamp": (now - timedelta(days=2)).isoformat(), "status": AntennaStatus.SATURADA.value},
        {"timestamp": (now - timedelta(days=3)).isoformat(), "status": AntennaStatus.CAIDA.value},
        {"timestamp": (now - timedelta(days=4)).isoformat(), "status": AntennaStatus.NORMAL.value},
    ]
    eval_res = evaluate_structural_failure(history)
    assert eval_res["structural_failure_alert"] is True
    assert eval_res["anomalies_7d_count"] == 3


def test_structural_failure_recurrence_criterion_b():
    """Valida la detección de falla estructural: 2 caídas completas en 48 horas (Sección 8.5)."""
    now = datetime.now(timezone.utc)
    # 2 caídas en las últimas 24 horas
    history = [
        {"timestamp": (now - timedelta(hours=5)).isoformat(), "status": AntennaStatus.CAIDA.value},
        {"timestamp": (now - timedelta(hours=18)).isoformat(), "status": AntennaStatus.INHABILITADA.value},
    ]
    eval_res = evaluate_structural_failure(history)
    assert eval_res["structural_failure_alert"] is True
    assert eval_res["drops_48h_count"] == 2


def test_list_antennas_and_metrics():
    """Valida la consulta de antenas y su estado de salud."""
    # Ingestar una métrica para que aparezca en el listado
    ingest_handler({
        "body": json.dumps({"antenna_id": "ANT-201", "traffic_gb_min": 0.0})
    })

    res = list_antennas_handler({"pathParameters": None})
    assert res["statusCode"] == 200
    data = json.loads(res["body"])["data"]
    assert data["total_antennas"] >= 1

    ant_201 = next((a for a in data["antennas"] if a["antenna_id"] == "ANT-201"), None)
    assert ant_201 is not None
    assert ant_201["status"] == AntennaStatus.INHABILITADA.value

