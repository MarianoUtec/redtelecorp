"""
Configuración de pruebas con Pytest para Red TeleCorp Backend.
"""

import os
import sys
from pathlib import Path
import pytest

# Configurar variables de entorno antes de importar módulos
os.environ["MOCK_AWS"] = "1"
os.environ["STAGE"] = "test"
os.environ["INCIDENTS_TABLE"] = "telecorp-incidents-test"
os.environ["METRICS_TABLE"] = "telecorp-antennas-metrics-test"
os.environ["COLLECTIVE_TABLE"] = "telecorp-collective-events-test"
os.environ["JWT_SECRET"] = "TestSecretKey2026Jwt_SecureKey32BytesLong!"

# Agregar rutas al sys.path
root_dir = Path(__file__).resolve().parent.parent
aws_dir = root_dir / "aws"
sys.path.insert(0, str(aws_dir))

from src.common.db import reset_mock_db
from src.common.sns_client import reset_published_messages
from src.notifications.worker import reset_dispatched_notifications


@pytest.fixture(autouse=True)
def clean_environment():
    """Limpia el estado en memoria antes de cada prueba unitaria."""
    reset_mock_db()
    reset_published_messages()
    reset_dispatched_notifications()
    yield
    reset_mock_db()
    reset_published_messages()
    reset_dispatched_notifications()
