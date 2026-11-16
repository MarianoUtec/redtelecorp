# Análisis de especificaciones y requerimientos del proyecto – Red TeleCorp

A partir del texto proporcionado, se identifican las especificaciones, requerimientos funcionales, no funcionales, técnicos y reglas de negocio que deberá contemplar la solución propuesta para Red TeleCorp.

El proyecto consiste en desarrollar una plataforma inteligente de gestión, monitoreo y detección de incidencias en una red de telecomunicaciones, que permita integrar información de las antenas y reportes de los usuarios para detectar fallas, identificar incidentes colectivos, priorizar su atención y mantener informados a los usuarios afectados.

# 1. Especificaciones del proyecto

Las especificaciones describen las características principales que deberá tener la solución.

| Código | Especificación | Descripción |
| --- | --- | --- |
| ESP-01 | Monitoreo de antenas | El sistema deberá recibir información periódica sobre el tráfico procesado por cada antena. |
| ESP-02 | Detección de anomalías | Deberá identificar antenas caídas, saturadas e inhabilitadas mediante umbrales establecidos. |
| ESP-03 | Portal de incidencias | Deberá disponer de un portal para que los usuarios registren problemas relacionados con sus servicios. |
| ESP-04 | Gestión de incidencias | Deberá permitir consultar, administrar y actualizar las incidencias registradas. |
| ESP-05 | Detección de incidentes colectivos | Deberá identificar posibles fallas generalizadas mediante la agrupación de reportes por zona y periodo de tiempo. |
| ESP-06 | Notificaciones | Deberá comunicar a los usuarios afectados los cambios de estado de los incidentes. |
| ESP-07 | Priorización | Deberá clasificar los incidentes según su impacto y criticidad. |
| ESP-08 | Análisis geográfico | Deberá identificar las zonas con mayor concentración de incidencias. |
| ESP-09 | Análisis de recurrencia | Deberá detectar antenas e infraestructura que presentan fallas repetitivas. |
| ESP-10 | Correlación de información | Deberá relacionar los reportes de los usuarios con las métricas de las antenas. |
| ESP-11 | Gestión de eventos simultáneos | Deberá soportar grandes cantidades de reportes e información generados simultáneamente. |
| ESP-12 | Información histórica | Deberá almacenar información para analizar la evolución y comportamiento de los incidentes. |
| ESP-13 | Escalabilidad | Deberá permitir el crecimiento de usuarios, antenas y eventos registrados. |
| ESP-14 | Optimización de costos | Deberá minimizar los costos operativos y evitar depender de infraestructura permanentemente encendida. |

# 2. Requerimientos funcionales

Los requerimientos funcionales describen las acciones y operaciones que el sistema deberá realizar.

## 2.1. Módulo de monitoreo de antenas

| Código | Requerimiento funcional |
| --- | --- |
| RF-01 | El sistema deberá recibir periódicamente las métricas de tráfico generadas por cada antena. |
| RF-02 | El sistema deberá identificar cada antena mediante un identificador único. |
| RF-03 | El sistema deberá evaluar el tráfico registrado por cada antena. |
| RF-04 | El sistema deberá identificar antenas caídas cuando registren menos de 60 GB por minuto. |
| RF-05 | El sistema deberá identificar antenas saturadas cuando registren más de 129 GB por minuto. |
| RF-06 | El sistema deberá identificar antenas inhabilitadas cuando registren 0 GB por minuto. |
| RF-07 | El sistema deberá identificar las antenas que operan dentro de los parámetros normales establecidos. |
| RF-08 | El sistema deberá registrar el historial de comportamiento de cada antena. |
| RF-09 | El sistema deberá generar alertas cuando se detecten anomalías en las métricas de las antenas. |

Reglas de negocio para la clasificación de antenas:

## Umbrales de tráfico

Inhabilitada

0 GB/min

La antena no registra tráfico.

Caída

Menos de 60 GB/min

La antena registra un tráfico inferior al umbral mínimo.

Funcionamiento normal

60 a 129 GB/min

La antena opera dentro de los parámetros establecidos.

Saturada

Más de 129 GB/min

La antena supera el umbral máximo establecido.

Observación: La clasificación de antena caída e inhabilitada presenta una superposición: 0 GB/min también es menor que 60 GB/min. Para evitar ambigüedades, se recomienda evaluar primero si el tráfico es 0 y luego aplicar el umbral de caída.

## 2.2. Módulo de registro de incidencias

| Código | Requerimiento funcional |
| --- | --- |
| RF-10 | El sistema deberá permitir que los usuarios registren incidencias relacionadas con sus servicios. |
| RF-11 | El sistema deberá solicitar la identificación del usuario. |
| RF-12 | El sistema deberá solicitar el número asociado al servicio. |
| RF-13 | El sistema deberá permitir registrar la ubicación aproximada del inconveniente. |
| RF-14 | El sistema deberá registrar la fecha y hora del incidente. |
| RF-15 | El sistema deberá permitir seleccionar el tipo de problema. |
| RF-16 | El sistema deberá permitir ingresar una descripción del inconveniente. |
| RF-17 | El sistema deberá generar un identificador único para cada incidencia. |
| RF-18 | El sistema deberá permitir consultar las incidencias registradas. |
| RF-19 | El sistema deberá permitir administrar y actualizar las incidencias. |

## 2.3. Módulo de gestión y seguimiento de incidencias

| Código | Requerimiento funcional |
| --- | --- |
| RF-20 | El sistema deberá asignar un estado inicial a cada incidencia. |
| RF-21 | El sistema deberá permitir cambiar el estado de una incidencia. |
| RF-22 | El sistema deberá permitir consultar el estado actual de cada incidencia. |
| RF-23 | El sistema deberá registrar los cambios de estado realizados. |
| RF-24 | El sistema deberá conservar un historial cronológico de cada incidencia. |

Estados establecidos para las incidencias:

1. Registrada.
2. En revisión.
3. Siendo atendida.
4. Solucionada.
5. Cerrada.

## 2.4. Módulo de detección de incidentes colectivos

| Código | Requerimiento funcional |
| --- | --- |
| RF-25 | El sistema deberá agrupar reportes de usuarios según su ubicación geográfica. |
| RF-26 | El sistema deberá identificar reportes relacionados con un mismo tipo de inconveniente o servicio. |
| RF-27 | El sistema deberá contabilizar los usuarios diferentes que reportan problemas en una misma zona. |
| RF-28 | El sistema deberá identificar posibles incidentes colectivos cuando existan 10 o más usuarios diferentes afectados en una misma zona dentro de un intervalo menor a 24 horas. |
| RF-29 | El sistema deberá generar una alerta cuando se cumpla la condición de incidente colectivo. |
| RF-30 | El sistema deberá permitir verificar la infraestructura relacionada con la zona afectada. |
| RF-31 | El sistema deberá relacionar las incidencias individuales con el incidente colectivo correspondiente. |

Regla de negocio principal:

Un incidente deberá ser considerado un posible incidente colectivo cuando cumpla las siguientes condiciones:

- Existan 10 o más usuarios diferentes.
- Los usuarios reporten inconvenientes relacionados con el servicio.
- Los reportes correspondan a una misma zona geográfica.
- Los reportes se hayan generado en un intervalo menor a 24 horas.

## 2.5. Módulo de notificaciones

| Código | Requerimiento funcional |
| --- | --- |
| RF-32 | El sistema deberá identificar a los usuarios que reportaron problemas en una zona afectada. |
| RF-33 | El sistema deberá permitir enviar notificaciones por correo electrónico. |
| RF-34 | El sistema deberá permitir enviar notificaciones al teléfono celular. |
| RF-35 | El sistema deberá comunicar cuando un inconveniente esté siendo evaluado. |
| RF-36 | El sistema deberá comunicar cuando se identifique una incidencia en la zona. |
| RF-37 | El sistema deberá comunicar cuando el servicio haya sido restablecido. |
| RF-38 | El sistema deberá actualizar las comunicaciones según el estado del incidente. |

## 2.6. Módulo de priorización de incidencias

| Código | Requerimiento funcional |
| --- | --- |
| RF-39 | El sistema deberá determinar la cantidad de usuarios afectados por cada incidente. |
| RF-40 | El sistema deberá considerar la ubicación geográfica del incidente. |
| RF-41 | El sistema deberá identificar zonas críticas como industriales, educativas, médicas y de servicios esenciales. |
| RF-42 | El sistema deberá asignar niveles de prioridad a los incidentes. |
| RF-43 | El sistema deberá permitir ordenar los incidentes según su prioridad. |

## 2.7. Módulo de análisis y estadísticas

| Código | Requerimiento funcional |
| --- | --- |
| RF-44 | El sistema deberá identificar las zonas geográficas con mayor cantidad de incidencias. |
| RF-45 | El sistema deberá identificar las antenas que presentan problemas con mayor frecuencia. |
| RF-46 | El sistema deberá identificar los tipos de inconvenientes más reportados. |
| RF-47 | El sistema deberá generar información estadística sobre las incidencias. |
| RF-48 | El sistema deberá permitir analizar la evolución histórica de los incidentes. |
| RF-49 | El sistema deberá calcular el tiempo de duración de cada incidente. |
| RF-50 | El sistema deberá determinar la cantidad de usuarios afectados por cada incidente. |
| RF-51 | El sistema deberá identificar patrones de fallas recurrentes en la infraestructura. |

## 2.8. Módulo de correlación y detección de fallas

| Código | Requerimiento funcional |
| --- | --- |
| RF-52 | El sistema deberá relacionar los reportes de los usuarios con las métricas generadas por las antenas. |
| RF-53 | El sistema deberá identificar posibles coincidencias entre fallas de infraestructura y reportes de usuarios. |
| RF-54 | El sistema deberá detectar problemas de infraestructura que se repitan durante diferentes días. |
| RF-55 | El sistema deberá identificar posibles problemas estructurales en antenas que presenten fallas recurrentes. |
| RF-56 | El sistema deberá generar alertas ante posibles fallas estructurales. |

# 3. Requerimientos no funcionales

Estos requerimientos establecen las condiciones de calidad y operación que deberá cumplir la solución.

| Código | Requerimiento | Descripción |
| --- | --- | --- |
| RNF-01 | Escalabilidad | La solución deberá soportar el crecimiento de usuarios, antenas y eventos. |
| RNF-02 | Rendimiento | Deberá procesar grandes volúmenes de información de manera oportuna. |
| RNF-03 | Disponibilidad | Deberá mantener accesibles sus funcionalidades durante la operación. |
| RNF-04 | Tolerancia a fallos | Deberá evitar la pérdida de registros cuando se produzcan múltiples incidentes simultáneamente. |
| RNF-05 | Eficiencia | Deberá utilizar eficientemente los recursos computacionales. |
| RNF-06 | Optimización económica | Deberá minimizar los costos de infraestructura y operación. |
| RNF-07 | Flexibilidad | Deberá permitir incorporar nuevos usuarios, antenas y fuentes de información. |
| RNF-08 | Persistencia | Deberá conservar la información histórica de las incidencias y métricas. |
| RNF-09 | Seguridad | Deberá proteger la información de identificación y contacto de los usuarios. |
| RNF-10 | Trazabilidad | Deberá permitir conocer las modificaciones y evolución de cada incidencia. |
| RNF-11 | Automatización | Deberá automatizar la detección de anomalías y la identificación de incidentes colectivos. |
| RNF-12 | Sostenibilidad | Deberá evitar depender de infraestructura permanentemente encendida. |

# 4. Requerimientos de información y datos

A partir del texto, se pueden identificar los principales datos que necesitará gestionar el sistema.

| Entidad | Datos principales |
| --- | --- |
| Usuario | Identificación, número de servicio, correo electrónico y teléfono celular. |
| Antena | Identificador, ubicación, estado y métricas de tráfico. |
| Métrica de antena | Antena asociada, cantidad de tráfico, fecha y hora de medición. |
| Incidencia | Código, usuario, ubicación, fecha, hora, tipo de problema, descripción y estado. |
| Incidente colectivo | Código, zona afectada, cantidad de usuarios, incidencias relacionadas y estado. |
| Historial | Incidencia asociada, estado anterior, estado nuevo, fecha y hora del cambio. |
| Notificación | Usuario destinatario, canal, mensaje, fecha de envío y estado de entrega. |
| Prioridad | Incidente asociado, cantidad de afectados, criticidad de la zona y nivel asignado. |

# 5. Reglas de negocio identificadas

Estas reglas son especialmente importantes porque definen cómo deberá comportarse el sistema independientemente de la tecnología utilizada.

| Código | Regla de negocio |
| --- | --- |
| RN-01 | Una antena con 0 GB/min se considera inhabilitada. |
| RN-02 | Una antena con menos de 60 GB/min se considera caída, salvo que registre exactamente 0 GB/min. |
| RN-03 | Una antena con más de 129 GB/min se considera saturada. |
| RN-04 | Una antena con tráfico entre 60 y 129 GB/min, inclusive, opera dentro de los parámetros normales. |
| RN-05 | Cada incidencia debe estar asociada a un usuario y tener un identificador único. |
| RN-06 | Cada incidencia debe mantener uno de los estados establecidos. |
| RN-07 | Todo cambio de estado deberá conservarse en el historial. |
| RN-08 | Diez o más usuarios diferentes que reporten inconvenientes relacionados con el servicio en una misma zona en menos de 24 horas generan un posible incidente colectivo. |
| RN-09 | Los usuarios que reportaron problemas en una zona afectada deberán poder recibir comunicaciones sobre el incidente. |
| RN-10 | La prioridad deberá considerar la cantidad de usuarios afectados y la criticidad de la zona. |
| RN-11 | Las fallas repetitivas de una antena deberán ser consideradas para identificar posibles problemas estructurales. |
| RN-12 | Los incidentes deberán conservar información histórica para su análisis posterior. |

# 6. Restricciones y condiciones del proyecto

- Costos: se debe buscar una infraestructura de bajo costo operativo.
- Escalabilidad: la solución debe poder crecer conforme aumente la cantidad de usuarios y eventos.
- Infraestructura: se debe evitar depender de servidores o recursos permanentemente encendidos.
- Procesamiento: se debe contemplar la recepción de grandes volúmenes de información.
- Concurrencia: se deben gestionar múltiples incidentes simultáneos.
- Integración: se deben considerar diferentes fuentes de información: antenas, usuarios y sistemas internos.
- Persistencia: no debe producirse pérdida de registros durante picos de eventos.

# 7. Componentes o módulos principales del sistema

Considerando todos los requerimientos, la arquitectura funcional del proyecto podría organizarse en los siguientes módulos:

PLATAFORMA DE GESTIÓN DE INCIDENCIAS – RED TELECORP

Sistema central

Monitoreo de antenas

Métricas y anomalías

Portal de usuarios

Registro de incidencias

Gestión de incidentes

Estados e historial

Detección colectiva

Agrupación y correlación

Notificaciones

Correo y teléfono

Analítica

Estadísticas y recurrencia

Almacenamiento de información

Usuarios, antenas, incidencias, métricas e historial

# 8\. Requerimientos y definiciones técnicas establecidas

A continuación se formalizan las definiciones técnicas y reglas operativas para los aspectos clave del sistema, asegurando la viabilidad en un entorno serverless y optimizado para la operación de Red TeleCorp.

| Aspecto | Especificación técnica definida |
| --- | --- |
| **Autenticación** | Implementación de **Custom Lambda Authorizer** con validación de tokens **JWT** en Serverless Lambda para usuarios y administradores. |
| **Ubicación** | División geográfica por **cuadrantes / geoceldas (Geohash o ID de Zona/Distrito)** mapeadas a las áreas de cobertura de las antenas. |
| **Tipos de incidencia** | Catálogo estandarizado: 1. Sin señal / Cobertura nula; 2. Degradación de datos / Internet lento; 3. Caída / Corte de llamadas de voz; 4. Falla en mensajería SMS; 5. Intermitencia recurrente de servicio. |
| **Priorización** | Matriz de 4 niveles (**P1 Crítica, P2 Alta, P3 Media, P4 Baja**) calculada según criticidad de la zona (médica, industrial, educativa) y número de usuarios afectados. |
| **Recurrencia** | Una antena o sector se marca como **falla estructural** si acumula **3 o más anomalías (caída/saturación) en 7 días móviles** o **2 anomalías en 48 horas**. |
| **Correlación** | Asociación espacio-temporal automática: vinculación de reportes de una misma zona con las métricas de la antena asociada en una ventana de **±60 minutos**. |
| **Notificaciones** | **Notificaciones automáticas** disparadas por eventos y cambios de estado (vía **Amazon SNS** a Email y SMS) a los usuarios afectados. |
| **Rendimiento** | Procesamiento asíncrono orientado a eventos, latencia de endpoints REST < 400 ms, procesamiento de eventos/lotes < 2 s, tolerancia a ráfagas concurrentes. |
| **Seguridad** | **Control de Acceso Basado en Roles (RBAC)** con roles `USUARIO`, `OPERADOR` y `ADMINISTRADOR`. Cifrado en tránsito (TLS 1.3) y reposo; principio de mínimo privilegio. |
| **Infraestructura** | Arquitectura **Serverless híbrida**: Lambdas en **Python**, **Amazon SNS** y **Step Functions** en AWS (usando `LabRole`), soporte/persistencia en **OCI**, y capa de borde/seguridad con **Cloudflare**. Despliegue mediante `serverless.yml`. |

---

## 8.1. Autenticación (JWT Lambda Authorizer)
- **Mecanismo:** La API estará protegida por un **Lambda Authorizer (TOKEN/REQUEST Authorizer)** desarrollado en Python.
- **Funcionamiento:**
  - El cliente envía en el encabezado `Authorization: Bearer <token_jwt>`.
  - La función Lambda Authorizer valida la firma criptográfica (algoritmo HMAC-SHA256 o RSA256), expiración (`exp`) y claims del token sin consultar bases de datos en cada llamada (stateless).
  - Emite una política IAM generada dinámicamente (`Allow`/`Deny`) y contexto inyectado (`userId`, `role`, `email`) para la función Lambda aguas abajo.
- **Perfiles soportados:** Clientes finales (usuarios del servicio) y personal técnico/operativo de Red TeleCorp.

## 8.2. Ubicación y Zonificación Geográfica
- **Criterio de agrupación:** Para determinar qué reportes e incidencias pertenecen a una misma zona geográfica, se utilizará un sistema de **Zonas / Celdas de Cobertura**:
  - Cada antena física posee un `antenna_id` y una cobertura delimitada por una `zone_id` (código de cuadrante o geocelda Geohash de precisión 6 ~1.2 km x 0.6 km).
  - En el portal de usuario, el usuario podrá indicar su ubicación mediante geolocalización de dispositivo (latitud/longitud) o seleccionando su distrito/sector. El sistema mapea automáticamente las coordenadas al `zone_id` y a las antenas que cubren dicho cuadrante.
  - Los reportes con el mismo `zone_id` se consolidan para la evaluación de incidentes colectivos (umbral de 10 reportes en < 24 h).

## 8.3. Catálogo de Tipos de Incidencia
El portal de usuario dispondrá de un catálogo estandarizado para evitar ambigüedades en la clasificación y agilizar el procesamiento:
1. `SIN_COBERTURA`: Sin señal celular ni conexión básica de red.
2. `INTERNET_LENTO`: Conexión de datos con alta latencia, pérdida de paquetes o velocidad degradada.
3. `FALLA_LLAMADAS`: Caída de llamadas, entrecortadas o imposibilidad de emitir/recibir voz.
4. `FALLA_SMS`: Imposibilidad de envío o recepción de mensajes cortos.
5. `INTERMITENCIA`: Pérdida y reconexión constante del servicio en lapsos cortos.

## 8.4. Matriz y Reglas de Priorización
La prioridad de atención se calculará dinámicamente mediante la combinación del impacto poblacional y la criticidad del sector:
- **Clasificación de zonas:**
  - *Crítica (Peso 3):* Centros de salud/hospitales, zonas industriales estratégicas, servicios de emergencia y seguridad.
  - *Alta (Peso 2):* Zonas comerciales de alta densidad e instituciones educativas.
  - *Estándar (Peso 1):* Áreas residenciales comunes y suburbanas.
- **Niveles de Prioridad:**
  - **P1 - Crítica:** Incidentes colectivos (≥10 usuarios) en zonas de criticidad Alta/Crítica, o antenas inhabilitadas (0 GB/min) que alimentan infraestructura crítica.
  - **P2 - Alta:** Incidentes colectivos en zonas estándar, o incidentes individuales múltiples (5-9 usuarios) en zonas críticas.
  - **P3 - Media:** Incidentes individuales menores (2-4 usuarios) o degradaciones de servicio leves en zonas estándar.
  - **P4 - Baja:** Reportes aislados individuales (1 usuario) sin impacto reportado en la infraestructura cercana.

## 8.5. Criterios de Recurrencia y Falla Estructural
Para identificar problemas estructurales que requieren mantenimiento correctivo mayor:
- **Regla de Recurrencia:** Se declara estado de **Alerta de Falla Estructural** cuando:
  - Una antena registra **3 o más transiciones a estado Caída o Saturada en un período de 7 días continuos**, o
  - Una antena presenta **2 caídas completas dentro de un margen de 48 horas**.
- **Acción:** El sistema genera un ticket técnico de revisión de infraestructura física/energética, independientemente de que la antena retorne temporalmente a su estado normal.

## 8.6. Correlación Espacio-Temporal (Antenas y Reportes)
- **Mecanismo:** Un módulo de correlación evalúa si los reportes de los usuarios coinciden temporal y espacialmente con las anomalías de tráfico de las antenas:
  - **Ventana temporal:** Intervalo de **±60 minutos** entre la generación del reporte y la métrica de tráfico anómala.
  - **Asociación espacial:** Vinculación por `zone_id` y cercanía a la antena.
  - **Regla de coincidencia:** Si los usuarios reportan `SIN_COBERTURA` o `INTERNET_LENTO` y la antena de la zona está en estado **Caída (< 60 GB/min)**, **Inhabilitada (0 GB/min)** o **Saturada (> 129 GB/min)**, el sistema confirma automáticamente la causa raíz y asocia los reportes al evento de red.

## 8.7. Sistema de Notificaciones Automáticas
- **Frecuencia y disparo:** Las notificaciones **se ejecutan de manera 100% automática** inmediatamente después de que ocurre un evento de red o cambio de estado de incidencia.
- **Disparadores de notificación:**
  1. *Registro exitoso:* Confirmación inmediata con código de ticket al usuario.
  2. *Detección de Incidente Colectivo:* Notificación a los usuarios de la zona indicando que la falla fue identificada y está siendo atendida.
  3. *Cambio de estado:* Transiciones de estado (`En revisión` -> `Siendo atendida` -> `Solucionada` -> `Cerrada`).
  4. *Restablecimiento del servicio:* Confirmación de normalización del tráfico en antena y cierre del incidente colectivo.
- **Canales:** Publicación a temas de **Amazon SNS**, con despacho a Correo Electrónico (Amazon SES / SNS Email) y SMS.

## 8.8. Parámetros de Rendimiento y Capacidad
- **Latencia de API:** Tiempo de respuesta en endpoints REST inferior a **400 ms** para el registro y consulta de tickets.
- **Tiempo de correlación y detección colectiva:** Procesamiento en menos de **2 segundos** desde la recepción del décimo reporte o de la métrica de antena.
- **Resiliencia ante ráfagas:** Arquitectura desacoplada y basada en eventos (Event-Driven) para absorber picos súbitos de miles de reportes simultáneos sin bloqueo de base de datos ni pérdida de peticiones.

## 8.9. Seguridad y Control de Acceso Basado en Roles (RBAC)
- **Modelo de acceso (RBAC):**
  - `USUARIO`: Registrar incidencias propias, consultar estado e historial de sus reportes.
  - `OPERADOR / TÉCNICO`: Consultar tablero de incidentes colectivos, actualizar estados de incidentes de su zona asignada y validar estado de antenas.
  - `ADMINISTRADOR`: Gestión completa de infraestructura, ajuste de umbrales de tráfico, auditoría de logs y analítica global.
- **Protección de datos:** Cifrado en tránsito estricto mediante **TLS 1.3** a través de Cloudflare; datos sensibles de usuarios (teléfono, correo) protegidos y tokenizados en reposo.

## 8.10. Infraestructura Serverless Híbrida
- **Cómputo:** Funciones **AWS Lambda en Python (3.11/3.12)** para authorizers, ingesta de métricas, lógica de negocio y APIs REST.
- **Orquestación:** **AWS Step Functions** para coordinar flujos de trabajo complejos (evaluación de umbrales, agrupación de reportes colectivos y correlación espacio-temporal).
- **Mensajería y Eventos:** **Amazon SNS** para la distribución de alertas y notificaciones a usuarios y personal de soporte.
- **Seguridad perimetral y CDN:** **Cloudflare** para administración de DNS, mitigación DDoS, WAF, gestión de certificados SSL/TLS y proxy seguro hacia el frontend y backend.
- **Nube secundaria / Persistencia:** Integración con **OCI** (Oracle Cloud Infrastructure) para almacenamiento histórico o servicios de respaldo aprovechando tiers gratuitos/estudiantiles.
- **Infraestructura como Código (IaC):** Automatización total mediante **Serverless Framework (`serverless.yml`)** configurado con el rol preexistente **`LabRole`** de AWS Academy.

# 9\. Priorización de los requerimientos para la hackathon

| Prioridad | Funcionalidades |
| --- | --- |
| Alta (MVP) | Monitoreo de antenas, clasificación por umbrales, registro de incidencias, gestión de estados y detección de incidentes colectivos. |
| Media | Notificaciones automáticas, priorización por impacto, correlación entre antenas y usuarios. |
| Complementaria | Estadísticas avanzadas, análisis de recurrencia, patrones históricos y optimización predictiva. |

## 10\. Conclusión del análisis

El proyecto Red TeleCorp requiere desarrollar una plataforma que integre el monitoreo de infraestructura de telecomunicaciones con la gestión de incidencias reportadas por los usuarios.

El aspecto más importante del proyecto no es únicamente registrar fallas, sino detectar automáticamente cuándo múltiples reportes individuales representan un problema colectivo, relacionarlos con las métricas de las antenas y facilitar una respuesta operativa oportuna.

Asimismo, la solución deberá contar con capacidades de escalabilidad, procesamiento de eventos simultáneos, almacenamiento histórico y optimización de costos.

1. Monitoreo automático de antenas y detección de anomalías.
2. Detección de incidentes colectivos mediante la agrupación de reportes por zona y tiempo.
3. Gestión y seguimiento de incidencias con notificaciones a los usuarios afectados.

Estos tres elementos representan el mayor valor funcional del proyecto y permiten construir posteriormente los módulos de analítica, recurrencia y priorización avanzada.

Nota: Este documento distingue los requerimientos funcionales del enunciado base y formaliza en la Sección 8 las decisiones técnicas y arquitectónicas elegidas para la solución (Serverless Lambda en Python, AWS Step Functions, Amazon SNS, Cloudflare, OCI y despliegue con Serverless Framework bajo la política LabRole para tier de estudiantes).
