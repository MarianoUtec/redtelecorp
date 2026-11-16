# Capa Multicloud: OCI Always Free & Almacenamiento Histórico

Este módulo implementa la estrategia de integración multicloud definida en la **Sección 2** de `ARCHITECTURE.md`, delegando el almacenamiento a largo plazo de reportes e histórico de antenas en **Oracle Cloud Infrastructure (OCI) Always Free Tier**.

## Ventajas en el Presupuesto Estudiantil
- **Preservación de cuotas de AWS Academy:** AWS Academy Learner Lab tiene un límite estricto de \$100. Almacenar gigabytes de métricas y auditorías en DynamoDB incrementaría innecesariamente los costos de almacenamiento.
- **20 GB Gratuitos Vitalicios:** OCI provee hasta 20 GB de Object Storage estándar y 2 bases de datos autónomas en su capa *Always Free*.

---

## Modos de Operación de `sync_history.py`

### 1. Modo Local / Simulación (`--dry-run`)
Genera el paquete comprimido `.json.gz` en disco local sin requerir credenciales ni conexión a OCI:

```bash
python3 back/oci/sync_history.py --dry-run --output-dir ./exports
```

### 2. Subida Directa a OCI Object Storage
Utiliza la API S3-Compatible de OCI:

1. Genera un **Customer Secret Key** en la consola de OCI (User Settings -> Customer Secret Keys).
2. Configura las variables de entorno:

```bash
export OCI_ACCESS_KEY_ID="tu-access-key-de-oci"
export OCI_SECRET_ACCESS_KEY="tu-secret-key-de-oci"
export OCI_NAMESPACE="tu-tenancy-namespace"
export OCI_BUCKET_NAME="telecorp-history-archive"
export OCI_COMPATIBLE_ENDPOINT="https://${OCI_NAMESPACE}.compat.objectstorage.us-ashburn-1.oraclecloud.com"
```

3. Ejecuta la sincronización:

```bash
python3 back/oci/sync_history.py --bucket telecorp-history-archive --namespace tu-tenancy-namespace
```

