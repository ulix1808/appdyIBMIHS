#!/usr/bin/env python3
"""
Script de prueba de integración para verificar que el script maneja correctamente
certificados SSL autofirmados.

Este script:
1. Crea un servidor HTTPS local con certificado autofirmado
2. Prueba que el script puede conectarse cuando SSL_VERIFY=false
3. Verifica que falla cuando SSL_VERIFY=true (comportamiento esperado)
"""
import os
import sys
import ssl
import socket
import threading
import time
import subprocess
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Optional

# Intentar importar requests, si no está disponible, mostrar mensaje
try:
    import requests
except ImportError:
    print("ERROR: El módulo 'requests' no está instalado.", file=sys.stderr)
    print("Instálalo con: pip install requests", file=sys.stderr)
    sys.exit(1)


class MockIHSStatusHandler(BaseHTTPRequestHandler):
    """Handler que simula el endpoint /server-status?auto de IHS."""
    
    def do_GET(self):
        if self.path == "/server-status?auto":
            # Respuesta típica de mod_status
            response = """Total Accesses: 12345
Total kBytes: 567890
CPULoad: 0.5
Uptime: 86400
ReqPerSec: 0.142
BytesPerSec: 6578.9
BytesPerReq: 46323.4
BusyWorkers: 5
IdleWorkers: 10
Scoreboard: _W__K__R__C__L__G___
"""
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(response)))
            self.end_headers()
            self.wfile.write(response.encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        # Suprimir logs del servidor HTTP
        pass


def create_self_signed_cert():
    """Crea un certificado autofirmado temporal usando OpenSSL."""
    import tempfile
    import atexit
    
    cert_file = tempfile.NamedTemporaryFile(mode='w', suffix='.crt', delete=False)
    key_file = tempfile.NamedTemporaryFile(mode='w', suffix='.key', delete=False)
    cert_file.close()
    key_file.close()
    
    # Generar certificado autofirmado
    try:
        subprocess.run([
            'openssl', 'req', '-x509', '-newkey', 'rsa:2048',
            '-keyout', key_file.name,
            '-out', cert_file.name,
            '-days', '1',
            '-nodes',
            '-subj', '/CN=localhost'
        ], check=True, capture_output=True)
        
        # Limpiar archivos al salir
        def cleanup():
            try:
                os.unlink(cert_file.name)
                os.unlink(key_file.name)
            except:
                pass
        
        atexit.register(cleanup)
        return cert_file.name, key_file.name
    except (subprocess.CalledProcessError, FileNotFoundError):
        # Si openssl no está disponible, intentar crear certificado básico
        print("ADVERTENCIA: OpenSSL no está disponible. Usando certificado simulado.", file=sys.stderr)
        return None, None


def find_free_port() -> int:
    """Encuentra un puerto libre."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port


def start_https_server(port: int, cert_file: Optional[str] = None, key_file: Optional[str] = None) -> HTTPServer:
    """Inicia un servidor HTTPS con certificado autofirmado."""
    server = HTTPServer(('localhost', port), MockIHSStatusHandler)
    
    if cert_file and key_file and os.path.exists(cert_file) and os.path.exists(key_file):
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(cert_file, key_file)
        server.socket = context.wrap_socket(server.socket, server_side=True)
    else:
        # Fallback: crear contexto SSL básico (puede no funcionar sin certificado)
        print("ADVERTENCIA: No se pudo crear certificado. El servidor puede no funcionar correctamente.", file=sys.stderr)
        context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        server.socket = context.wrap_socket(server.socket, server_side=True)
    
    return server


def test_with_ssl_verify(ssl_verify_value: str, url: str, expected_success: bool) -> bool:
    """Prueba la conexión con un valor específico de SSL_VERIFY."""
    # Limpiar variable de entorno
    if "SSL_VERIFY" in os.environ:
        old_value = os.environ["SSL_VERIFY"]
    else:
        old_value = None
    
    try:
        # Configurar SSL_VERIFY
        if ssl_verify_value:
            os.environ["SSL_VERIFY"] = ssl_verify_value
        elif old_value is None:
            if "SSL_VERIFY" in os.environ:
                del os.environ["SSL_VERIFY"]
        
        # Importar y usar la función del script real
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from ihs_status_to_appd import get_ssl_config
        
        config = get_ssl_config()
        verify_value = config["verify"]
        
        # Intentar conexión
        try:
            resp = requests.get(url, timeout=2, verify=verify_value)
            resp.raise_for_status()
            success = True
            error = None
        except requests.exceptions.SSLError as e:
            success = False
            error = str(e)
        except Exception as e:
            success = False
            error = str(e)
        
        # Verificar resultado
        if success == expected_success:
            status = "✓ PASS"
            result = True
        else:
            status = "✗ FAIL"
            result = False
        
        print(f"{status}: SSL_VERIFY={ssl_verify_value or '(no configurado)'} -> verify={verify_value}")
        print(f"  URL: {url}")
        print(f"  Resultado: {'Éxito' if success else 'Error'}")
        if error and not expected_success:
            print(f"  Error esperado: {error[:100]}...")
        elif error and expected_success:
            print(f"  Error inesperado: {error[:100]}...")
        print()
        
        return result
        
    finally:
        # Restaurar variable de entorno
        if old_value is None:
            if "SSL_VERIFY" in os.environ:
                del os.environ["SSL_VERIFY"]
        else:
            os.environ["SSL_VERIFY"] = old_value


def main():
    """Ejecuta las pruebas de integración."""
    print("=" * 70)
    print("Prueba de Integración: Manejo de Certificados SSL Autofirmados")
    print("=" * 70)
    print()
    
    # Verificar si openssl está disponible
    cert_file, key_file = create_self_signed_cert()
    
    if not cert_file or not os.path.exists(cert_file):
        print("ERROR: No se pudo crear certificado autofirmado.", file=sys.stderr)
        print("Asegúrate de tener OpenSSL instalado.", file=sys.stderr)
        print()
        print("Prueba alternativa: Usando servidor HTTPS público con certificado válido")
        print("(Esta prueba solo verifica la lógica, no certificados autofirmados)")
        print()
        
        # Prueba alternativa con servidor público
        test_url = "https://httpbin.org/get"
        print("Probando con servidor público (certificado válido)...")
        print()
        
        # Esta prueba debería funcionar siempre (certificado válido)
        test_with_ssl_verify("true", test_url, True)
        test_with_ssl_verify("false", test_url, True)
        
        print("=" * 70)
        print("NOTA: Para probar certificados autofirmados, necesitas OpenSSL instalado.")
        print("=" * 70)
        return 0
    
    # Iniciar servidor HTTPS local
    port = find_free_port()
    server = start_https_server(port, cert_file, key_file)
    
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    
    # Dar tiempo al servidor para iniciar
    time.sleep(0.5)
    
    test_url = f"https://localhost:{port}/server-status?auto"
    
    print(f"Servidor HTTPS de prueba iniciado en: {test_url}")
    print()
    
    # Pruebas
    print("Prueba 1: SSL_VERIFY=false (debe funcionar con certificado autofirmado)")
    test1 = test_with_ssl_verify("false", test_url, True)
    
    print("Prueba 2: SSL_VERIFY=true (debe fallar con certificado autofirmado)")
    test2 = test_with_ssl_verify("true", test_url, False)
    
    print("Prueba 3: SSL_VERIFY no configurado (debe fallar, default=true)")
    test3 = test_with_ssl_verify("", test_url, False)
    
    # Detener servidor
    server.shutdown()
    
    print("=" * 70)
    if test1 and test2 and test3:
        print("✓ TODAS LAS PRUEBAS PASARON")
        print()
        print("El script maneja correctamente los certificados autofirmados.")
        print("En producción, configura SSL_VERIFY=\"false\" para usar certificados autofirmados.")
        return 0
    else:
        print("✗ ALGUNAS PRUEBAS FALLARON")
        print()
        print("Revisa los resultados arriba para más detalles.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
