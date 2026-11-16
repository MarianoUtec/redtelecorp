#!/usr/bin/env python3
"""
Sincronizador Multicloud a Oracle Cloud Infrastructure (OCI Always Free)
Exporta métricas de antenas e incidencias resueltas/cerradas a OCI Object Storage
para análisis histórico de largo plazo sin consumir cuotas de almacenamiento en AWS.
Referencia: Sección 2 y Sección 7 de ARCHITECTURE.md.
"""

import os
import sys
import json
import gzip
import argparse
from datetime import datetime, timezone
from pathlib import Path

# Agregar raíz de backend al path para importar módulos comunes
current_dir = Path(__file__).resolve().parent
aws_src_dir = current_dir.parent / "aws"
sys.path.insert(0, str(aws_src_dir))

try:
    from src.common.db import db
    from src.common.response import json_dumps
except ImportError:
    # Fallback si se ejecuta desde otra ubicación
    sys.path.insert(0, str(current_dir.parent / "aws" / "src"))
    from common.db import db
    from common.response import json_dumps


def export_history_dataset(days_back: int = 30) -> dict:
    """Extrae incidencias solucionadas y métricas de antenas para archivo histórico."""
    all_incidents = db.list_all_incidents()
    all_metrics = db.list_all_metrics()
    all_collectives = db.list_collective_events()

    # Filtrar incidencias consolidadas (solucionadas o cerradas)
    historical_incidents = [
        i for i in all_incidents
        if i.get("status") in ("SOLUCIONADA", "CERRADA")
    ]

    export_timestamp = datetime.now(timezone.utc).isoformat()
    return {
        "metadata": {
            "exported_at": export_timestamp,
            "provider": "Oracle Cloud Infrastructure (OCI) Always Free",
            "tier": "Object Storage Archive",
            "telecorp_stage": os.environ.get("STAGE", "dev"),
            "total_incidents_archived": len(historical_incidents),
            "total_metrics_archived": len(all_metrics),
            "total_collectives_archived": len(all_collectives)
        },
        "incidents": historical_incidents,
        "antennas_metrics": all_metrics,
        "collective_events": all_collectives
    }


def upload_to_oci(
    data: dict,
    bucket_name: str,
    namespace: str,
    dry_run: bool = False,
    output_dir: str = "./oci_exports"
) -> dict:
    """
    Sube el archivo comprimido a OCI Object Storage.
    Soporta API S3-Compatible de OCI y modo local offline (--dry-run).
    """
    now_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"telecorp_historical_{now_str}.json.gz"

    # Preparar payload JSON comprimido en gzip
    json_bytes = json_dumps(data).encode("utf-8")
    compressed_data = gzip.compress(json_bytes)

    # Si es dry-run o faltan credenciales OCI, guardar localmente
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    local_file = out_path / filename

    with open(local_file, "wb") as f:
        f.write(compressed_data)

    print(f"[OK] Archivo histórico generado exitosamente: {local_file} ({len(compressed_data)} bytes)")

    if dry_run:
        return {
            "status": "DRY_RUN_SUCCESS",
            "file": str(local_file),
            "bytes": len(compressed_data),
            "note": "Modo de simulación activado. El archivo no fue transferido a OCI."
        }

    # Intentar subir mediante cliente S3 compatible o SDK de OCI
    oci_endpoint = os.environ.get(
        "OCI_COMPATIBLE_ENDPOINT",
        f"https://{namespace}.compat.objectstorage.us-ashburn-1.oraclecloud.com"
    )
    oci_access_key = os.environ.get("OCI_ACCESS_KEY_ID")
    oci_secret_key = os.environ.get("OCI_SECRET_ACCESS_KEY")

    if not (oci_access_key and oci_secret_key):
        print("[AVISO] OCI_ACCESS_KEY_ID u OCI_SECRET_ACCESS_KEY no configurados.")
        print(f"[INFO] Archivo preservado localmente en: {local_file}")
        return {
            "status": "LOCAL_SAVED",
            "file": str(local_file),
            "bytes": len(compressed_data),
            "reason": "Credenciales OCI no suministradas"
        }

    try:
        import boto3
        from botocore.config import Config

        s3_oci = boto3.client(
            "s3",
            endpoint_url=oci_endpoint,
            aws_access_key_id=oci_access_key,
            aws_secret_access_key=oci_secret_key,
            config=Config(signature_version="s3v4")
        )

        s3_oci.put_object(
            Bucket=bucket_name,
            Key=f"history/{filename}",
            Body=compressed_data,
            ContentType="application/gzip"
        )
        print(f"[SUCCESS] Subida a OCI Object Storage completada: s3://{bucket_name}/history/{filename}")
        return {
            "status": "UPLOADED_TO_OCI",
            "bucket": bucket_name,
            "key": f"history/{filename}",
            "bytes": len(compressed_data)
        }

    except Exception as e:
        print(f"[ERROR] Error al transferir a OCI: {str(e)}")
        return {
            "status": "UPLOAD_FAILED",
            "error": str(e),
            "local_file": str(local_file)
        }


def main():
    parser = argparse.ArgumentParser(description="Sincronizador Multicloud a OCI Object Storage")
    parser.add_argument("--bucket", default=os.environ.get("OCI_BUCKET_NAME", "telecorp-history-archive"), help="Nombre del bucket en OCI")
    parser.add_argument("--namespace", default=os.environ.get("OCI_NAMESPACE", "telecorp_tenancy"), help="Tenancy Namespace en OCI")
    parser.add_argument("--dry-run", action="store_true", help="Generar archivo local sin subir a la nube")
    parser.add_argument("--output-dir", default="./oci_exports", help="Directorio de exportaciones locales")
    parser.add_argument("--days", type=int, default=30, help="Días de historial a exportar")

    args = parser.parse_args()

    print("=====================================================")
    print("  Red TeleCorp - Multicloud OCI Synchronization")
    print("=====================================================")
    dataset = export_history_dataset(days_back=args.days)
    print(f"  Incidencias históricas: {dataset['metadata']['total_incidents_archived']}")
    print(f"  Métricas de antenas:    {dataset['metadata']['total_metrics_archived']}")
    print(f"  Incidentes colectivos:  {dataset['metadata']['total_collectives_archived']}")
    print("-----------------------------------------------------")

    result = upload_to_oci(
        data=dataset,
        bucket_name=args.bucket,
        namespace=args.namespace,
        dry_run=args.dry_run,
        output_dir=args.output_dir
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

