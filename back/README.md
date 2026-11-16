# Backend Serverless – Red TeleCorp
## Detección y Gestión Inteligente de Incidencias en Redes de Telecomunicaciones

Backend 100% Serverless, basado en eventos (Event-Driven Architecture) y optimizado para **AWS Academy Learner Lab (`LabRole`)**, con distribución multicloud pragmática que incorpora **Amazon Web Services (AWS)** y **Oracle Cloud Infrastructure (OCI) Always Free**.

---

## 1. Arquitectura y Stack Tecnológico

- **Cómputo Serverless:** AWS Lambda en **Python 3.11** con bajo tiempo de arranque en frío (cold start) y asignación de memoria eficiente (128 MB a 256 MB). Arquitectura modular basada en paquetes de espacio de nombres implícitos (PEP 420), sin depender de archivos `__init__.py`, evitando conflictos de empaquetado y resolución de rutas en el runtime de Lambda.
- **Control de Acceso (RBAC):** Lambda Authorizer para validación stateless de tokens **JWT** (HMAC-SHA256) con claims de rol (`USUARIO`, `OPERADOR`, `ADMINISTRADOR`).
- **Orquestación de Procesos:** **AWS Step Functions** para la máquina de estados de detección colectiva y correlación espacio-temporal.
- **Mensajería Pub/Sub:** **Amazon SNS** (`telecorp-incident-events`, `telecorp-collective-alerts`, `telecorp-user-notifications`).
- **Persistencia NoSQL:** **Amazon DynamoDB** en modo On-Demand (`PAY_PER_REQUEST` – \$0 de costo en reposo).
- **Capa Histórica Multicloud:** **OCI Object Storage Always Free** para archivo comprimido a largo plazo de métricas e incidencias cerradas.
- **Infraestructura como Código (IaC):** **Serverless Framework (`serverless.yml`)** configurado de forma centralizada con el rol preexistente **`LabRole`** de AWS Academy.

---

## 2. Estructura de Directorios

```text
back/
├── aws/
│   ├── serverless.yml           # Definición completa de IaC para AWS (usando LabRole)
│   ├── package.json             # Dependencias de plugins Serverless
│   ├── requirements.txt         # Librerías Python de producción
│   └── src/
│       ├── common/
│       │   ├── models.py        # Modelos, enums, matriz de prioridad y umbrales de tráfico
│       │   ├── zones.py         # Catálogo geográfico, criticidad y resolución espacial
│       │   ├── jwt_utils.py     # Criptografía JWT (HMAC-SHA256, emisión y validación)
│       │   ├── response.py      # Formateador HTTP estándar API Gateway con CORS y Decimals
│       │   ├── db.py            # Cliente unificado DynamoDB (Boto3 real y Mock en memoria)
│       │   └── sns_client.py    # Cliente unificado Amazon SNS
│       ├── auth/
│       │   ├── authorizer.py    # Lambda Authorizer stateless para API Gateway
│       │   └── login.py         # POST /auth/login (emisión de tokens para demo/roles)
│       ├── incidents/
│       │   ├── create.py        # POST /incidents (alta de tickets y notificación inicial)
│       │   ├── get_by_user.py   # GET /incidents/my-reports (reportes del usuario)
│       │   ├── get_incident.py  # GET /incidents/{id} (detalle e historial completo)
│       │   ├── list_incidents.py# GET /incidents (búsqueda con filtros para NOC)
│       │   └── update_status.py # PATCH /incidents/{id}/status (cambio de estado y aviso)
│       ├── antennas/
│       │   ├── ingest.py        # POST /antennas/metrics (umbrales y falla estructural)
│       │   └── list_antennas.py # GET /antennas y GET /antennas/{id}/metrics (estado de red)
│       ├── analytics/
│       │   ├── evaluate_group.py# Detección colectiva (>=10 usuarios) y correlación antena
│       │   ├── summary.py       # GET /analytics/summary (rankings, zonas críticas y métricas)
│       │   └── collective.py    # GET /collective-events (tablero de fallas colectivas)
│       └── notifications/
│           └── worker.py        # Consumidor SNS para despacho automático SMS y Email
├── oci/
│   ├── sync_history.py          # Script de exportación y respaldo a OCI Object Storage
│   └── README.md                # Guía de configuración para OCI Always Free
├── scripts/
│   ├── seed_data.py             # Script de carga inicial de antenas, reportes y tokens
│   └── simulate_storm.py        # Simulación de ráfaga/tormenta de fallas masivas
├── tests/                       # Suite completa de pruebas unitarias y de integración
│   ├── conftest.py
│   ├── test_auth.py
│   ├── test_antennas.py
│   ├── test_incidents.py
│   ├── test_correlation.py
│   ├── test_analytics.py
│   ├── test_notifications.py
│   └── test_oci.py
├── pytest.ini
└── README.md
```

---

## 3. Catálogo de Endpoints REST

| Método | Ruta | Autorización | Descripción |
| :--- | :--- | :--- | :--- |
| **POST** | `/auth/login` | Pública | Autenticación y obtención de token JWT para `USUARIO`, `OPERADOR` o `ADMINISTRADOR`. |
| **POST** | `/incidents` | `Bearer JWT` | Registra una nueva incidencia individual, emite código de ticket y envía notificación. |
| **GET** | `/incidents/my-reports` | `Bearer JWT` | Lista las incidencias reportadas por el usuario autenticado. |
| **GET** | `/incidents/{id}` | `Bearer JWT` | Detalle completo de una incidencia, historial de transiciones y contexto colectivo. |
| **GET** | `/incidents` | `Bearer JWT (Operador/Admin)` | Lista todas las incidencias con filtros opcionales (`zone_id`, `status`, `problem_type`). |
| **PATCH**| `/incidents/{id}/status`| `Bearer JWT (Operador/Admin)` | Actualiza el estado de la incidencia, agrega nota al historial y notifica al usuario. |
| **POST** | `/antennas/metrics` | Pública / API Key | Ingesta de tráfico de antenas (GB/min), clasificación de umbrales y evaluación estructural. |
| **GET** | `/antennas` | Pública / Dashboard | Lista todas las antenas, estado operativo actual, tráfico y alertas estructurales. |
| **GET** | `/antennas/{id}/metrics` | Pública / Dashboard | Historial cronológico de telemetría de una antena específica. |
| **GET** | `/analytics/summary` | Pública / Dashboard | Resumen analítico global: top zonas afectadas, problemas frecuentes y antenas críticas. |
| **GET** | `/collective-events` | Pública / Dashboard | Lista de incidentes colectivos activos y resueltos. |

---

## 4. Reglas de Negocio Implementadas

### 4.1. Umbrales de Antenas (RN-01 a RN-04)
- **`0 GB/min`:** `INHABILITADA` (Evaluado primero para eliminar ambigüedades).
- **`< 60 GB/min`:** `CAIDA`.
- **`60 a 129 GB/min`:** `NORMAL` (Funcionamiento óptimo).
- **`> 129 GB/min`:** `SATURADA`.

### 4.2. Detección de Falla Estructural y Recurrencia (RN-11, Sección 8.5)
Una antena se clasifica en estado de **Alerta de Falla Estructural** cuando:
- Acumula **3 o más anomalías** (`CAIDA`, `SATURADA` o `INHABILITADA`) en **7 días continuos**, o
- Presenta **2 caídas completas** (`CAIDA` o `INHABILITADA`) en un lapso de **48 horas**.

### 4.3. Detección de Incidentes Colectivos (RN-08)
- Agrupación por cuadrante geográfico (`zone_id`).
- Ventana temporal menor a **24 horas**.
- Umbral crítico: **10 o más usuarios distintos** reportando problemas en la misma zona.
- Acción: Generación de ticket colectivo (`COL#YYYYMMDD-{zone_id}`), vinculación de tickets individuales y despacho de notificación masiva.

### 4.4. Correlación Espacio-Temporal (Sección 8.6)
- Ventana de **±60 minutos** entre la telemetría de la antena y los reportes de los usuarios.
- Coincidencia de causa raíz: Si los reportes indican `SIN_COBERTURA` o `INTERNET_LENTO` y la antena está `CAIDA`, `SATURADA` o `INHABILITADA`, se confirma la falla de infraestructura.

### 4.5. Matriz de Priorización Dinámica (Sección 8.4)
- **`P1 - Crítica`:** Incidentes colectivos (≥10 usuarios) en zonas de criticidad Alta o Crítica (hospitales, industrias), o antenas inhabilitadas (0 GB/min) en infraestructura crítica.
- **`P2 - Alta`:** Incidentes colectivos en zonas estándar, o múltiples reportes (5-9 usuarios) en zonas críticas.
- **`P3 - Media`:** Incidentes menores (2-4 usuarios), o degradación leve en zonas estándar.
- **`P4 - Baja`:** Reportes aislados (1 usuario) sin impacto confirmado en infraestructura.

---

## 5. Ejecución Local y Pruebas Unitarias

El backend incluye una capa mock en memoria de alta fidelidad para DynamoDB y Amazon SNS, lo que permite ejecutar todas las pruebas y simulaciones de inmediato **sin necesidad de credenciales de AWS ni LocalStack**:

### Ejecutar Suite Completa de Tests (Pytest)
```bash
# Desde la raíz del repositorio o de la carpeta back:
pytest back/
```
*Resultado: 23 pruebas unitarias y de integración pasando al 100% en menos de 0.1 segundos.*

### Cargar Datos Semilla para Demostración
```bash
python3 back/scripts/seed_data.py
```

### Simular Tormenta de Reportes y Detección en Tiempo Real
```bash
python3 back/scripts/simulate_storm.py
```

### Exportar Datos Históricos a OCI Always Free (Modo Simulación)
```bash
python3 back/oci/sync_history.py --dry-run
```

---

## 6. Despliegue en AWS Academy (`LabRole`)

El archivo `serverless.yml` cuenta con la directiva obligatoria para cuentas de AWS Academy:

```yaml
provider:
  name: aws
  runtime: python3.11
  region: us-east-1
  iam:
    role: arn:aws:iam::${aws:accountId}:role/LabRole
```

Para desplegar en la nube:
```bash
cd back/aws
npm install
serverless deploy --stage dev
```

