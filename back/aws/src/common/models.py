"""
Modelos de datos, catálogos estandarizados y reglas de negocio
del sistema Red TeleCorp de acuerdo con SPECIFICATION.md y ARCHITECTURE.md.
"""

from enum import Enum
from typing import Optional, List, Dict, Any


class IncidentStatus(str, Enum):
    """Estados del ciclo de vida de una incidencia (RF-20, RF-21)."""
    REGISTRADA = "REGISTRADA"
    EN_REVISION = "EN_REVISION"
    SIENDO_ATENDIDA = "SIENDO_ATENDIDA"
    SOLUCIONADA = "SOLUCIONADA"
    CERRADA = "CERRADA"

    @classmethod
    def is_valid_transition(cls, current: str, target: str) -> bool:
        """
        Valida que la transición entre estados sea válida según el flujo operativo.
        """
        valid_transitions = {
            cls.REGISTRADA.value: [cls.EN_REVISION.value, cls.CERRADA.value],
            cls.EN_REVISION.value: [cls.SIENDO_ATENDIDA.value, cls.SOLUCIONADA.value, cls.CERRADA.value],
            cls.SIENDO_ATENDIDA.value: [cls.SOLUCIONADA.value, cls.EN_REVISION.value, cls.CERRADA.value],
            cls.SOLUCIONADA.value: [cls.CERRADA.value, cls.EN_REVISION.value],
            cls.CERRADA.value: [],  # Estado terminal
        }
        return target in valid_transitions.get(current, [])


class ProblemType(str, Enum):
    """Catálogo estandarizado de problemas reportados por usuarios (Sección 8.3)."""
    SIN_COBERTURA = "SIN_COBERTURA"          # Sin señal / Cobertura nula
    INTERNET_LENTO = "INTERNET_LENTO"        # Datos lentos / Latencia alta
    FALLA_LLAMADAS = "FALLA_LLAMADAS"        # Corte o caída de voz
    FALLA_SMS = "FALLA_SMS"                  # Falla en mensajería SMS
    INTERMITENCIA = "INTERMITENCIA"          # Reconexión recurrente / inestable


class AntennaStatus(str, Enum):
    """Estados operativos de una antena de telecomunicaciones (RF-04 a RF-07, RN-01 a RN-04)."""
    INHABILITADA = "INHABILITADA"  # 0 GB/min
    CAIDA = "CAIDA"                # < 60 GB/min (excepto 0)
    NORMAL = "NORMAL"              # 60 a 129 GB/min inclusive
    SATURADA = "SATURADA"          # > 129 GB/min


class Priority(str, Enum):
    """Niveles de prioridad para atención de incidencias (RF-42, Sección 8.4)."""
    P1 = "P1"  # Crítica
    P2 = "P2"  # Alta
    P3 = "P3"  # Media
    P4 = "P4"  # Baja


class ZoneCriticality(str, Enum):
    """Criticidad de zonas geográficas (Sección 8.4)."""
    CRITICA = "CRITICA"    # Hospitales, industrias estratégicas, emergencias (Peso 3)
    ALTA = "ALTA"          # Zonas comerciales densas, universidades (Peso 2)
    ESTANDAR = "ESTANDAR"  # Residenciales, suburbanas (Peso 1)


class UserRole(str, Enum):
    """Roles de acceso RBAC (Sección 8.9)."""
    USUARIO = "USUARIO"
    OPERADOR = "OPERADOR"
    ADMINISTRADOR = "ADMINISTRADOR"


# Constantes y umbrales de negocio (RN-01 a RN-11, Sección 8)
COLLECTIVE_MIN_USERS = 10              # >= 10 usuarios distintos en misma zona
COLLECTIVE_WINDOW_HOURS = 24           # Dentro de un intervalo < 24 horas
CORRELATION_WINDOW_MINUTES = 60        # +-60 min entre reporte y anomalía de antena
RECURRENCE_ANOMALIES_WINDOW_DAYS = 7   # 7 días continuos
RECURRENCE_ANOMALIES_THRESHOLD = 3     # 3 o más anomalías (CAIDA o SATURADA)
RECURRENCE_DROPS_WINDOW_HOURS = 48     # 48 horas
RECURRENCE_DROPS_THRESHOLD = 2         # 2 caídas completas (CAIDA o INHABILITADA)


def classify_antenna_traffic(traffic_gb_min: float) -> str:
    """
    Clasifica el estado de una antena según los umbrales de tráfico (RN-01 a RN-04):
    - 0 GB/min: Inhabilitada (evaluado primero)
    - Menos de 60 GB/min: Caída
    - 60 a 129 GB/min: Funcionamiento normal
    - Más de 129 GB/min: Saturada
    """
    try:
        traffic = float(traffic_gb_min)
    except (ValueError, TypeError):
        raise ValueError(f"Valor de tráfico inválido: {traffic_gb_min}")

    if traffic < 0:
        raise ValueError("El tráfico no puede ser negativo")

    # Regla: Se evalúa primero si el tráfico es 0 para evitar ambigüedad con < 60
    if traffic == 0.0:
        return AntennaStatus.INHABILITADA.value
    elif traffic < 60.0:
        return AntennaStatus.CAIDA.value
    elif traffic <= 129.0:
        return AntennaStatus.NORMAL.value
    else:
        return AntennaStatus.SATURADA.value


def calculate_incident_priority(
    affected_users_count: int,
    zone_criticality: str = ZoneCriticality.ESTANDAR.value,
    antenna_status: Optional[str] = None
) -> str:
    """
    Calcula la prioridad (P1 a P4) combinando el impacto poblacional,
    la criticidad del sector y el estado de la infraestructura (Sección 8.4):

    - P1 - Crítica: Incidentes colectivos (>=10) en zona Alta/Crítica,
                    O antena inhabilitada (0 GB/min) en infraestructura crítica/alta.
    - P2 - Alta:    Incidentes colectivos en zona estándar,
                    O múltiples individuales (5-9) en zona crítica.
    - P3 - Media:   Incidentes individuales menores (2-4),
                    O degradaciones leves en estándar.
    - P4 - Baja:    Reporte aislado (1 usuario) sin impacto reportado en infraestructura.
    """
    crit = zone_criticality.upper() if zone_criticality else ZoneCriticality.ESTANDAR.value

    # Condición de antena inhabilitada en zona crítica o alta
    if antenna_status == AntennaStatus.INHABILITADA.value and crit in (ZoneCriticality.CRITICA.value, ZoneCriticality.ALTA.value):
        return Priority.P1.value

    if affected_users_count >= COLLECTIVE_MIN_USERS:
        if crit in (ZoneCriticality.CRITICA.value, ZoneCriticality.ALTA.value):
            return Priority.P1.value
        return Priority.P2.value

    if 5 <= affected_users_count <= 9:
        if crit == ZoneCriticality.CRITICA.value:
            return Priority.P2.value
        return Priority.P3.value

    if 2 <= affected_users_count <= 4:
        return Priority.P3.value

    # 1 o 0 usuarios
    return Priority.P4.value


def evaluate_structural_failure(metrics_history: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Evalúa si una antena cumple con los criterios de Falla Estructural (Sección 8.5):
    - Criterio A: 3 o más transiciones a estado Caída o Saturada o Inhabilitada en 7 días móviles.
    - Criterio B: 2 caídas completas (Caída o Inhabilitada) dentro de 48 horas.
    """
    from datetime import datetime, timezone, timedelta

    now = datetime.now(timezone.utc)
    cutoff_7d = now - timedelta(days=RECURRENCE_ANOMALIES_WINDOW_DAYS)
    cutoff_48h = now - timedelta(hours=RECURRENCE_DROPS_WINDOW_HOURS)

    anomalies_7d = 0
    drops_48h = 0

    for item in metrics_history:
        ts_str = item.get("timestamp")
        status = item.get("status")
        if not ts_str or not status:
            continue

        try:
            ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        except Exception:
            continue

        if ts >= cutoff_7d:
            if status in (AntennaStatus.CAIDA.value, AntennaStatus.SATURADA.value, AntennaStatus.INHABILITADA.value):
                anomalies_7d += 1

        if ts >= cutoff_48h:
            if status in (AntennaStatus.CAIDA.value, AntennaStatus.INHABILITADA.value):
                drops_48h += 1

    alert = False
    reasons = []

    if anomalies_7d >= RECURRENCE_ANOMALIES_THRESHOLD:
        alert = True
        reasons.append(f"{anomalies_7d} anomalías detectadas en los últimos 7 días (umbral: {RECURRENCE_ANOMALIES_THRESHOLD})")

    if drops_48h >= RECURRENCE_DROPS_THRESHOLD:
        alert = True
        reasons.append(f"{drops_48h} caídas completas detectadas en las últimas 48 horas (umbral: {RECURRENCE_DROPS_THRESHOLD})")

    return {
        "structural_failure_alert": alert,
        "anomalies_7d_count": anomalies_7d,
        "drops_48h_count": drops_48h,
        "reasons": reasons,
    }

