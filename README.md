# AppDynamics – Agente para IBM HTTP Server (IHS)

Este directorio contiene documentación y ejemplos para instalar el **Apache Agent** de Splunk AppDynamics en **IBM HTTP Server (IHS)**.

## Contenido

| Archivo | Descripción |
|---------|-------------|
| [MANUAL_INSTALACION_APPDYNAMICS_IHS.md](./MANUAL_INSTALACION_APPDYNAMICS_IHS.md) | Manual completo de instalación y configuración (español) |
| [docs/REFERENCIA_APPDYNAMICS_APACHE_AGENT.md](./docs/REFERENCIA_APPDYNAMICS_APACHE_AGENT.md) | Referencia local: plataformas, libstdc++, AIX, SELinux, proxy, descargas (sin enlaces externos) |
| [alternativas-hpux/](./alternativas-hpux/) | Alternativas para IHS en HP-UX (mod_status + Machine Agent + Python). Host Linux: 1 CPU, 4 GB RAM mín. |
| [appdynamics_agent.conf.ejemplo](./appdynamics_agent.conf.ejemplo) | Ejemplo de configuración del agente para copiar y adaptar |
| [CHECKLIST_INSTALACION_IHS.md](./CHECKLIST_INSTALACION_IHS.md) | Lista de comprobación para la instalación |

## Referencia (todo en este repo)

- [Referencia AppDynamics Apache Agent](docs/REFERENCIA_APPDYNAMICS_APACHE_AGENT.md): plataformas, libstdc++.so.5, AIX, SELinux, proxy, descargas, etc. Sin dependencia de enlaces externos.

## Puntos importantes

- **Apache Agent ≠ Java Agent.** El Apache Agent es **nativo (C/C++)**, cargado vía `LoadModule`. No usa `JAVA_HOME`, `javaagent.jar` ni JVM options. El **proxy** (`runSDKProxy.sh`) sí es Java.
- **IHS ≠ Apache vanilla.** La doc oficial aplica **conceptualmente**; rutas y plataformas pueden diferir (p. ej. `$IHS_HOME/modules`, `$IHS_HOME/libexec`).
- **HP-UX / Itanium (IA-64):** AppDynamics **no** publica binarios oficiales para HP-UX Itanium. No usar `.so` de otra arquitectura (x86_64, etc.): `Exec format error` / `Symbol not found`. Ver [manual](MANUAL_INSTALACION_APPDYNAMICS_IHS.md) §2 y §9 y [referencia](docs/REFERENCIA_APPDYNAMICS_APACHE_AGENT.md). **Alternativas sin agente:** [§2.3 del manual](MANUAL_INSTALACION_APPDYNAMICS_IHS.md#23-alternativas-para-hp-ux-sin-agente-nativo) — métricas vía `mod_status` + scraping, y logs `access_log`/`error_log` con recolección remota (sin forwarders en HP-UX).
- **mod_so (DSO), APR, permisos y logging:** Validar `mod_so` (`apachectl -l`), compatibilidad APR (`ldd`/`chatr`), ownership y rutas absolutas de logs. Sin ello, el agente puede cargar y no reportar nada. Ver [referencia local](docs/REFERENCIA_APPDYNAMICS_APACHE_AGENT.md).

## Resumen rápido

1. **Requisitos:** IHS soportado, MPM prefork/worker, mod_so, mismo usuario que IHS, locale y ulimit correctos.
2. **Instalación:** Descargar Apache Agent para **SO y arquitectura exactos**, extraer, ejecutar `install.sh`, configurar ownership/permisos en `logs/`.
3. **Configuración:** Crear `appdynamics_agent.conf` (rutas absolutas), Controller, cuenta, aplicación, tier y nodo.
4. **Proxy:** Iniciar `runSDKProxy.sh` (manual o `AppDynamicsLaunchProxy On`) como usuario de IHS.
5. **IHS:** Validar `mod_so`, añadir `Include conf/appdynamics_agent.conf` al final de `httpd.conf`, reiniciar y generar tráfico.

**IHS 7.x–8.x** → `libmod_appdynamics22.so` (Apache 2.2).  
**IHS 9.x** → `libmod_appdynamics.so` (Apache 2.4).
