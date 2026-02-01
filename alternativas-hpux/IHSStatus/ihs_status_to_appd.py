#!/usr/bin/env python3
"""
Scrape /server-status?auto (mod_status) de 1 o N instancias IHS y publica métricas
al HTTP Listener del Machine Agent de AppDynamics.

Variables de entorno:
  - IHS_TARGETS: (recomendado) Lista de targets separada por coma. Cada target: "url|label".
    Ejemplo: IHS_TARGETS="http://ihs1:80/server-status?auto|IHS-PROD-1,http://ihs2:80/server-status?auto|IHS-PROD-2"
  - IHS_STATUS_URL + IHS_LABEL: (legacy, 1 solo IHS) URL y etiqueta opcional (default "default").
  - APPD_HTTP_LISTENER: URL del listener (default http://127.0.0.1:8293/api/v1/metrics).
  - METRIC_PREFIX: Prefijo base (default "Custom Metrics|Web|IHS|HPUX").
"""
import os
import re
import sys
import requests
from typing import Dict, Any, List, Tuple

# --- Helpers ------------------------------------------------------------


def parse_targets() -> List[Tuple[str, str]]:
    """
    Parsea los targets desde IHS_TARGETS o IHS_STATUS_URL.
    Retorna lista de (url, label).
    """
    targets: List[Tuple[str, str]] = []
    ihs_targets = os.getenv("IHS_TARGETS", "").strip()
    ihs_url = os.getenv("IHS_STATUS_URL", "").strip()
    ihs_label = os.getenv("IHS_LABEL", "default").strip()

    if ihs_targets:
        for item in ihs_targets.split(","):
            item = item.strip()
            if "|" in item:
                url, label = item.split("|", 1)
                url, label = url.strip(), label.strip()
            else:
                url, label = item.strip(), f"ihs-{len(targets) + 1}"
            if url:
                targets.append((url, _sanitize_label(label)))
    elif ihs_url:
        targets.append((ihs_url, _sanitize_label(ihs_label)))

    return targets


def _sanitize_label(label: str) -> str:
    """Elimina caracteres no válidos para la ruta de métricas."""
    return re.sub(r"[^\w\-.]", "_", label) or "unnamed"


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


def make_metric_payload(metric_prefix: str, metrics: Dict[str, float]) -> List[Dict[str, Any]]:
    """
    Payload para Machine Agent HTTP Listener (Custom Metrics API).
    Formato: array de objetos con metricName, aggregatorType, value.
    IMPORTANTE: value debe ser entero (64-bit) según documentación AppDynamics.
    Para decimales (ReqPerSec, BytesPerSec, BytesPerReq) se escala x1000 para conservar precisión.
    Ref: https://docs.appdynamics.com/.../machine-agent-http-listener
    """
    # Métricas que son decimales: escalar x1000 para conservar 3 decimales
    scale_1000 = {"ReqPerSec", "BytesPerSec", "BytesPerReq"}

    metric_list: List[Dict[str, Any]] = []
    for name, value in metrics.items():
        if name in scale_1000:
            val = int(round(float(value) * 1000))
        else:
            val = int(round(float(value)))
        # OBSERVATION para snapshots puntuales (mejor visualización en Server Visibility)
        metric_list.append({
            "metricName": f"{metric_prefix}|{name}",
            "aggregatorType": "OBSERVATION",
            "value": val,
        })
    return metric_list


def post_metrics(listener_url: str, payload: List[Dict[str, Any]]) -> None:
    r = requests.post(listener_url, json=payload, timeout=10)
    if r.status_code not in (200, 202, 204):
        raise RuntimeError(f"HTTP {r.status_code}: {r.text[:300]}")


def _extract_metrics(status: Dict[str, Any]) -> Dict[str, float]:
    """Extrae las métricas clave del status parseado."""
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
    return metrics_out


# --- Main ---------------------------------------------------------------


def main() -> int:
    targets = parse_targets()
    listener_url = os.getenv("APPD_HTTP_LISTENER", "http://127.0.0.1:8293/api/v1/metrics").strip()
    metric_prefix_base = os.getenv("METRIC_PREFIX", "Custom Metrics|Web|IHS|HPUX").strip()

    if not targets:
        print("Missing config: set IHS_TARGETS or IHS_STATUS_URL", file=sys.stderr)
        return 2

    all_payload: List[Dict[str, Any]] = []
    ok_count = 0

    for url, label in targets:
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
        except requests.RequestException as e:
            print(f"[{label}] Error fetching {url}: {e}", file=sys.stderr)
            continue

        status = parse_server_status_auto(resp.text)
        metrics_out = _extract_metrics(status)

        if not metrics_out:
            print(f"[{label}] No metrics parsed from server-status?auto", file=sys.stderr)
            continue

        prefix = f"{metric_prefix_base}|{label}"
        all_payload.extend(make_metric_payload(prefix, metrics_out))
        ok_count += 1

    if all_payload:
        post_metrics(listener_url, all_payload)
        print(f"Posted {len(all_payload)} metrics ({ok_count} IHS) to Machine Agent listener.")
        return 0

    print("No metrics collected from any IHS target.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
