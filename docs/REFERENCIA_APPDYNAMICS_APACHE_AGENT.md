# Referencia: Apache Agent de AppDynamics (IHS / Apache / OHS)

Este documento consolida la información de soporte, requisitos y troubleshooting del **Apache Web Server Agent** de Splunk AppDynamics. Se mantiene en el repositorio para **no depender de enlaces externos** que puedan dejar de estar disponibles.

---

## 1. Plataformas y versiones soportadas (Supported Apache Web Servers)

### Servidores web

| Servidor | Versiones |
|----------|-----------|
| Apache HTTP Server | 2.2.x, 2.4.x |
| IBM HTTP Server (IHS) | ≥ 7.0 |
| Oracle HTTP Server (OHS) | ≥ 11g |

### Sistemas operativos y arquitecturas

- **Linux**
  - x86 64-bit, `glibc` ≥ 2.34 (distribuciones habituales).
  - Alpine Linux ≥ 3.18.3; solo 64-bit y Apache 2.4.
  - RHEL 7 **no** soportado desde Apache Agent 23.x. RHEL 8 desde 23.12.x; RHEL 9 desde 23.8.x.
  - Si aparece aviso ELF, comprobar versión de `glibc`.
- **AIX**
  - AIX 7.2 (7200-05-03-2148 o posterior), PowerPC.
  - Solo 64-bit y Apache 2.4.

### Entornos multicloud

- Amazon EC2, ECS, EKS.
- Azure AKS.

### No soportados oficialmente

- **HP-UX** (incl. Itanium / IA-64): no hay binarios oficiales. No usar `.so` de otras arquitecturas. Para IHS en HP-UX existen **alternativas sin agente**: métricas “tipo salud” vía **`mod_status`** + scraping desde un host Linux (OTel/Telegraf/Prometheus), y uso de **`access_log`** / **`error_log`** con recolección remota (syslog, rsync, NFS, etc.) y parsing en el collector — sin instalar forwarders en HP-UX. Detalle en [§2.3 Alternativas para HP-UX](../MANUAL_INSTALACION_APPDYNAMICS_IHS.md#23-alternativas-para-hp-ux-sin-agente-nativo) del manual.
- **Solaris** / **Windows**: no aparecen en la matriz actual del Apache Agent. Confirmar con documentación vigente o soporte si se usan.

### Módulos Apache

- El agente detecta automáticamente los módulos cargados como *remote services*.
- Excluye una lista interna de módulos (p. ej. `core`, `mod_so`, `mod_ssl`, `mod_actions`, `mod_alias`, `mod_auth_*`, `mod_deflate`, `mod_dir`, `mod_mime`, `mod_rewrite`, etc.). La lista exacta puede variar por versión del agente.
- **mod_so (DSO)** es imprescindible para cargar el módulo del agente.

---

## 2. Consideraciones `libstdc++.so.5` (IHS / OHS)

En IHS y OHS es habitual que otros módulos dependan de **`libstdc++.so.5`**, mientras que el Apache Agent suele construirse contra **`libstdc++.so.6`**.

- Si el sistema tiene **ambas** versiones:
  - Asegurarse de que el agente y el proxy usen la correcta (p. ej. `libstdc++.so.6`).
  - Si hace falta, usar **`LD_PRELOAD`** apuntando a la ruta del `libstdc++` adecuado **antes** de ejecutar `runSDKProxy.sh`.
- **Apache 32-bit en SO 64-bit:**
  - Usar agente **32-bit** y **`libstdc++` 32-bit**.
  - Asegurarse de que `LD_PRELOAD` o las libs cargadas correspondan a la arquitectura correcta.

En caso de conflictos de símbolos o cargas incorrectas, revisar dependencias con `ldd` (Linux) o `chatr` (HP-UX).

---

## 3. Prerrequisitos en AIX

- **AIX 7.2** (build indicado arriba), **PowerPC**, **64-bit**, **Apache 2.4**.
- **`LoadFile`** no se usa en AIX; las libs se resuelven por otros medios (en el manual se indican los pasos).
- Extracción del agente:

  ```bash
  gzip -c appdynamics-sdk-native-nativeWebServer-64bit-aix-<version>.tgz | tar xvf - -C /opt
  ```

- **Proxy:** puede requerir JRE explícito. Usar `--jre-dir=<ruta>` al invocar `runSDKProxy.sh` o configurar `AppDynamicsProxyJreDir` / `AppDynamicsLaunchProxy` según la documentación del agente.
- Revisar requisitos específicos de libs y patches en AIX en la documentación del producto instalada.

---

## 4. Machine Agent y Apache Monitoring Extension

- Si se usa la **Apache Monitoring Extension** con el **Machine Agent**, se puede seguir utilizando.
- Tras instalar el **Apache Agent** (módulo nativo en Apache/IHS), puede ser necesario **reiniciar el Machine Agent** para que convivan correctamente.

---

## 5. SELinux (Linux)

En distribuciones con **SELinux** (p. ej. RHEL, CentOS):

- El módulo del agente y los accesos a logs/sockets pueden verse **bloqueados** por políticas por defecto.
- Síntomas: el módulo no carga, errores de permisos en `logs/` o en el directorio de comunicación del proxy aunque los permisos Unix sean correctos.
- Acciones posibles (ajustar al estándar de tu entorno):
  - Asignar el **contexto** adecuado a los directorios del agente (p. ej. compatibles con `httpd`) o usar etiquetas que permitan a `httpd` leer/escribir.
  - En **pruebas** se usa a veces `setenforce 0` para comprobar si SELinux es la causa; **no** se recomienda dejar SELinux en permissive en producción.
  - Definir políticas o reglas específicas para el agente según las guías de hardening del SO.

**HP-UX:** no hay SELinux. Si se usa **Trusted HP-UX** u otros MAC, verificar que el usuario de IHS pueda escribir en `logs/` y en el directorio de comunicación del proxy.

---

## 6. Filtrado de datos sensibles (Filter Sensitive Data)

Para no enviar información sensible al Controller (query strings, headers, cookies, etc.):

- AppDynamics permite **filtrar o enmascarar** datos en las peticiones capturadas por el agente.
- La configuración depende de la versión del agente y del Controller (directivas en `appdynamics_agent.conf`, configuración en Controller, etc.).
- Recomendación: revisar la **documentación instalada** o los archivos de configuración de ejemplo del agente en `<agent_install_directory>` para opciones como:
  - Exclusiones de parámetros.
  - Enmascarado de headers.
  - Reglas por URL o por tipo de contenido.

No incluir en logs ni en configuraciones valores sensibles (contraseñas, tokens, etc.).

---

## 7. Proxy (Dynamic Language Agent Proxy) y troubleshooting

El **proxy** es un proceso Java (`runSDKProxy.sh`) que recibe datos del Apache Agent y los envía al Controller.

### Comprobaciones típicas

- **Proceso en ejecución:** que `runSDKProxy.sh` esté corriendo (mismo usuario que IHS).
- **Conectividad:** Controller accesible (puerto, firewall, proxy HTTP si aplica).
- **JRE:** versión adecuada si se usa `--jre-dir` o equivalente.
- **Logs:** revisar `proxy.out`, logs en `<agent_install_directory>/logs` y, si existe, `appdynamics_agent.log`.
- **Directorios de comunicación:** `AppDynamicsProxyCommDir` (o el por defecto) con permisos correctos y ruta accesible para el usuario de IHS.
- **LD_LIBRARY_PATH / SHLIB_PATH:** que las libs del SDK estén en el path del proceso que ejecuta el proxy (y del Apache, si aplica).

### Errores frecuentes

- El agente **carga** pero **no hay datos** en el Controller: ver [§9 Logging y permisos](../MANUAL_INSTALACION_APPDYNAMICS_IHS.md#9-logging-permisos-y-troubleshooting) del manual (ownership, rutas absolutas de log, permisos).
- **Exec format error / Symbol not found** al cargar el `.so`: arquitectura o SO incorrectos; no usar binarios de otra plataforma.
- Problemas de **conexión al Controller**: comprobar host, puerto, SSL, proxy HTTP y que el Controller esté operativo.

---

## 8. Descargas del Apache Agent

- **Getting Started** del Controller: suele ofrecer enlaces o pasos para descargar el Apache Agent.
- **Portal de descargas** de AppDynamics: disponible tras iniciar sesión (por ejemplo en el sitio de cuentas de AppDynamics). Buscar “Apache Agent” o “native Web Server” / “nativeWebServer” y elegir el paquete según **SO y arquitectura** (por ejemplo `64bit-linux`, `64bit-aix`).

Siempre usar el binario que coincida con el SO y la arquitectura del servidor donde corre IHS/Apache.

---

## 9. Resumen de referencias internas

| Tema | Dónde está en este repo |
|------|--------------------------|
| Manual de instalación IHS | [MANUAL_INSTALACION_APPDYNAMICS_IHS.md](../MANUAL_INSTALACION_APPDYNAMICS_IHS.md) |
| Checklist instalación | [CHECKLIST_INSTALACION_IHS.md](../CHECKLIST_INSTALACION_IHS.md) |
| Ejemplo de configuración | [appdynamics_agent.conf.ejemplo](../appdynamics_agent.conf.ejemplo) |
| Índice y resumen | [README.md](../README.md) |

---

*Referencia local. No se dependen enlaces externos a documentación de AppDynamics. Basado en documentación Apache Agent (AppDynamics 24.x).*
