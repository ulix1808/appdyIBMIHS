# IHSStatus – extensión Machine Agent para IHS en HP-UX (mod_status)

Scrapea `/server-status?auto` de IBM HTTP Server (IHS) en HP-UX y envía métricas al **HTTP Listener** del Machine Agent de AppDynamics. Para IHS en HP-UX no se usa el Apache Agent nativo; solo mod_status en IHS y esta extensión en un host Linux.

## Requisitos

- **Host Linux** con **mínimo 1 CPU y 4 GB RAM**
- **Python instalado** en el host Linux (Python 3). Dependencia: `python3 -m pip install requests`
- Machine Agent de AppDynamics con **HTTP Listener** habilitado (puerto 8293, 127.0.0.1)
- **Conectividad de red:** el host Linux debe poder **alcanzar al IHS** en HP-UX (o viceversa) para hacer el scraping de `server-status?auto`; sin conectividad no se recolectan métricas.
- IHS en HP-UX con **mod_status** habilitado y `/server-status?auto` accesible solo desde la IP del host Linux

## Instalación

1. Copiar `monitor.xml`, `ihs_status_to_appd.py`, `env.example` y este `README.md` a:
   ```
   /opt/appdynamics/machine-agent/monitors/IHSStatus/
   ```
   (Ajustar la ruta si el Machine Agent está en otro directorio.)
2. Editar `monitor.xml`: actualizar la ruta en `<argument>` al script Python según tu instalación (ej. `/opt/appdynamics/machine-agent/monitors/IHSStatus/ihs_status_to_appd.py`). Si `python3` no está en `/usr/bin/python3`, cambiar también `<executable>`.
3. Definir las variables de entorno para el script (el Machine Agent las hereda al ejecutar la extensión):
   - Copiar `env.example` a `env.sh`, editar valores y hacer `source env.sh` antes de arrancar el Machine Agent, **o** exportarlas en el script/systemd que inicia el Machine Agent.
   - `IHS_STATUS_URL`: URL completa de `server-status?auto` del IHS (IP/puerto del HP-UX).
   - `APPD_HTTP_LISTENER`: normalmente `http://127.0.0.1:8293/api/v1/metrics`.
   - `METRIC_PREFIX`: prefijo de métricas en el Controller (ej. `Custom Metrics|Web|IHS|HPUX`).
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

En AppDynamics: **Metric Browser** → `Custom Metrics|Web|IHS|HPUX|...` (o el prefijo configurado).

## Manual completo

Ver [§2.3 y §2.3.1 del manual de instalación](../../MANUAL_INSTALACION_APPDYNAMICS_IHS.md#23-alternativas-para-hp-ux-sin-agente-nativo) (config IHS, ACL, validación, HTTP Listener, etc.).
