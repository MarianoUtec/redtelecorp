"""
Módulo de Analítica, Estadísticas y Detección de Patrones Históricos
GET /analytics/summary
Cumple con RF-44 a RF-51, ESP-08, ESP-09 de SPECIFICATION.md.
"""

from datetime import datetime
from typing import Dict, Any, List
from collections import Counter

try:
    from src.common.response import success, server_error
    from src.common.db import db
    from src.common.models import AntennaStatus, evaluate_structural_failure
    from src.common.zones import ZONES_CATALOG, ANTENNA_TO_ZONE
except ImportError:
    from common.response import success, server_error
    from common.db import db
    from common.models import AntennaStatus, evaluate_structural_failure
    from common.zones import ZONES_CATALOG, ANTENNA_TO_ZONE


def handler(event: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
    """Genera métricas consolidadas, rankings de zonas y detección de anomalías."""
    try:
        # 1. Recuperar datos actuales
        incidents = db.list_all_incidents()
        metrics = db.list_all_metrics()
        collective_events = db.list_collective_events()

        total_incidents = len(incidents)
        unique_users = len({i.get("user_id") for i in incidents if i.get("user_id")})

        # 2. Distribución de incidencias por zona geográfica (RF-44)
        zone_counter = Counter(i.get("zone_id", "DESCONOCIDA") for i in incidents)
        zones_ranking = [
            {
                "zone_id": z,
                "name": ZONES_CATALOG.get(z, {}).get("name", z),
                "criticality": ZONES_CATALOG.get(z, {}).get("criticality", "ESTANDAR"),
                "total_incidents": count
            }
            for z, count in zone_counter.most_common()
        ]

        # 3. Distribución por tipo de inconveniente (RF-46)
        problem_counter = Counter(i.get("problem_type", "OTRO") for i in incidents)
        problems_breakdown = [
            {
                "problem_type": pt,
                "count": count,
                "percentage": round((count / total_incidents * 100), 2) if total_incidents > 0 else 0
            }
            for pt, count in problem_counter.most_common()
        ]

        # 4. Distribución por estado
        status_counter = Counter(i.get("status", "DESCONOCIDO") for i in incidents)

        # 5. Antenas con anomalías frecuentes y fallas estructurales (RF-45, RF-51, RF-55)
        anomalous_metrics = [
            m for m in metrics
            if m.get("status") in (AntennaStatus.CAIDA.value, AntennaStatus.SATURADA.value, AntennaStatus.INHABILITADA.value)
        ]
        antenna_anomaly_counter = Counter(m.get("antenna_id") for m in anomalous_metrics if m.get("antenna_id"))
        problematic_antennas = [
            {
                "antenna_id": a,
                "zone_id": ANTENNA_TO_ZONE.get(a),
                "total_anomalies": count
            }
            for a, count in antenna_anomaly_counter.most_common(10)
        ]

        # Chequeo de alertas de falla estructural activas
        structural_alerts = []
        all_antennas = set(ANTENNA_TO_ZONE.keys()).union(set(m.get("antenna_id") for m in metrics if m.get("antenna_id")))
        for ant in sorted(all_antennas):
            history = db.query_metrics_by_antenna(ant, limit=100)
            struct_eval = evaluate_structural_failure(history)
            if struct_eval.get("structural_failure_alert"):
                structural_alerts.append({
                    "antenna_id": ant,
                    "zone_id": ANTENNA_TO_ZONE.get(ant),
                    "reasons": struct_eval.get("reasons"),
                    "anomalies_7d": struct_eval.get("anomalies_7d_count"),
                    "drops_48h": struct_eval.get("drops_48h_count")
                })

        # 6. Cálculo de tiempo promedio de resolución (RF-49)
        durations = []
        for inc in incidents:
            if inc.get("status") in ("SOLUCIONADA", "CERRADA"):
                created_str = inc.get("created_at")
                updated_str = inc.get("updated_at")
                if created_str and updated_str:
                    try:
                        c_dt = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
                        u_dt = datetime.fromisoformat(updated_str.replace("Z", "+00:00"))
                        durations.append((u_dt - c_dt).total_seconds() / 60.0)
                    except Exception:
                        pass

        avg_resolution_minutes = round(sum(durations) / len(durations), 1) if durations else 0

        # 7. Resumen de incidentes colectivos activos
        active_collective = [c for c in collective_events if c.get("state") in ("ACTIVO", "EN_ATENCION")]

        return success({
            "overview": {
                "total_incidents": total_incidents,
                "total_affected_users": unique_users,
                "active_collective_incidents": len(active_collective),
                "structural_alerts_count": len(structural_alerts),
                "avg_resolution_time_minutes": avg_resolution_minutes
            },
            "incidents_by_status": dict(status_counter),
            "zones_ranking": zones_ranking,
            "problem_types_breakdown": problems_breakdown,
            "problematic_antennas_ranking": problematic_antennas,
            "active_structural_failure_alerts": structural_alerts,
            "active_collective_events": active_collective
        })

    except Exception as e:
        return server_error(f"Error al compilar resumen analítico: {str(e)}")

