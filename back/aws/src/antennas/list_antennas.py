"""
Servicio de Consulta del Estado y Métricas de Antenas
GET /antennas y GET /antennas/{id}/metrics
Permite a supervisores y personal de red monitorear la salud de la infraestructura,
anomalías activas y evaluar alertas estructurales (RF-07, RF-08, RF-45, ESP-01).
"""

from typing import Dict, Any, List
try:
    from src.common.response import success, not_found, server_error
    from src.common.zones import ZONES_CATALOG, ANTENNA_TO_ZONE
    from src.common.models import evaluate_structural_failure, AntennaStatus
    from src.common.db import db
except ImportError:
    from common.response import success, not_found, server_error
    from common.zones import ZONES_CATALOG, ANTENNA_TO_ZONE
    from common.models import evaluate_structural_failure, AntennaStatus
    from common.db import db


def handler(event: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
    """Maneja listado de antenas y consulta de métricas por antena."""
    try:
        path_params = event.get("pathParameters") or {}
        antenna_id = path_params.get("id")

        # Caso 1: Consulta del historial de una antena específica
        if antenna_id:
            ant_clean = antenna_id.upper()
            metrics = db.query_metrics_by_antenna(ant_clean, limit=100)
            structural = evaluate_structural_failure(metrics)
            zone_id = ANTENNA_TO_ZONE.get(ant_clean)

            return success({
                "antenna_id": ant_clean,
                "zone_id": zone_id,
                "total_records": len(metrics),
                "structural_health": structural,
                "metrics": metrics
            })

        # Caso 2: Listado consolidado de todas las antenas
        # Se combinan las antenas del catálogo y las métricas más recientes
        known_antennas = set(ANTENNA_TO_ZONE.keys())
        all_metrics = db.list_all_metrics()

        # Agrupar métricas por antena para encontrar la más reciente
        latest_by_ant: Dict[str, Dict[str, Any]] = {}
        for m in all_metrics:
            a_id = m.get("antenna_id")
            if not a_id:
                continue
            known_antennas.add(a_id)
            if a_id not in latest_by_ant or m.get("timestamp", "") > latest_by_ant[a_id].get("timestamp", ""):
                latest_by_ant[a_id] = m

        antennas_summary: List[Dict[str, Any]] = []

        for a_id in sorted(known_antennas):
            latest = latest_by_ant.get(a_id)
            history = db.query_metrics_by_antenna(a_id, limit=50)
            structural = evaluate_structural_failure(history)
            assigned_zone = ANTENNA_TO_ZONE.get(a_id) or (latest.get("zone_id") if latest else None)

            current_status = latest.get("status") if latest else AntennaStatus.NORMAL.value
            current_traffic = latest.get("traffic_gb_min") if latest else None
            last_reading = latest.get("timestamp") if latest else None

            antennas_summary.append({
                "antenna_id": a_id,
                "zone_id": assigned_zone,
                "status": current_status,
                "current_traffic_gb_min": current_traffic,
                "last_reading": last_reading,
                "structural_failure_alert": structural.get("structural_failure_alert", False),
                "reasons": structural.get("reasons", [])
            })

        return success({
            "total_antennas": len(antennas_summary),
            "antennas": antennas_summary
        })

    except Exception as e:
        return server_error(f"Error al consultar información de antenas: {str(e)}")

