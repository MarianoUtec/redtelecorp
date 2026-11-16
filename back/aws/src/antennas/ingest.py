"""
Ingesta y Clasificación Periódica de Telemetría de Antenas
POST /antennas/metrics
Cumple con RF-01 a RF-09, RF-54 a RF-56, RN-01 a RN-04, RN-11 y Sección 8.5 de SPECIFICATION.md.
"""

import json
from datetime import datetime, timezone
from typing import Dict, Any

try:
    from src.common.response import created, bad_request, server_error
    from src.common.models import (
        AntennaStatus,
        classify_antenna_traffic,
        evaluate_structural_failure
    )
    from src.common.zones import get_zone_for_antenna, resolve_zone
    from src.common.db import db
    from src.common.sns_client import sns
except ImportError:
    from common.response import created, bad_request, server_error
    from common.models import (
        AntennaStatus,
        classify_antenna_traffic,
        evaluate_structural_failure
    )
    from common.zones import get_zone_for_antenna, resolve_zone
    from common.db import db
    from common.sns_client import sns


def handler(event: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
    """Ingesta de métricas de tráfico y detección de anomalías operativas y estructurales."""
    try:
        body_raw = event.get("body")
        if not body_raw:
            return bad_request("El cuerpo de la petición no puede estar vacío")

        body = json.loads(body_raw) if isinstance(body_raw, str) else body_raw

        antenna_id = body.get("antenna_id")
        if not antenna_id:
            return bad_request("El campo 'antenna_id' es obligatorio (RF-02)")

        traffic_raw = body.get("traffic_gb_min")
        if traffic_raw is None:
            return bad_request("El campo 'traffic_gb_min' es obligatorio (RF-01)")

        try:
            traffic_gb_min = float(traffic_raw)
        except (ValueError, TypeError):
            return bad_request("El valor de 'traffic_gb_min' debe ser un número")

        # Clasificación estricta de umbrales (RN-01 a RN-04)
        # Evaluando 0 primero para evitar ambigüedad con < 60
        try:
            status = classify_antenna_traffic(traffic_gb_min)
        except ValueError as ve:
            return bad_request(str(ve))

        # Determinar zona asociada (RF-13, RF-30)
        zone_id = body.get("zone_id") or get_zone_for_antenna(antenna_id)
        if not zone_id:
            zone_id = resolve_zone(
                lat=body.get("lat") or body.get("latitude"),
                lng=body.get("lng") or body.get("longitude")
            )

        # Timestamp de la medición (RF-08)
        ts_str = body.get("timestamp")
        if ts_str:
            try:
                # Validar formato ISO
                _ = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                timestamp = ts_str
            except Exception:
                timestamp = datetime.now(timezone.utc).isoformat()
        else:
            timestamp = datetime.now(timezone.utc).isoformat()

        metric_item: Dict[str, Any] = {
            "antenna_id": str(antenna_id).upper(),
            "timestamp": timestamp,
            "zone_id": zone_id,
            "traffic_gb_min": traffic_gb_min,
            "status": status
        }

        # Guardar métrica en DynamoDB (RF-08)
        db.put_metric(metric_item)

        # -------------------------------------------------------------
        # Evaluación de Recurrencia y Falla Estructural (RF-54, RF-55, RF-56, Sección 8.5)
        # -------------------------------------------------------------
        history = db.query_metrics_by_antenna(str(antenna_id).upper(), limit=100)
        structural_eval = evaluate_structural_failure(history)

        if structural_eval.get("structural_failure_alert"):
            # Generar alerta técnica inmediata (RF-56, Sección 8.5)
            sns.publish_collective_alert({
                "event": "STRUCTURAL_FAILURE_ALERT",
                "antenna_id": str(antenna_id).upper(),
                "zone_id": zone_id,
                "reasons": structural_eval.get("reasons"),
                "timestamp": timestamp,
                "message": (
                    f"ALERTA OPERATIVA: Antena {antenna_id.upper()} en zona {zone_id} presenta "
                    f"patrón de falla estructural recurrente. Requiere mantenimiento físico."
                )
            })

        # Si hay anomalía (Caída, Saturada o Inhabilitada), emitir evento (RF-09, ESP-02)
        if status in (AntennaStatus.CAIDA.value, AntennaStatus.SATURADA.value, AntennaStatus.INHABILITADA.value):
            sns.publish_incident_event({
                "event": "ANTENNA_ANOMALY_DETECTED",
                "antenna_id": str(antenna_id).upper(),
                "zone_id": zone_id,
                "traffic_gb_min": traffic_gb_min,
                "status": status,
                "timestamp": timestamp
            })

            # Disparar correlación espacio-temporal reactiva
            try:
                try:
                    from src.analytics.evaluate_group import evaluate_zone_collective_incidents
                except ImportError:
                    from analytics.evaluate_group import evaluate_zone_collective_incidents
                evaluate_zone_collective_incidents(zone_id)
            except Exception:
                pass

        response_payload = {
            **metric_item,
            "structural_evaluation": structural_eval
        }

        return created(response_payload)

    except json.JSONDecodeError:
        return bad_request("El cuerpo de la petición contiene un JSON inválido")
    except Exception as e:
        return server_error(f"Error al procesar métrica de antena: {str(e)}")

