"""
Capa de abstracción y persistencia DynamoDB para Red TeleCorp.
Soporta ejecución real con AWS boto3 y emulación en memoria de alta fidelidad
para pruebas unitarias y desarrollo local offline sin credenciales de AWS.
"""

import os
import copy
from typing import Dict, Any, List, Optional
from decimal import Decimal

def _to_dynamo(obj):
    """DynamoDB no acepta float: convierte recursivamente a Decimal."""
    if isinstance(obj, float):
        return Decimal(str(obj))
    if isinstance(obj, dict):
        return {k: _to_dynamo(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_dynamo(v) for v in obj]
    return obj


# Tablas configuradas desde variables de entorno
STAGE = os.environ.get("STAGE", "dev")
INCIDENTS_TABLE_NAME = os.environ.get("INCIDENTS_TABLE", f"telecorp-incidents-{STAGE}")
METRICS_TABLE_NAME = os.environ.get("METRICS_TABLE", f"telecorp-antennas-metrics-{STAGE}")
COLLECTIVE_TABLE_NAME = os.environ.get("COLLECTIVE_TABLE", f"telecorp-collective-events-{STAGE}")

# Determinación de modo mock/local
FORCE_MOCK = os.environ.get("MOCK_AWS", "0") == "1" or "PYTEST_CURRENT_TEST" in os.environ

# Almacenamiento en memoria para desarrollo local / pruebas
_MOCK_STORAGE: Dict[str, List[Dict[str, Any]]] = {
    INCIDENTS_TABLE_NAME: [],
    METRICS_TABLE_NAME: [],
    COLLECTIVE_TABLE_NAME: []
}


def reset_mock_db() -> None:
    """Limpia el almacenamiento mock en memoria (ideal para tests)."""
    for table_name in _MOCK_STORAGE:
        _MOCK_STORAGE[table_name].clear()


def is_mock_active() -> bool:
    """Verifica si se debe usar la base de datos mock."""
    if FORCE_MOCK:
        return True
    try:
        import boto3
        session = boto3.session.Session()
        credentials = session.get_credentials()
        return credentials is None
    except Exception:
        return True


class DynamoClient:
    """Cliente unificado para interactuar con DynamoDB (Boto3 o Mock)."""

    def __init__(self):
        self._dynamodb = None
        if not is_mock_active():
            try:
                import boto3
                region = os.environ.get("AWS_REGION", "us-east-1")
                self._dynamodb = boto3.resource("dynamodb", region_name=region)
            except Exception:
                self._dynamodb = None

    def _get_table(self, table_name: str):
        if self._dynamodb:
            return self._dynamodb.Table(table_name)
        return None

    # ==========================================
    # Operaciones sobre Incidencias
    # ==========================================
    def put_incident(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Guarda o reemplaza una incidencia."""
        table = self._get_table(INCIDENTS_TABLE_NAME)
        if table:
            table.put_item(Item=_to_dynamo(item))
        else:
            # Mock store
            existing = [
                i for i in _MOCK_STORAGE[INCIDENTS_TABLE_NAME]
                if not (i.get("zone_id") == item.get("zone_id") and i.get("incident_id") == item.get("incident_id"))
            ]
            existing.append(copy.deepcopy(item))
            _MOCK_STORAGE[INCIDENTS_TABLE_NAME] = existing
        return item

    def get_incident(self, incident_id: str, zone_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Busca una incidencia por incident_id (y opcionalmente zone_id)."""
        table = self._get_table(INCIDENTS_TABLE_NAME)
        if table and zone_id:
            res = table.get_item(Key={"zone_id": zone_id, "incident_id": incident_id})
            return res.get("Item")
        elif table:
            # Scan con filtro
            res = table.scan(
                FilterExpression="incident_id = :inc_id",
                ExpressionAttributeValues={":inc_id": incident_id}
            )
            items = res.get("Items", [])
            return items[0] if items else None
        else:
            # Mock store
            for inc in _MOCK_STORAGE[INCIDENTS_TABLE_NAME]:
                if inc.get("incident_id") == incident_id:
                    if zone_id is None or inc.get("zone_id") == zone_id:
                        return copy.deepcopy(inc)
            return None

    def query_incidents_by_user(self, user_id: str) -> List[Dict[str, Any]]:
        """Obtiene las incidencias reportadas por un usuario específico."""
        table = self._get_table(INCIDENTS_TABLE_NAME)
        if table:
            try:
                # Intentar usar GSI de usuario
                res = table.query(
                    IndexName="UserIndex",
                    KeyConditionExpression="user_id = :u",
                    ExpressionAttributeValues={":u": user_id},
                    ScanIndexForward=False
                )
                return res.get("Items", [])
            except Exception:
                # Fallback a Scan si el GSI no está disponible
                res = table.scan(
                    FilterExpression="user_id = :u",
                    ExpressionAttributeValues={":u": user_id}
                )
                items = res.get("Items", [])
                items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
                return items
        else:
            results = [
                copy.deepcopy(inc)
                for inc in _MOCK_STORAGE[INCIDENTS_TABLE_NAME]
                if inc.get("user_id") == user_id
            ]
            results.sort(key=lambda x: x.get("created_at", ""), reverse=True)
            return results

    def query_incidents_by_zone(
        self,
        zone_id: str,
        since_iso: Optional[str] = None,
        active_only: bool = False
    ) -> List[Dict[str, Any]]:
        """Obtiene las incidencias de una zona determinada."""
        table = self._get_table(INCIDENTS_TABLE_NAME)
        if table:
            try:
                if since_iso:
                    res = table.query(
                        KeyConditionExpression="zone_id = :z",
                        FilterExpression="created_at >= :since",
                        ExpressionAttributeValues={":z": zone_id, ":since": since_iso}
                    )
                else:
                    res = table.query(
                        KeyConditionExpression="zone_id = :z",
                        ExpressionAttributeValues={":z": zone_id}
                    )
                items = res.get("Items", [])
            except Exception:
                res = table.scan(
                    FilterExpression="zone_id = :z",
                    ExpressionAttributeValues={":z": zone_id}
                )
                items = res.get("Items", [])
        else:
            items = [
                copy.deepcopy(inc)
                for inc in _MOCK_STORAGE[INCIDENTS_TABLE_NAME]
                if inc.get("zone_id") == zone_id
            ]

        if since_iso:
            items = [i for i in items if i.get("created_at", "") >= since_iso]
        if active_only:
            items = [i for i in items if i.get("status") != "CERRADA"]

        items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return items

    def list_all_incidents(
        self,
        zone_id: Optional[str] = None,
        status: Optional[str] = None,
        problem_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Lista todas las incidencias aplicando filtros opcionales."""
        table = self._get_table(INCIDENTS_TABLE_NAME)
        if table:
            res = table.scan()
            items = res.get("Items", [])
        else:
            items = [copy.deepcopy(i) for i in _MOCK_STORAGE[INCIDENTS_TABLE_NAME]]

        if zone_id:
            items = [i for i in items if i.get("zone_id") == zone_id]
        if status:
            items = [i for i in items if i.get("status") == status]
        if problem_type:
            items = [i for i in items if i.get("problem_type") == problem_type]

        items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return items

    def update_incident_record(
        self,
        zone_id: str,
        incident_id: str,
        updates: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Actualiza atributos específicos de una incidencia."""
        table = self._get_table(INCIDENTS_TABLE_NAME)
        if table:
            update_expr_parts = []
            expr_names = {}
            expr_values = {}
            for idx, (k, v) in enumerate(updates.items()):
                attr_name = f"#attr{idx}"
                attr_val = f":val{idx}"
                update_expr_parts.append(f"{attr_name} = {attr_val}")
                expr_names[attr_name] = k
                expr_values[attr_val] = _to_dynamo(v)

            expr_str = "SET " + ", ".join(update_expr_parts)
            res = table.update_item(
                Key={"zone_id": zone_id, "incident_id": incident_id},
                UpdateExpression=expr_str,
                ExpressionAttributeNames=expr_names,
                ExpressionAttributeValues=expr_values,
                ReturnValues="ALL_NEW"
            )
            return res.get("Attributes")
        else:
            for inc in _MOCK_STORAGE[INCIDENTS_TABLE_NAME]:
                if inc.get("zone_id") == zone_id and inc.get("incident_id") == incident_id:
                    inc.update(copy.deepcopy(updates))
                    return copy.deepcopy(inc)
            return None

    # ==========================================
    # Operaciones sobre Métricas de Antenas
    # ==========================================
    def put_metric(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Registra una métrica de antena."""
        table = self._get_table(METRICS_TABLE_NAME)
        if table:
            table.put_item(Item=_to_dynamo(item))
        else:
            _MOCK_STORAGE[METRICS_TABLE_NAME].append(copy.deepcopy(item))
        return item

    def query_metrics_by_antenna(
        self,
        antenna_id: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Obtiene el historial cronológico de métricas de una antena."""
        table = self._get_table(METRICS_TABLE_NAME)
        if table:
            try:
                res = table.query(
                    KeyConditionExpression="antenna_id = :a",
                    ExpressionAttributeValues={":a": antenna_id},
                    ScanIndexForward=False,
                    Limit=limit
                )
                return res.get("Items", [])
            except Exception:
                res = table.scan(
                    FilterExpression="antenna_id = :a",
                    ExpressionAttributeValues={":a": antenna_id}
                )
                items = res.get("Items", [])
                items.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
                return items[:limit]
        else:
            results = [
                copy.deepcopy(m)
                for m in _MOCK_STORAGE[METRICS_TABLE_NAME]
                if m.get("antenna_id") == antenna_id
            ]
            results.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
            return results[:limit]

    def query_metrics_by_zone(
        self,
        zone_id: str,
        since_iso: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Obtiene métricas de antenas asociadas a una zona."""
        table = self._get_table(METRICS_TABLE_NAME)
        if table:
            res = table.scan(
                FilterExpression="zone_id = :z",
                ExpressionAttributeValues={":z": zone_id}
            )
            items = res.get("Items", [])
        else:
            items = [
                copy.deepcopy(m)
                for m in _MOCK_STORAGE[METRICS_TABLE_NAME]
                if m.get("zone_id") == zone_id
            ]

        if since_iso:
            items = [m for m in items if m.get("timestamp", "") >= since_iso]

        items.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return items

    def list_all_metrics(self) -> List[Dict[str, Any]]:
        """Obtiene todas las métricas registradas."""
        table = self._get_table(METRICS_TABLE_NAME)
        if table:
            res = table.scan()
            return res.get("Items", [])
        return [copy.deepcopy(m) for m in _MOCK_STORAGE[METRICS_TABLE_NAME]]

    # ==========================================
    # Operaciones sobre Incidentes Colectivos
    # ==========================================
    def put_collective_event(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Guarda o actualiza un evento de incidente colectivo."""
        table = self._get_table(COLLECTIVE_TABLE_NAME)
        if table:
            table.put_item(Item=_to_dynamo(item))
        else:
            existing = [
                c for c in _MOCK_STORAGE[COLLECTIVE_TABLE_NAME]
                if not (c.get("zone_id") == item.get("zone_id") and c.get("collective_id") == item.get("collective_id"))
            ]
            existing.append(copy.deepcopy(item))
            _MOCK_STORAGE[COLLECTIVE_TABLE_NAME] = existing
        return item

    def get_collective_event(self, zone_id: str, collective_id: str) -> Optional[Dict[str, Any]]:
        """Busca un incidente colectivo por clave compuesta."""
        table = self._get_table(COLLECTIVE_TABLE_NAME)
        if table:
            res = table.get_item(Key={"zone_id": zone_id, "collective_id": collective_id})
            return res.get("Item")
        else:
            for col in _MOCK_STORAGE[COLLECTIVE_TABLE_NAME]:
                if col.get("zone_id") == zone_id and col.get("collective_id") == collective_id:
                    return copy.deepcopy(col)
            return None

    def list_collective_events(
        self,
        zone_id: Optional[str] = None,
        active_only: bool = False
    ) -> List[Dict[str, Any]]:
        """Lista los incidentes colectivos registrados."""
        table = self._get_table(COLLECTIVE_TABLE_NAME)
        if table:
            res = table.scan()
            items = res.get("Items", [])
        else:
            items = [copy.deepcopy(c) for c in _MOCK_STORAGE[COLLECTIVE_TABLE_NAME]]

        if zone_id:
            items = [c for c in items if c.get("zone_id") == zone_id]
        if active_only:
            items = [c for c in items if c.get("state") in ("ACTIVO", "EN_ATENCION")]

        items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return items


# Instancia singleton para uso en toda la aplicación
db = DynamoClient()

