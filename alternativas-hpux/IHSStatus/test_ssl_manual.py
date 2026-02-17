#!/usr/bin/env python3
"""
Script de prueba manual para verificar SSL_VERIFY en el servidor productivo.

Este script prueba directamente con los servidores IHS reales para verificar
que SSL_VERIFY=false funciona correctamente.

Uso:
    # Probar con SSL_VERIFY=false (debe funcionar)
    SSL_VERIFY=false python3 test_ssl_manual.py
    
    # Probar con SSL_VERIFY=true (debe fallar con certificados autofirmados)
    SSL_VERIFY=true python3 test_ssl_manual.py
"""
import os
import sys

try:
    import requests
except ImportError:
    print("ERROR: El módulo 'requests' no está instalado.", file=sys.stderr)
    sys.exit(1)

# Importar la función del script principal
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ihs_status_to_appd import get_ssl_config, parse_targets


def test_ssl_connection():
    """Prueba la conexión SSL con la configuración actual."""
    print("=" * 70)
    print("Prueba Manual de Configuración SSL")
    print("=" * 70)
    print()
    
    # Mostrar configuración actual
    ssl_verify_env = os.getenv("SSL_VERIFY", "true")
    print(f"SSL_VERIFY (variable de entorno): '{ssl_verify_env}'")
    
    ssl_config = get_ssl_config()
    verify_value = ssl_config["verify"]
    print(f"verify (valor usado por requests): {verify_value}")
    print()
    
    # Obtener targets
    targets = parse_targets()
    
    if not targets:
        print("ERROR: No hay targets configurados.", file=sys.stderr)
        print("Configura IHS_TARGETS o IHS_STATUS_URL", file=sys.stderr)
        return 1
    
    print(f"Targets a probar: {len(targets)}")
    print()
    
    results = []
    
    for url, label in targets:
        print(f"Probando: [{label}] {url}")
        
        # Solo probar URLs HTTPS
        if not url.startswith("https://"):
            print(f"  ⚠ Saltando (no es HTTPS)")
            print()
            continue
        
        try:
            resp = requests.get(url, timeout=10, verify=verify_value)
            resp.raise_for_status()
            
            # Verificar que la respuesta tiene el formato esperado
            if "Total Accesses" in resp.text or "BusyWorkers" in resp.text:
                print(f"  ✓ ÉXITO: Conexión establecida y respuesta válida")
                print(f"    Status: {resp.status_code}")
                print(f"    Tamaño respuesta: {len(resp.text)} bytes")
                results.append((label, True, None))
            else:
                print(f"  ⚠ ADVERTENCIA: Conexión exitosa pero respuesta inesperada")
                print(f"    Status: {resp.status_code}")
                results.append((label, True, "Respuesta inesperada"))
                
        except requests.exceptions.SSLError as e:
            error_msg = str(e)
            if "CERTIFICATE_VERIFY_FAILED" in error_msg or "self-signed" in error_msg.lower():
                print(f"  ✗ ERROR SSL: Certificado autofirmado detectado")
                print(f"    Error: {error_msg[:150]}...")
                if verify_value:
                    print(f"    SOLUCIÓN: Configura SSL_VERIFY=\"false\" para deshabilitar verificación")
                results.append((label, False, "SSL Error: certificado autofirmado"))
            else:
                print(f"  ✗ ERROR SSL: {error_msg[:150]}...")
                results.append((label, False, f"SSL Error: {error_msg[:100]}"))
                
        except requests.exceptions.RequestException as e:
            print(f"  ✗ ERROR: {str(e)[:150]}...")
            results.append((label, False, str(e)[:100]))
        
        print()
    
    # Resumen
    print("=" * 70)
    print("RESUMEN")
    print("=" * 70)
    
    success_count = sum(1 for _, success, _ in results if success)
    total_count = len(results)
    
    for label, success, error in results:
        status = "✓" if success else "✗"
        print(f"{status} [{label}]: {'Éxito' if success else f'Error: {error}'}")
    
    print()
    print(f"Resultados: {success_count}/{total_count} exitosos")
    print()
    
    if success_count == total_count:
        print("✓ TODAS LAS PRUEBAS PASARON")
        print()
        if verify_value == False:
            print("La configuración SSL_VERIFY=\"false\" está funcionando correctamente.")
            print("El script debería funcionar en producción con esta configuración.")
        else:
            print("ADVERTENCIA: SSL_VERIFY está habilitado pero las conexiones funcionaron.")
            print("Esto puede indicar que los certificados son válidos o que hay otra configuración.")
        return 0
    else:
        print("✗ ALGUNAS PRUEBAS FALLARON")
        print()
        if verify_value:
            print("RECOMENDACIÓN: Configura SSL_VERIFY=\"false\" para certificados autofirmados:")
            print("  export SSL_VERIFY=\"false\"")
            print("  python3 test_ssl_manual.py")
        return 1


if __name__ == "__main__":
    sys.exit(test_ssl_connection())
