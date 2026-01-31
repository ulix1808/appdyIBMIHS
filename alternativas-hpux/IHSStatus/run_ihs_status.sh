#!/bin/sh
# Wrapper para ejecutar el script Python.
# Evita problemas de parsing en monitor.xml con type=command (executable + argument).
# Se ejecuta desde el directorio monitors/IHSStatus/.
cd "$(dirname "$0")"
exec /usr/bin/python3 ./ihs_status_to_appd.py
