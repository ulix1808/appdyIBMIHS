# AppDynamics – Agente para IBM HTTP Server (IHS)

Este directorio contiene documentación y ejemplos para instalar el **Apache Agent** de Splunk AppDynamics en **IBM HTTP Server (IHS)**.

## Contenido

| Archivo | Descripción |
|---------|-------------|
| [MANUAL_INSTALACION_APPDYNAMICS_IHS.md](./MANUAL_INSTALACION_APPDYNAMICS_IHS.md) | Manual completo de instalación y configuración (español) |
| [appdynamics_agent.conf.ejemplo](./appdynamics_agent.conf.ejemplo) | Ejemplo de configuración del agente para copiar y adaptar |
| [CHECKLIST_INSTALACION_IHS.md](./CHECKLIST_INSTALACION_IHS.md) | Lista de comprobación para la instalación |

## Referencia oficial

- [Install the Apache Agent](https://docs.appdynamics.com/appd/24.x/24.7/en/application-monitoring/install-app-server-agents/apache-web-server-agent/install-the-apache-agent) (AppDynamics 24.7)

## Resumen rápido

1. **Requisitos:** IHS soportado, mismo usuario que IHS para instalar/ejecutar, locale y ulimit correctos.
2. **Instalación:** Descargar Apache Agent, extraer en `/opt`, ejecutar `install.sh`, configurar permisos en `logs/`.
3. **Configuración:** Crear `appdynamics_agent.conf` (ej. en `conf/` de IHS), definir Controller, cuenta, aplicación, tier y nodo.
4. **Proxy:** Iniciar `runSDKProxy.sh` (manual o con `AppDynamicsLaunchProxy On`) como usuario de IHS.
5. **IHS:** Añadir `Include conf/appdynamics_agent.conf` al final de `httpd.conf`, reiniciar IHS y generar tráfico.

**IHS 7.x–8.x** → módulo `libmod_appdynamics22.so` (Apache 2.2).  
**IHS 9.x** → módulo `libmod_appdynamics.so` (Apache 2.4).
