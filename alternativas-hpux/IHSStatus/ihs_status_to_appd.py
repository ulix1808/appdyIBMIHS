#!/usr/bin/env python3
"""
Scrape /server-status?auto (mod_status) de IHS en HP-UX y publica métricas
al HTTP Listener del Machine Agent de AppDynamics.
Variables de entorno: IHS_STATUS_URL, APPD_HTTP_LISTENER, METRIC_PREFIX.
"""
import os
import sys
import time
import json
import requests
from typing import Dict, Any, List

# --- Helpers ------------------------------------------------------------


def parse_server_status_auto(text: str) -> Dict[str, Any]:
    """
    Parse de /server-status?auto (mod_status).
    Retorna dict con claves típicas: BusyWorkers, IdleWorkers, ReqPerSec,
    BytesPerSec, Scoreboard, etc.
    """
    data: Dict[str, Any] = {}
    for line in text.splitlines():
        if not line.strip() or ":" not in line:
            continue
        k, v = line.split(":", 1)
        k = k.strip()
        v = v.strip()
        data[k] = v

    # Convertir a números cuando aplica
    def to_int(key: str):
        if key in data:
            try:
                data[key] = int(float(str(data[key])))
            except Exception:
                pass

    def to_float(key: str):
        if key in data:
            try:
                data[key] = float(str(data[key]))
            except Exception:
                pass

    for k in ["BusyWorkers", "IdleWorkers", "Total Accesses", "Total kBytes", "Uptime"]:
        to_int(k)

    for k in ["ReqPerSec", "BytesPerSec", "BytesPerReq"]:
        to_float(k)

    return data


def make_metric_payload(metric_prefix: str, metrics: Dict[str, float]) -> Dict[str, Any]:
    """
    Payload típico para Machine Agent HTTP Listener (métricas custom).
    Estructura basada en ejemplos oficiales/repos de AppDynamics.
    """
    now_ms = int(time.time() * 1000)

    metric_list: List[Dict[str, Any]] = []
    for name, value in metrics.items():
        metric_list.append({
            "metricName": f"{metric_prefix}|{name}",
            "metricValue": float(value),
            "aggregatorType": "AVERAGE",
            "timeRollUpType": "AVERAGE",
            "clusterRollUpType": "COLLECTIVE",
            "timestamp": now_ms
        })

    return {"metrics": metric_list}


def post_metrics(listener_url: str, payload: Dict[str, Any]) -> None:
    r = requests.post(listener_url, json=payload, timeout=10)
    if r.status_code not in (200, 202, 204):
        raise RuntimeError(f"HTTP {r.status_code}: {r.text[:300]}")


# --- Main ---------------------------------------------------------------


def main() -> int:
    ihs_url = os.getenv("IHS_STATUS_URL", "").strip()
    listener_url = os.getenv("APPD_HTTP_LISTENER", "http://127.0.0.1:8293/api/v1/metrics").strip()
    metric_prefix = os.getenv("METRIC_PREFIX", "Custom Metrics|Web|IHS|HPUX").strip()

    if not ihs_url:
        print("Missing env IHS_STATUS_URL", file=sys.stderr)
        return 2

    # 1) Scrape IHS
    resp = requests.get(ihs_url, timeout=10)
    resp.raise_for_status()

    status = parse_server_status_auto(resp.text)

    # 2) Extraer métricas clave (si faltan, las omitimos)
    metrics_out: Dict[str, float] = {}

    if isinstance(status.get("BusyWorkers"), int):
        metrics_out["BusyWorkers"] = status["BusyWorkers"]
    if isinstance(status.get("IdleWorkers"), int):
        metrics_out["IdleWorkers"] = status["IdleWorkers"]
    if isinstance(status.get("ReqPerSec"), float):
        metrics_out["ReqPerSec"] = status["ReqPerSec"]
    if isinstance(status.get("BytesPerSec"), float):
        metrics_out["BytesPerSec"] = status["BytesPerSec"]
    if isinstance(status.get("BytesPerReq"), float):
        metrics_out["BytesPerReq"] = status["BytesPerReq"]
    if isinstance(status.get("Total Accesses"), int):
        metrics_out["TotalAccesses"] = status["Total Accesses"]
    if isinstance(status.get("Uptime"), int) and status["Uptime"] > 0:
        metrics_out["UptimeSec"] = status["Uptime"]

    # 3) Publicar a Machine Agent HTTP Listener
    if metrics_out:
        payload = make_metric_payload(metric_prefix, metrics_out)
        post_metrics(listener_url, payload)
        print(f"Posted {len(metrics_out)} metrics to Machine Agent listener.")
        return 0

    print("No metrics parsed from server-status?auto (check mod_status output).", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
