# IHSStatus – extensión Machine Agent para IHS en HP-UX (mod_status)

Scrapea `/server-status?auto` de IBM HTTP Server (IHS) en HP-UX y envía métricas al **HTTP Listener** del Machine Agent de AppDynamics. Para IHS en HP-UX no se usa el Apache Agent nativo; solo mod_status en IHS y esta extensión en un host Linux.

## Requisitos

- **Host Linux** con **mínimo 1 CPU y 4 GB RAM**
- **Java 11 o superior** (Machine Agent 25.x requiere Java 11+; Java 8 no es compatible)
- **Python instalado** en el host Linux (Python 3). Dependencia: `python3 -m pip install requests`
- Machine Agent de AppDynamics con **HTTP Listener** habilitado (puerto 8293, 127.0.0.1)
- **Conectividad de red:** el host Linux debe poder **alcanzar al IHS** en HP-UX (o viceversa) para hacer el scraping de `server-status?auto`; sin conectividad no se recolectan métricas.
- IHS en HP-UX con **mod_status** habilitado y `/server-status?auto` accesible solo desde la IP del host Linux

## Instalación

1. Copiar `monitor.xml`, `run_ihs_status.sh`, `ihs_status_to_appd.py`, `env.example` y este `README.md` a:
   ```
   /opt/appdynamics/machine-agent/monitors/IHSStatus/
   ```
   (Ajustar la ruta si el Machine Agent está en otro directorio.)
2. Hacer ejecutable el wrapper: `chmod +x run_ihs_status.sh`. Si `python3` no está en `/usr/bin/python3`, editar la primera línea ejecutable en `run_ihs_status.sh` con la ruta correcta.
3. Definir las variables de entorno para el script (el Machine Agent las hereda al ejecutar la extensión):
   - Copiar `env.example` a `env.sh`, editar valores y hacer `source env.sh` antes de arrancar el Machine Agent, **o** exportarlas en el script/systemd que inicia el Machine Agent.
   - **Múltiples IHS:** `IHS_TARGETS` = lista separada por coma. Cada target: `"url|label"`.
     Ejemplo: `IHS_TARGETS="http://ihs1:80/server-status?auto|IHS-PROD-1,http://ihs2:80/server-status?auto|IHS-PROD-2"`
   - **Un solo IHS:** `IHS_STATUS_URL` + opcional `IHS_LABEL` (default `"default"`).
   - `APPD_HTTP_LISTENER`: normalmente `http://127.0.0.1:8293/api/v1/metrics`.
   - `METRIC_PREFIX`: prefijo base (ej. `Custom Metrics|Web|IHS|HPUX`).
4. Asegurar que el Machine Agent arranca con:
   ```
   -Dmetric.http.listener=true
   -Dmetric.http.listener.port=8293
   -Dmetric.http.listener.host=127.0.0.1
   ```
5. Reiniciar el Machine Agent.

## Métricas publicadas

- `BusyWorkers`, `IdleWorkers`
- `ReqPerSec`, `BytesPerSec`, `BytesPerReq`
- `TotalAccesses`, `UptimeSec`

En AppDynamics: **Metric Browser** → `Custom Metrics|Web|IHS|HPUX|{label}|...` (el `{label}` identifica cada IHS cuando se monitorean varios).

**Nota:** El HTTP Listener exige valores enteros (64-bit). Las métricas decimales (`ReqPerSec`, `BytesPerSec`, `BytesPerReq`) se envían escaladas x1000. Para visualizarlas correctamente en un dashboard, usa fórmula `valor/1000` si necesitas la escala original.

## Manual completo

Ver [§2.3 y §2.3.1 del manual de instalación](../../MANUAL_INSTALACION_APPDYNAMICS_IHS.md#23-alternativas-para-hp-ux-sin-agente-nativo) (config IHS, ACL, validación, HTTP Listener, etc.).
