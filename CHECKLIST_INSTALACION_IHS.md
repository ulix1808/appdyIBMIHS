# Checklist de instalación – AppDynamics Apache Agent en IHS

Use esta lista para asegurar una instalación completa del agente en IBM HTTP Server.

## Fase 0: Conceptos y plataforma

### Apache Agent ≠ Java Agent
- [ ] Entendido: el **Apache Agent es nativo (C/C++)**, no usa `JAVA_HOME`, `javaagent.jar` ni JVM options
- [ ] Java solo aplica al **proxy** (`runSDKProxy.sh`) o a WAS detrás de IHS (correlación E2E)

### Plataforma y binarios
- [ ] SO y arquitectura **soportados** (Linux x86_64, AIX, etc.; ver [Plataformas soportadas](docs/REFERENCIA_APPDYNAMICS_APACHE_AGENT.md#1-plataformas-y-versiones-soportadas-supported-apache-web-servers))
- [ ] **HP-UX Itanium (IA-64):** si aplica, asumir que **no hay .so oficial**; documentar origen del binario y no usar .so de otra arquitectura
- [ ] `.so` compilado para la **arquitectura exacta** (IA-64 ≠ x86_64; Exec format error / Symbol not found si no coincide)

### Si HP-UX y **no** usas agente (alternativas) — ver [§2.3 del manual](MANUAL_INSTALACION_APPDYNAMICS_IHS.md#23-alternativas-para-hp-ux-sin-agente-nativo)
- [ ] **Opción A – Métricas tipo salud:** `mod_status` en IHS, `/server-status?auto` con ACL estricta (solo IP del collector); scraping desde Linux (OTel/Telegraf/Prometheus). Cero binarios en HP-UX.
- [ ] **Opción B – Logs:** `access_log` (con `%D` si se quiere latencia) y `error_log`. Recolectar de forma **remota** (syslog, rsync, NFS, etc.) y parsear en Linux; **no** instalar forwarders en HP-UX.

## Fase 1: Antes de comenzar

### Requisitos
- [ ] IHS y SO soportados (consultar documentación AppDynamics)
- [ ] MPM **prefork** o **worker** (no event); **mod_so (DSO)** disponible
- [ ] Módulo correcto: IHS 7.x/8.x → `libmod_appdynamics22.so`; IHS 9.x → `libmod_appdynamics.so`
- [ ] Instalación con el **mismo usuario y grupo** que los workers de IHS
- [ ] Permisos de lectura/escritura en `<agent_install_directory>/logs` para el usuario de IHS
- [ ] `/dev/random` o `/dev/urandom` operativos
- [ ] `ulimit -n` adecuado (ver manual: MPM_Worker vs otros modos)
- [ ] Locale definido (p. ej. `LANG=en_US.UTF-8` o `LC_ALL=C`)
- [ ] Linux con módulos `libstdc++.so.5`: ver [Consideraciones libstdc++.so.5](docs/REFERENCIA_APPDYNAMICS_APACHE_AGENT.md#2-consideraciones-libstdcso5-ihs--ohs)
- [ ] **APR:** versión documentada; validar con `ldd` (Linux) o `chatr` (HP-UX) que las dependencias del .so se resuelven

### Datos del Controller
- [ ] Controller Host
- [ ] Controller Port (SaaS: 80/443; On‑premise: 8090/8181)
- [ ] SSL On/Off
- [ ] Account Name
- [ ] Access Key
- [ ] Application name
- [ ] Tier name
- [ ] Node name (único por instancia)

## Fase 2: Descarga e instalación

- [ ] Descargar Apache Agent (Getting Started o portal de descargas) para **SO y arquitectura exactos**; ver [Descargas](docs/REFERENCIA_APPDYNAMICS_APACHE_AGENT.md#8-descargas-del-apache-agent)
- [ ] Extraer en `/opt` (o directorio elegido): `tar -xzvf ... -C /opt`
- [ ] Verificar `<agent_install_directory>` (ej. `/opt/appdynamics-sdk-native`)
- [ ] `chown`/`chmod` en `logs/` para el usuario de IHS (**ownership** y permisos explícitos)
- [ ] `export LD_LIBRARY_PATH` (o `SHLIB_PATH` en HP-UX) = `<agent_install_directory>/sdk_lib/lib`
- [ ] Ejecutar `install.sh`
- [ ] Múltiples IHS: directorio de instalación distinto por agente

## Fase 3: Configuración del agente

- [ ] Crear `appdynamics_agent.conf` en el directorio de conf de IHS
- [ ] **Rutas IHS:** usar `$IHS_HOME/modules` o `$IHS_HOME/libexec` según instalación; **rutas absolutas** en `LoadFile`/`LoadModule`
- [ ] Configurar `LoadFile` (Linux) y `LoadModule` según versión IHS
- [ ] `AppDynamicsEnabled On`
- [ ] Controller: Host, Port, SSL
- [ ] Account Name, Access Key
- [ ] Application, Tier, Node
- [ ] Proxy HTTP (si aplica): ProxyHost, ProxyPort
- [ ] Múltiples instancias: `AppDynamicsProxyCommDir` y Node únicos

## Fase 4: Proxy

- [ ] `LD_LIBRARY_PATH` exportado
- [ ] Decidir: `AppDynamicsLaunchProxy On` o arranque manual
- [ ] Si manual: ejecutar `runSDKProxy.sh` como usuario de IHS
- [ ] Considerar servicio (systemd/init) para inicio automático
- [ ] Revisar `logs/proxy.out` si hay problemas

## Fase 5: Configuración de IHS

- [ ] **Validar mod_so:** `apachectl -l` (o equivalente IHS); confirmar que **`mod_so.c`** está compilado
- [ ] Añadir `Include conf/appdynamics_agent.conf` al final de `httpd.conf` (o config principal)
- [ ] Incluir **después** de los módulos a instrumentar
- [ ] Reiniciar IHS
- [ ] Aplicar carga al servidor web

## Fase 6: Verificación

- [ ] Proxy en ejecución
- [ ] Sin errores en logs del agente y del proxy
- [ ] **Logging:** ownership y permisos correctos en `<agent_install_directory>/logs`; **rutas absolutas** para logs
- [ ] Conectividad al Controller (puerto, firewall, proxy)
- [ ] Nodo visible en el Controller
- [ ] Métricas y transacciones recibidas
- [ ] Si el módulo carga pero no hay datos: revisar [§9 Logging y permisos](MANUAL_INSTALACION_APPDYNAMICS_IHS.md#9-logging-permisos-y-troubleshooting) y [Proxy / troubleshooting](docs/REFERENCIA_APPDYNAMICS_APACHE_AGENT.md#7-proxy-dynamic-language-agent-proxy-y-troubleshooting)

## Fase 7: Opcionales

- [ ] Virtual Hosts: `AppDynamicsApplicationContext` por VirtualHost
- [ ] Directivas adicionales (BackendNameSegments, CustomTags, etc.)
- [ ] Unique Host ID en `runProxy` si se requiere
- [ ] Documentar cambios y handoff a operaciones

---

**Fecha:** _______________  
**Responsable:** _______________  
**Estado:** ☐ Exitoso  ☐ Parcial  ☐ Fallido  

**Notas:**  
_________________________________________________________________  
_________________________________________________________________
