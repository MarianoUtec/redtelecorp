"""
Pruebas unitarias para el script de Sincronización Multicloud a OCI.
"""

import gzip
import json
import sys
from pathlib import Path

# Agregar carpeta oci al path
oci_dir = Path(__file__).resolve().parent.parent / "oci"
sys.path.insert(0, str(oci_dir))

from sync_history import export_history_dataset, upload_to_oci
from src.common.db import db
from src.common.models import ProblemType
from src.incidents.create import handler as create_incident_handler
from src.incidents.update_status import handler as update_status_handler
from src.antennas.ingest import handler as ingest_metric_handler


def test_oci_export_and_dry_run_archive(tmp_path):
    """Valida que el exportador a OCI empaquete incidencias y métricas en gzip válido."""
    # 1. Crear una incidencia y marcarla como SOLUCIONADA
    res_create = create_incident_handler({
        "body": json.dumps({
            "user_id": "usr-oci-1",
            "service_number": "999000111",
            "problem_type": ProblemType.INTERNET_LENTO.value,
            "description": "Falla resuelta para OCI",
            "zone_id": "ZONA-CENTRO-01"
        })
    })
    inc_data = json.loads(res_create["body"])["data"]
    inc_id = inc_data["incident_id"]

    update_status_handler({
        "pathParameters": {"id": inc_id},
        "queryStringParameters": {"zone_id": "ZONA-CENTRO-01"},
        "requestContext": {"authorizer": {"userId": "tech-1", "role": "OPERADOR"}},
        "body": json.dumps({"status": "EN_REVISION"})
    })
    update_status_handler({
        "pathParameters": {"id": inc_id},
        "queryStringParameters": {"zone_id": "ZONA-CENTRO-01"},
        "requestContext": {"authorizer": {"userId": "tech-1", "role": "OPERADOR"}},
        "body": json.dumps({"status": "SOLUCIONADA"})
    })

    # Ingestar una métrica
    ingest_metric_handler({
        "body": json.dumps({"antenna_id": "ANT-101", "traffic_gb_min": 80.0, "zone_id": "ZONA-CENTRO-01"})
    })

    # 2. Generar dataset histórico
    dataset = export_history_dataset()
    assert dataset["metadata"]["total_incidents_archived"] >= 1
    assert dataset["metadata"]["total_metrics_archived"] >= 1

    # 3. Probar subida en modo simulación (dry-run)
    result = upload_to_oci(
        data=dataset,
        bucket_name="telecorp-history-test",
        namespace="test_namespace",
        dry_run=True,
        output_dir=str(tmp_path)
    )
    assert result["status"] == "DRY_RUN_SUCCESS"

    # 4. Verificar integridad del archivo comprimido .json.gz
    created_file = Path(result["file"])
    assert created_file.exists()
    assert created_file.stat().st_size > 0

    with gzip.open(created_file, "rt", encoding="utf-8") as f:
        unpacked_data = json.load(f)

    assert unpacked_data["metadata"]["provider"] == "Oracle Cloud Infrastructure (OCI) Always Free"
    assert len(unpacked_data["incidents"]) >= 1

