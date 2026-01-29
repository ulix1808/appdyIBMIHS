# Checklist de instalación – AppDynamics Apache Agent en IHS

Use esta lista para asegurar una instalación completa del agente en IBM HTTP Server.

## Fase 1: Antes de comenzar

### Requisitos
- [ ] IHS y SO soportados (consultar documentación AppDynamics)
- [ ] Módulo correcto: IHS 7.x/8.x → `libmod_appdynamics22.so`; IHS 9.x → `libmod_appdynamics.so`
- [ ] Instalación con el **mismo usuario y grupo** que los workers de IHS
- [ ] Permisos de lectura/escritura en `<agent_install_directory>/logs` para el usuario de IHS
- [ ] `/dev/random` o `/dev/urandom` operativos
- [ ] `ulimit -n` adecuado (ver manual: MPM_Worker vs otros modos)
- [ ] Locale definido (p. ej. `LANG=en_US.UTF-8` o `LC_ALL=C`)
- [ ] Linux con módulos `libstdc++.so.5`: revisar consideraciones especiales

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

- [ ] Descargar Apache Agent (Getting Started o accounts.appdynamics.com/downloads)
- [ ] Extraer en `/opt` (o directorio elegido): `tar -xzvf ... -C /opt`
- [ ] Verificar `<agent_install_directory>` (ej. `/opt/appdynamics-sdk-native`)
- [ ] `chown`/`chmod` en `logs/` para el usuario de IHS
- [ ] `export LD_LIBRARY_PATH=<agent_install_directory>/sdk_lib/lib`
- [ ] Ejecutar `install.sh`
- [ ] Múltiples IHS: directorio de instalación distinto por agente

## Fase 3: Configuración del agente

- [ ] Crear `appdynamics_agent.conf` en el directorio de conf de IHS
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

- [ ] Añadir `Include conf/appdynamics_agent.conf` al final de `httpd.conf` (o config principal)
- [ ] Incluir **después** de los módulos a instrumentar
- [ ] Reiniciar IHS
- [ ] Aplicar carga al servidor web

## Fase 6: Verificación

- [ ] Proxy en ejecución
- [ ] Sin errores en logs del agente y del proxy
- [ ] Conectividad al Controller (puerto, firewall, proxy)
- [ ] Nodo visible en el Controller
- [ ] Métricas y transacciones recibidas

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
