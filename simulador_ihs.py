#!/usr/bin/env python3
"""
Simulador de IHS mod_status para pruebas locales.
Sirve /server-status?auto con formato compatible con ihs_status_to_appd.py.
Uso: python3 simulador_ihs.py [puerto]   (default: 8080)
"""
import random
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
import sys

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8080

# Simular valores que van cambiando ligeramente
def get_status_text():
    base_uptime = int(time.time()) % 1000000 + 1000
    total_accesses = random.randint(5000, 15000) + int(time.time() % 1000)
    busy = random.randint(2, 8)
    idle = random.randint(90, 98)
    req_per_sec = round(random.uniform(0.5, 5.0), 4)
    bytes_per_sec = round(random.uniform(100, 2000), 2)
    bytes_per_req = round(random.uniform(200, 800), 0)
    total_kb = total_accesses * 2

    return f"""Total Accesses: {total_accesses}
Total kBytes: {total_kb}
CPULoad: .{random.randint(1, 9)}
Uptime: {base_uptime}
ReqPerSec: {req_per_sec}
BytesPerSec: {bytes_per_sec}
BytesPerReq: {bytes_per_req}
BusyWorkers: {busy}
IdleWorkers: {idle}
Scoreboard: {"_" * (busy + idle)}.
""".strip()


class IHSStatusHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.split("?")[0] == "/server-status" and "auto" in self.path:
            body = get_status_text().encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", len(body))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found")

    def log_message(self, format, *args):
        print(f"[IHS simulador] {args[0]}")


if __name__ == "__main__":
    server = HTTPServer(("127.0.0.1", PORT), IHSStatusHandler)
    print(f"IHS simulador en http://127.0.0.1:{PORT}/server-status?auto (Ctrl+C para detener)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nDetenido.")
        server.shutdown()
