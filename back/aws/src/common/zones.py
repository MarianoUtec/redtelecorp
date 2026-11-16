"""
Registro de zonas geográficas, criticidad y resolución espacial
de acuerdo con la Sección 8.2 y 8.4 de SPECIFICATION.md.
"""

import math
from typing import Dict, Any, Optional, List
try:
    from src.common.models import ZoneCriticality
except ImportError:
    from common.models import ZoneCriticality

# Catálogo centralizado de zonas de cobertura de Red TeleCorp
ZONES_CATALOG: Dict[str, Dict[str, Any]] = {
    "ZONA-HOSP-01": {
        "zone_id": "ZONA-HOSP-01",
        "name": "Complejo Hospitalario y Servicios de Emergencia",
        "district": "Distrito Salud",
        "criticality": ZoneCriticality.CRITICA.value,
        "center_lat": -12.0850,
        "center_lng": -77.0350,
        "antennas": ["ANT-201", "ANT-202"],
        "description": "Sector crítico con hospitales de alta complejidad y centros de respuesta a emergencias."
    },
    "ZONA-IND-01": {
        "zone_id": "ZONA-IND-01",
        "name": "Parque Industrial y Logístico Norte",
        "district": "Distrito Industrial",
        "criticality": ZoneCriticality.CRITICA.value,
        "center_lat": -11.9500,
        "center_lng": -77.0600,
        "antennas": ["ANT-301", "ANT-302"],
        "description": "Sector de manufactura pesada, centros de datos y redes de distribución eléctrica."
    },
    "ZONA-CENTRO-01": {
        "zone_id": "ZONA-CENTRO-01",
        "name": "Centro Financiero y Administrativo",
        "district": "Distrito Central",
        "criticality": ZoneCriticality.ALTA.value,
        "center_lat": -12.0464,
        "center_lng": -77.0428,
        "antennas": ["ANT-101", "ANT-102"],
        "description": "Alta densidad comercial, entidades bancarias y dependencias gubernamentales."
    },
    "ZONA-UNIV-01": {
        "zone_id": "ZONA-UNIV-01",
        "name": "Ciudad Universitaria e Institutos Tecnológicos",
        "district": "Distrito Educativo",
        "criticality": ZoneCriticality.ALTA.value,
        "center_lat": -12.0580,
        "center_lng": -77.0810,
        "antennas": ["ANT-401", "ANT-402"],
        "description": "Campus universitarios de gran afluencia de estudiantes e investigadores."
    },
    "ZONA-ESTE-01": {
        "zone_id": "ZONA-ESTE-01",
        "name": "Corredor Comercial Este",
        "district": "Distrito Este",
        "criticality": ZoneCriticality.ALTA.value,
        "center_lat": -12.0250,
        "center_lng": -76.9950,
        "antennas": ["ANT-701"],
        "description": "Centros comerciales, estaciones de transporte multimodal y negocios minoristas."
    },
    "ZONA-SUR-01": {
        "zone_id": "ZONA-SUR-01",
        "name": "Residencial Sur - Los Laureles",
        "district": "Distrito Sur",
        "criticality": ZoneCriticality.ESTANDAR.value,
        "center_lat": -12.1400,
        "center_lng": -77.0200,
        "antennas": ["ANT-501", "ANT-502"],
        "description": "Área residencial y suburbana con comercios locales."
    },
    "ZONA-NORTE-01": {
        "zone_id": "ZONA-NORTE-01",
        "name": "Residencial Norte - Valle Verde",
        "district": "Distrito Norte",
        "criticality": ZoneCriticality.ESTANDAR.value,
        "center_lat": -11.9800,
        "center_lng": -77.0700,
        "antennas": ["ANT-601"],
        "description": "Comunidad residencial de densidad media y áreas recreativas."
    },
    "ZONA-OESTE-01": {
        "zone_id": "ZONA-OESTE-01",
        "name": "Residencial Oeste - Brisas del Mar",
        "district": "Distrito Costero",
        "criticality": ZoneCriticality.ESTANDAR.value,
        "center_lat": -12.0700,
        "center_lng": -77.1200,
        "antennas": ["ANT-801"],
        "description": "Zona costera residencial y portuaria ligera."
    }
}

# Mapeo inverso de antena a zona
ANTENNA_TO_ZONE: Dict[str, str] = {}
for z_id, data in ZONES_CATALOG.items():
    for ant in data["antennas"]:
        ANTENNA_TO_ZONE[ant] = z_id


def get_zone(zone_id: str) -> Optional[Dict[str, Any]]:
    """Obtiene la información de una zona por su identificador."""
    return ZONES_CATALOG.get(zone_id.upper() if zone_id else "")


def list_zones() -> List[Dict[str, Any]]:
    """Lista todas las zonas registradas en el sistema."""
    return list(ZONES_CATALOG.values())


def get_zone_criticality(zone_id: str) -> str:
    """Devuelve la criticidad de la zona o ESTANDAR si no existe."""
    zone = get_zone(zone_id)
    if zone:
        return zone.get("criticality", ZoneCriticality.ESTANDAR.value)
    return ZoneCriticality.ESTANDAR.value


def get_zone_for_antenna(antenna_id: str) -> Optional[str]:
    """Obtiene el zone_id asignado a una antena."""
    return ANTENNA_TO_ZONE.get(antenna_id.upper() if antenna_id else "")


def get_antennas_for_zone(zone_id: str) -> List[str]:
    """Devuelve la lista de antenas que dan cobertura a una zona."""
    zone = get_zone(zone_id)
    if zone:
        return zone.get("antennas", [])
    return []


def _haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calcula la distancia aproximada en kilómetros entre dos coordenadas GPS."""
    r = 6371.0  # Radio medio de la Tierra en km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return r * c


def resolve_zone(
    lat: Optional[float] = None,
    lng: Optional[float] = None,
    provided_zone_id: Optional[str] = None
) -> str:
    """
    Resuelve el identificador de zona más adecuado:
    1. Si se proporciona un `zone_id` válido, se utiliza.
    2. Si se suministran coordenadas lat/lng, busca la zona más cercana.
    3. En caso contrario, asigna 'ZONA-CENTRO-01' por defecto.
    """
    if provided_zone_id:
        clean_id = provided_zone_id.upper().strip()
        if clean_id in ZONES_CATALOG:
            return clean_id

    if lat is not None and lng is not None:
        try:
            flat = float(lat)
            flng = float(lng)
            closest_zone = "ZONA-CENTRO-01"
            min_dist = float("inf")
            for z_id, z_data in ZONES_CATALOG.items():
                dist = _haversine_distance(flat, flng, z_data["center_lat"], z_data["center_lng"])
                if dist < min_dist:
                    min_dist = dist
                    closest_zone = z_id
            return closest_zone
        except (ValueError, TypeError):
            pass

    return "ZONA-CENTRO-01"

