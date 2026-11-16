#!/usr/bin/env python3
"""
Script de Carga de Datos Demo y Semilla Inicial
Pobla la plataforma con infraestructura de antenas, mediciones históricas,
reportes de usuarios y tokens de prueba para desarrollo local o demostración.
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Configurar PYTHONPATH
current_dir = Path(__file__).resolve().parent
aws_dir = current_dir.parent / "aws"
sys.path.insert(0, str(aws_dir))

from src.common.db import db
from src.common.jwt_utils import generate_token
from src.common.zones import ZONES_CATALOG, list_zones
from src.common.models import ProblemType, IncidentStatus, AntennaStatus, UserRole
from src.incidents.create import handler as create_incident_handler
from src.antennas.ingest import handler as ingest_metric_handler
from src.analytics.evaluate_group import evaluate_zone_collective_incidents


def seed_all():
    print("==================================================")
    print("  Iniciando Carga de Datos Demo - Red TeleCorp")
    print("==================================================")

    # 1. Generar Tokens de Prueba para la Hackathon
    print("\n[1/4] Generando tokens de autenticación para pruebas:")
    user_token = generate_token("usr-1001", UserRole.USUARIO.value, "usuario@telecorp.com")
    tech_token = generate_token("tech-2001", UserRole.OPERADOR.value, "operador@telecorp.com")
    admin_token = generate_token("adm-3001", UserRole.ADMINISTRADOR.value, "admin@telecorp.com")

    print(f"  * Token USUARIO:       Bearer {user_token[:25]}... (ID: usr-1001)")
    print(f"  * Token OPERADOR:      Bearer {tech_token[:25]}... (ID: tech-2001)")
    print(f"  * Token ADMINISTRADOR: Bearer {admin_token[:25]}... (ID: adm-3001)")

    # 2. Poblar Telemetría de Antenas
    print("\n[2/4] Registrando telemetría y métricas de antenas:")
    now = datetime.now(timezone.utc)

    # Sembrar diferentes condiciones
    antenna_scenarios = [
        ("ANT-101", 95.0, "ZONA-CENTRO-01"),   # Normal (60-129)
        ("ANT-102", 110.0, "ZONA-CENTRO-01"),  # Normal (60-129)
        ("ANT-201", 35.0, "ZONA-HOSP-01"),     # Caída (<60)
        ("ANT-202", 0.0, "ZONA-HOSP-01"),      # Inhabilitada (0)
        ("ANT-301", 145.0, "ZONA-IND-01"),     # Saturada (>129)
        ("ANT-401", 85.0, "ZONA-UNIV-01"),     # Normal
        ("ANT-501", 20.0, "ZONA-SUR-01"),      # Caída (<60)
        ("ANT-601", 75.0, "ZONA-NORTE-01"),    # Normal
        ("ANT-701", 132.0, "ZONA-ESTE-01"),    # Saturada (>129)
        ("ANT-801", 90.0, "ZONA-OESTE-01")     # Normal
    ]

    for ant_id, traffic, zone in antenna_scenarios:
        # Generar lectura actual
        res = ingest_metric_handler({
            "body": json.dumps({
                "antenna_id": ant_id,
                "traffic_gb_min": traffic,
                "zone_id": zone,
                "timestamp": now.isoformat()
            })
        })
        data = json.loads(res["body"])["data"]
        print(f"  * Antena {ant_id:<7} -> Tráfico: {traffic:>5.1f} GB/min -> Estado: {data['status']:<12} (Zona: {zone})")

    # 3. Poblar Incidencias de Usuarios
    print("\n[3/4] Registrando incidencias de usuarios en diferentes sectores:")
    sample_reports = [
        ("usr-1001", "987654321", ProblemType.SIN_COBERTURA.value, "Sin señal en hospital central", "ZONA-HOSP-01"),
        ("usr-1002", "987654322", ProblemType.FALLA_LLAMADAS.value, "Llamadas de emergencia caídas", "ZONA-HOSP-01"),
        ("usr-1003", "987654323", ProblemType.INTERNET_LENTO.value, "Conexión sumamente degradada", "ZONA-IND-01"),
        ("usr-1004", "987654324", ProblemType.INTERMITENCIA.value, "Señal va y viene constantemente", "ZONA-CENTRO-01"),
        ("usr-1005", "987654325", ProblemType.FALLA_SMS.value, "No llegan códigos de verificación SMS", "ZONA-SUR-01"),
    ]

    for uid, phone, p_type, desc, zone in sample_reports:
        res = create_incident_handler({
            "body": json.dumps({
                "user_id": uid,
                "service_number": phone,
                "problem_type": p_type,
                "description": desc,
                "zone_id": zone
            })
        })
        data = json.loads(res["body"])["data"]
        print(f"  * Incidencia {data['incident_id']} -> {p_type:<15} en {zone} (Estado: {data['status']})")

    # 4. Evaluación inicial de incidentes colectivos
    print("\n[4/4] Ejecutando evaluación inicial de correlación por zona:")
    for z in list_zones():
        z_id = z["zone_id"]
        res = evaluate_zone_collective_incidents(z_id)
        if res["isCollective"]:
            print(f"  [ALERTA COLECTIVA] Zona {z_id} -> Afectados: {res['affectedUsersCount']} -> Prioridad: {res['priority']}")
        else:
            print(f"  [OK] Zona {z_id} -> Reportes: {res['reportsProcessed']} (Bajo umbral colectivo)")

    print("\n==================================================")
    print("  Datos Semilla Cargados con Éxito")
    print("==================================================")


if __name__ == "__main__":
    seed_all()

