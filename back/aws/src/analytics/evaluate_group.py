"""
Orquestador de Detección de Incidentes Colectivos y Correlación Espacio-Temporal
Cumple con RF-25 a RF-31, RF-39 a RF-43, RF-52 a RF-56, RN-08, RN-10
y Secciones 3.2, 8.4 y 8.6 de SPECIFICATION.md y ARCHITECTURE.md.

Invocable tanto como tarea de AWS Step Functions (Task State)
como función reactiva desacoplada desde APIs y EventBus.
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional

try:
    from src.common.models import (
        COLLECTIVE_MIN_USERS,
        COLLECTIVE_WINDOW_HOURS,
        CORRELATION_WINDOW_MINUTES,
        AntennaStatus,
        calculate_incident_priority
    )
    from src.common.zones import (
        get_zone,
        get_zone_criticality,
        get_antennas_for_zone,
        ZONES_CATALOG
    )
    from src.common.db import db
    from src.common.sns_client import sns
except ImportError:
    from common.models import (
        COLLECTIVE_MIN_USERS,
        COLLECTIVE_WINDOW_HOURS,
        CORRELATION_WINDOW_MINUTES,
        AntennaStatus,
        calculate_incident_priority
    )
    from common.zones import (
        get_zone,
        get_zone_criticality,
        get_antennas_for_zone,
        ZONES_CATALOG
    )
    from common.db import db
    from common.sns_client import sns


def evaluate_zone_collective_incidents(zone_id: str) -> Dict[str, Any]:
    """
    Evalúa la existencia de un posible incidente colectivo en una zona geográfica:
    1. Agrupa reportes de la zona dentro de las últimas 24 horas (RN-08).
    2. Cuenta usuarios distintos (umbral >= 10).
    3. Si se alcanza el umbral, correlaciona con la telemetría de antenas (±60 min).
    4. Asigna prioridad P1-P4 según criticidad de zona y usuarios.
    5. Registra/actualiza el incidente colectivo y vincula los reportes individuales (RF-31).
    6. Dispara alertas y notificaciones a los usuarios afectados.
    """
    now_dt = datetime.now(timezone.utc)
    cutoff_24h = (now_dt - timedelta(hours=COLLECTIVE_WINDOW_HOURS)).isoformat()
    now_iso = now_dt.isoformat()
    today_str = now_dt.strftime("%Y%m%d")

    # 1. Consultar reportes activos en la zona en la ventana < 24 horas
    reports = db.query_incidents_by_zone(zone_id, since_iso=cutoff_24h, active_only=True)

    # 2. Contabilizar usuarios distintos (RN-08, RF-27, RF-28)
    user_ids = {r.get("user_id") for r in reports if r.get("user_id")}
    affected_users_count = len(user_ids)
    is_collective = affected_users_count >= COLLECTIVE_MIN_USERS

    # 3. Correlación espacio-temporal con telemetría de antenas (RF-52, RF-53, Sección 8.6)
    correlation_cutoff = (now_dt - timedelta(minutes=CORRELATION_WINDOW_MINUTES)).isoformat()
    zone_metrics = db.query_metrics_by_zone(zone_id, since_iso=correlation_cutoff)

    # Buscar anomalías en antenas que dan cobertura a la zona
    related_antenna_id: Optional[str] = None
    antenna_status: str = AntennaStatus.NORMAL.value
    root_cause_confirmed = False
    anomalous_metrics = [
        m for m in zone_metrics
        if m.get("status") in (AntennaStatus.CAIDA.value, AntennaStatus.SATURADA.value, AntennaStatus.INHABILITADA.value)
    ]

    if anomalous_metrics:
        # Tomar la anomalía más severa o reciente
        best_match = anomalous_metrics[0]
        related_antenna_id = best_match.get("antenna_id")
        antenna_status = best_match.get("status", AntennaStatus.NORMAL.value)
        root_cause_confirmed = True
    else:
        # Si no hay métricas recientes, tomar la antena principal asignada a la zona
        assigned_antennas = get_antennas_for_zone(zone_id)
        if assigned_antennas:
            related_antenna_id = assigned_antennas[0]

    # 4. Cálculo de Prioridad según la Matriz (RF-41, RF-42, Sección 8.4)
    zone_crit = get_zone_criticality(zone_id)
    priority = calculate_incident_priority(
        affected_users_count=affected_users_count,
        zone_criticality=zone_crit,
        antenna_status=antenna_status
    )

    collective_id = f"COL#{today_str}-{zone_id}"
    collective_event_record: Optional[Dict[str, Any]] = None

    if is_collective:
        # 5. Crear o actualizar registro de incidente colectivo en DynamoDB
        collective_event_record = {
            "zone_id": zone_id,
            "collective_id": collective_id,
            "affected_users_count": affected_users_count,
            "distinct_users": list(user_ids),
            "priority": priority,
            "related_antenna_id": related_antenna_id,
            "antenna_status": antenna_status,
            "root_cause_confirmed": root_cause_confirmed,
            "state": "ACTIVO",
            "created_at": now_iso,
            "updated_at": now_iso
        }
        db.put_collective_event(collective_event_record)

        # Vincular cada reporte individual al incidente colectivo (RF-31)
        for rep in reports:
            if rep.get("collective_id") != collective_id:
                inc_id = rep.get("incident_id")
                if inc_id:
                    db.update_incident_record(zone_id, inc_id, {
                        "collective_id": collective_id,
                        "priority": priority,
                        "updated_at": now_iso
                    })

        # 6. Publicar alerta colectiva y notificaciones (RF-29, RF-36, Sección 8.7)
        sns.publish_collective_alert({
            "event": "COLLECTIVE_INCIDENT_DETECTED",
            "zone_id": zone_id,
            "collective_id": collective_id,
            "affected_users_count": affected_users_count,
            "priority": priority,
            "antenna_status": antenna_status,
            "related_antenna_id": related_antenna_id,
            "timestamp": now_iso
        })

        # Notificar a usuarios de la zona (vía SNS Topic telecorp-user-notifications)
        sns.publish_user_notification({
            "event": "COLLECTIVE_INCIDENT_DETECTED",
            "zone_id": zone_id,
            "collective_id": collective_id,
            "affectedUsers": affected_users_count,
            "priority": priority,
            "antennaStatus": antenna_status,
            "message": (
                f"Red TeleCorp Alerta: Se ha identificado una afectación colectiva en su sector ({zone_id}) "
                f"con prioridad {priority}. Nuestro equipo técnico está gestionando la solución."
            )
        })

    return {
        "isCollective": is_collective,
        "zoneId": zone_id,
        "affectedUsersCount": affected_users_count,
        "priority": priority,
        "antennaStatus": antenna_status,
        "relatedAntennaId": related_antenna_id,
        "rootCauseConfirmed": root_cause_confirmed,
        "collectiveId": collective_id if is_collective else None,
        "reportsProcessed": len(reports),
        "evaluatedAt": now_iso
    }


def handler(event: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
    """
    Manejador Lambda para AWS Step Functions o invocación directa.
    Acepta tanto payloads con `zoneId` o `zone_id`, como arrays de eventos.
    """
    zone_id = (
        event.get("zoneId")
        or event.get("zone_id")
        or event.get("detail", {}).get("zone_id")
    )

    if not zone_id:
        # Si no se especifica zona, evaluar todas las zonas del catálogo
        results = []
        for z in ZONES_CATALOG.keys():
            res = evaluate_zone_collective_incidents(z)
            results.append(res)
        return {
            "success": True,
            "totalZonesEvaluated": len(results),
            "zones": results
        }

    result = evaluate_zone_collective_incidents(zone_id)
    return result

