# Manual de Instalación del Agente AppDynamics para IBM HTTP Server (IHS)

Este manual describe los pasos para instalar y configurar el **Apache Agent** de Splunk AppDynamics en **IBM HTTP Server (IHS)**. El agente instrumenta el servidor web y envía datos de rendimiento a un proxy Java, que a su vez los envía al Controller.

**Documentación de referencia:** [Install the Apache Agent](https://docs.appdynamics.com/appd/24.x/24.7/en/application-monitoring/install-app-server-agents/apache-web-server-agent/install-the-apache-agent)

---

## Tabla de contenidos

1. [Antes de comenzar](#1-antes-de-comenzar)
2. [Descargar e instalar el agente](#2-descargar-e-instalar-el-agente)
3. [Configurar el agente Apache](#3-configurar-el-agente-apache)
4. [Iniciar el proxy](#4-iniciar-el-proxy)
5. [Configurar IHS para AppDynamics](#5-configurar-ihs-para-appdynamics)
6. [Mapear Virtual Hosts a Tiers](#6-mapear-virtual-hosts-a-tiers-appdynamics)
7. [Directivas adicionales](#7-directivas-adicionales)
8. [Resolución de problemas](#8-resolución-de-problemas)

---

## 1. Antes de comenzar

### 1.1 Requisitos de software y sistema

- **Versión de IHS:** Comprobar que la versión y el sistema operativo estén soportados. Consultar [Supported Apache Web Servers](https://docs.appdynamics.com/appd/24.x/24.7/en/application-monitoring/install-app-server-agents/apache-web-server-agent/install-the-apache-agent).
- **Módulo según versión de IHS:**
  - **IHS 7.x – 8.x:** módulo Apache 2.2 → `libmod_appdynamics22.so`
  - **IHS 9.x:** módulo Apache 2.4 → `libmod_appdynamics.so`
- **Linux con `libstdc++.so.5`:** Si IHS usa módulos que dependen de `libstdc++.so.5`, revisar [Special Considerations for Apache Web Servers with libstdc++.so.5 Modules](https://docs.appdynamics.com/appd/24.x/24.7/en/application-monitoring/install-app-server-agents/apache-web-server-agent/install-the-apache-agent). Es habitual en IHS y OHS.
- **AIX:** Ver [Prerequisites for Apache Agent Installation on AIX](https://docs.appdynamics.com/appd/24.x/24.7/en/application-monitoring/install-app-server-agents/apache-web-server-agent/install-the-apache-agent) si aplica.

### 1.2 Usuario y permisos

- Instalar y ejecutar el agente con el **mismo usuario y grupo** con el que IHS arranca los procesos worker.
- El usuario que ejecuta IHS debe tener **lectura y escritura** en el directorio de logs del agente: `<agent_install_directory>/logs`.

### 1.3 Entorno del sistema

- **`/dev/random` o `/dev/urandom`:** Deben estar correctamente configurados. El agente usa generación de números aleatorios; si no, pueden fallar creación de logs, directorios o el envío de datos al Controller.
- **Límite de descriptores de archivo (`ulimit -n`):**
  - **MPM_Worker:** `1024 + ServerLimit + (2 × ServerLimit × ThreadsPerChild)`
  - **Otros modos:** `(Número total de workers Apache activos concurrentemente × 2) + 1024`
  - Configurar en `/etc/security/limits.conf` (requiere reinicio) o con `ulimit -n` en la sesión del usuario.
- **Locale:** Definir variables de entorno según el idioma deseado, por ejemplo:

  ```bash
  export LANG=en_US.UTF-8
  export LANGUAGE=$LANG
  export LC_ALL=$LANG
  ```

  O bien:

  ```bash
  export LANG=en_US.UTF-8
  ```

  O:

  ```bash
  export LC_ALL=C
  ```

### 1.4 Información necesaria del Controller

Tener a mano:

| Parámetro | Descripción | Ejemplo |
|-----------|-------------|---------|
| **Controller Host** | Host o IP del Controller | `mycontroller.saas.appdynamics.com` |
| **Controller Port** | Puerto HTTP(S) | SaaS: 443 (HTTPS) / 80 (HTTP); On‑premise: 8090 (HTTP) / 8181 (HTTPS) |
| **SSL** | Uso de HTTPS | ON / OFF |
| **Account Name** | Cuenta AppDynamics | `MyCompany` |
| **Access Key** | Access Key de la cuenta | (proporcionado en Welcome email o en Controller > License) |
| **Application** | Nombre de la aplicación | `MiAppIHS` |
| **Tier** | Nombre del tier | `IHS_Tier` |
| **Node** | Nombre del nodo (único por instancia) | `IHS_Node_01` |

---

## 2. Descargar e instalar el agente

### 2.1 Descarga

1. Descargar el **Apache Agent** desde:
   - El asistente **Getting Started** del Controller, o  
   - [https://accounts.appdynamics.com/downloads](https://accounts.appdynamics.com/downloads)
2. Elegir el paquete según SO y arquitectura (por ejemplo `64bit-linux` o `64bit-aix`).

### 2.2 Extracción

**Linux (ejemplo):**

```bash
tar -xzvf appdynamics-sdk-native-nativeWebServer-64bit-linux-<version>.tgz -C /opt
```

**AIX:**

```bash
gzip -c appdynamics-sdk-native-nativeWebServer-64bit-aix-<version>.tgz | tar xvf - -C /opt
```

El agente queda en `/opt/appdynamics-sdk-native` (este es el `<agent_install_directory>`).

- **Múltiples instancias de IHS:** Usar un directorio de instalación distinto por agente.
- **Recomendación:** Un agente por instancia de IHS; no superar **dos** instancias de Apache/IHS por agente.

### 2.3 Permisos en logs

```bash
chown -R <usuario_ihs>:<grupo_ihs> <agent_install_directory>/logs
chmod -R u+rwX <agent_install_directory>/logs
```

Asegurar que el usuario de IHS tenga lectura y escritura en `logs`.

### 2.4 Variables de entorno para librerías

Antes de instalar y de arrancar el proxy, exportar (y se recomienda añadir a `~/.bashrc`):

```bash
export LD_LIBRARY_PATH=<agent_install_directory>/sdk_lib/lib
```

Ejemplo:

```bash
export LD_LIBRARY_PATH=/opt/appdynamics-sdk-native/sdk_lib/lib
```

### 2.5 Ejecutar el instalador

El script `install.sh` instala el **proxy** del agente:

```bash
<agent_install_directory>/install.sh
```

Ejemplo:

```bash
/opt/appdynamics-sdk-native/install.sh
```

---

## 3. Configurar el agente Apache

### 3.1 Crear el archivo de configuración

Crear un archivo de configuración del agente en el directorio de configuración de IHS, por ejemplo:

```bash
touch /opt/IBM/HTTPServer/conf/appdynamics_agent.conf
```

Ajustar la ruta según la instalación real de IHS (`httpd.conf`, etc.).

### 3.2 Contenido mínimo de `appdynamics_agent.conf`

Ajustar rutas, nombres de aplicación/tier/nodo y parámetros del Controller según el entorno.

**IHS 9.x (Apache 2.4):**

```apache
# Cargar el SDK de AppDynamics (Linux / Alpine)
LoadFile /opt/appdynamics-sdk-native/sdk_lib/lib/libzmq.so.5
LoadFile /opt/appdynamics-sdk-native/sdk_lib/lib/libappdynamics_native_sdk.so

# Módulo Apache Agent - Apache 2.4 (IHS 9.x)
LoadModule appdynamics_module /opt/appdynamics-sdk-native/WebServerAgent/Apache/libmod_appdynamics.so

AppDynamicsEnabled On

# Controller
AppDynamicsControllerHost mycontroller.saas.appdynamics.com
AppDynamicsControllerPort 443
AppDynamicsControllerSSL On

# Credenciales
AppDynamicsAccountName MiEmpresa
AppDynamicsAccessKey <tu-access-key>

# Aplicación, Tier, Node
AppDynamicsApplication MiAppIHS
AppDynamicsTier IHS_Tier
AppDynamicsNode IHS_Node_01
```

**IHS 7.x / 8.x (Apache 2.2):**

```apache
LoadFile /opt/appdynamics-sdk-native/sdk_lib/lib/libzmq.so.5
LoadFile /opt/appdynamics-sdk-native/sdk_lib/lib/libappdynamics_native_sdk.so

# Módulo Apache 2.2 (IHS 7.x - 8.x)
LoadModule appdynamics_module /opt/appdynamics-sdk-native/WebServerAgent/Apache/libmod_appdynamics22.so

AppDynamicsEnabled On
AppDynamicsControllerHost mycontroller.saas.appdynamics.com
AppDynamicsControllerPort 443
AppDynamicsControllerSSL On
AppDynamicsAccountName MiEmpresa
AppDynamicsAccessKey <tu-access-key>
AppDynamicsApplication MiAppIHS
AppDynamicsTier IHS_Tier
AppDynamicsNode IHS_Node_01
```

- `LoadFile` no aplica en AIX; en Linux/Alpine son necesarios.
- `libappdynamics_native_sdk.so` depende de `libzmq` y `libuuid` (en el mismo directorio).

### 3.3 Parámetros principales

| Directiva | Obligatorio | Descripción |
|-----------|-------------|-------------|
| `LoadFile` | Linux/Alpine | Carga `libzmq` y `libappdynamics_native_sdk.so` |
| `LoadModule` | Sí | Ruta a `libmod_appdynamics.so` (2.4) o `libmod_appdynamics22.so` (2.2) |
| `AppDynamicsEnabled` | Sí | `On` para habilitar monitoreo |
| `AppDynamicsControllerHost` | Sí | Host o IP del Controller |
| `AppDynamicsControllerPort` | Sí | Puerto (80/443 SaaS; 8090/8181 on‑premise) |
| `AppDynamicsControllerSSL` | Sí si HTTPS | `On` o `Off` |
| `AppDynamicsAccountName` | Sí | Cuenta AppDynamics |
| `AppDynamicsAccessKey` | Sí | Access Key |
| `AppDynamicsApplication` | Sí | Nombre de la aplicación |
| `AppDynamicsTier` | Sí | Nombre del tier |
| `AppDynamicsNode` | Sí | Nombre del nodo (único por instancia) |

### 3.4 Proxy HTTP (opcional)

Si el agente se conecta al Controller a través de un proxy HTTP:

```apache
AppDynamicsProxyHost <proxy-host>
AppDynamicsProxyPort <proxy-puerto>
```

### 3.5 Múltiples instancias de IHS

- Cada instancia debe usar un `appdynamics_agent.conf` **distinto** y un **directorio de instalación** distinto si hay más de un agente.
- Cada proxy debe tener un **directorio de comunicación** (`AppDynamicsProxyCommDir`) **diferente**.
- Los **nombres de nodo** deben ser **únicos** en la aplicación.

---

## 4. Iniciar el proxy

El proxy Java debe estar en ejecución para que el agente envíe datos al Controller.

### 4.1 Exportar librerías

```bash
export LD_LIBRARY_PATH=<agent_install_directory>/sdk_lib/lib
```

### 4.2 Inicio manual del proxy

Ejecutar como el **mismo usuario** que los workers de IHS:

```bash
nohup <agent_install_directory>/runSDKProxy.sh >>/dev/null 2><agent_install_directory>/logs/proxy.out &
```

Con JRE específico (por ejemplo en AIX cuando se usa `AppDynamicsLaunchProxy`):

```bash
nohup <agent_install_directory>/runSDKProxy.sh --jre-dir=<ruta-jre> >>/dev/null 2><agent_install_directory>/logs/proxy.out &
```

**Recomendación:** Crear un **servicio de sistema** (systemd, init, etc.) que inicie el proxy al arrancar el servidor.

### 4.3 Inicio automático por IHS (`AppDynamicsLaunchProxy`)

En `appdynamics_agent.conf`:

```apache
AppDynamicsLaunchProxy On
```

Si se usan reinicios gracefully (log rotate, etc.) o carga alta, AppDynamics recomienda `AppDynamicsLaunchProxy Off` y **arrancar el proxy manualmente** (o vía servicio).

### 4.4 Host ID único (opcional)

Para definir un **Unique Host ID** en los agentes, editar `runProxy` y añadir:

```bash
set -- "$@" -Dappdynamics.agent.uniqueHostId="<your-unique-host-id>"
```

Tras actualizar el agente, revisar que esta línea siga presente.

---

## 5. Configurar IHS para AppDynamics

### 5.1 Incluir la configuración del agente

En el archivo principal de IHS (`httpd.conf` o el que corresponda), incluir el `appdynamics_agent.conf` **después** de los módulos que se quieran instrumentar. Los módulos cargados **después** del agente no se instrumentan.

Añadir al final del archivo (ajustar ruta si es necesario):

```apache
# Include AppDynamics Apache Agent
Include conf/appdynamics_agent.conf
```

Si hay varias instancias con distintos archivos de configuración:

```apache
Include conf/appdynamics_agent1.conf
```

### 5.2 Reiniciar IHS

```bash
# Ejemplo genérico; ajustar según instalación IHS
apachectl -k restart
# o
/opt/IBM/HTTPServer/bin/apachectl -k restart
```

### 5.3 Generar tráfico

Aplicar carga al servidor web para que el agente detecte transacciones y las envíe al Controller.

---

## 6. Mapear Virtual Hosts a Tiers AppDynamics

Si IHS tiene **Virtual Hosts**, se puede asociar cada uno a un **tier** distinto usando `AppDynamicsApplicationContext`:

```apache
Listen 80
<VirtualHost *:80>
    DocumentRoot "/www/sitio1"
    ServerName sitio1.ejemplo.com
    ...
    AppDynamicsApplicationContext MiApp sitio1.ejemplo.com:80 node01
</VirtualHost>

<VirtualHost *:80>
    DocumentRoot "/www/sitio2"
    ServerName sitio2.ejemplo.com
    ...
    AppDynamicsApplicationContext MiApp sitio2.ejemplo.com:80 node01
</VirtualHost>
```

Sintaxis:

```apache
AppDynamicsApplicationContext <application> <tier> <node>
```

- **application:** nombre de la aplicación en AppDynamics.  
- **tier:** nombre del tier (p. ej. `ServerName:puerto`).  
- **node:** nombre del nodo.

Cada virtual host puede tener su propio tier para una mejor organización en el Controller.

---

## 7. Directivas adicionales

Algunas directivas opcionales útiles en `appdynamics_agent.conf`:

| Directiva | Descripción | Ejemplo |
|-----------|-------------|---------|
| `AppDynamicsBackendNameSegments` | Segmentos de URL usados en el nombre del backend (reverse proxy). Por defecto `0`. | `AppDynamicsBackendNameSegments 2` |
| `AppDynamicsResolveBackends` | Si `On`, los backends de módulos se muestran como downstream; si `Off`, aparecen en el mapa de flujo. Por defecto `On`. | `AppDynamicsResolveBackends Off` |
| `AppDynamicsTraceAsError` | Si `On`, los tracepoints se escriben como errores en los logs de Apache. Por defecto `Off`. | `AppDynamicsTraceAsError Off` |
| `AppDynamicsReportAllInstrumentedModules` | Si `On`, se reportan módulos en todas las fases; si `Off`, solo en fase `HANDLER`. Por defecto `Off`. | `AppDynamicsReportAllInstrumentedModules Off` |
| `AppDynamicsLaunchProxy` | `On` = el agente inicia el proxy; `Off` = hay que iniciarlo manualmente. Por defecto `Off`. | `AppDynamicsLaunchProxy Off` |
| `AppDynamicsProxyCommDir` | Directorio del socket de comunicación con el proxy. Por defecto `<agent_install_directory>/logs/appd-sdk`. La ruta no debe superar **107 caracteres** (límite en Linux). | `AppDynamicsProxyCommDir /ruta/altcommdir` |
| `AppDynamicsRequestCacheCleanupInterval` | Intervalo en ms para limpieza de la caché de requests del proxy (por defecto 60000). | `AppDynamicsRequestCacheCleanupInterval 120000` |
| `AppDynamicsTlsProtocol` | TLS para la conexión al Controller. Por defecto TLS 1.2. | `AppDynamicsTlsProtocol TLSv1.3` |
| `AppDynamicsCustomTags` | Tags personalizados clave=valor, separados por coma. | `AppDynamicsCustomTags Env=Prod,DC=DC1` |

Para **filtrado de datos sensibles**, consultar la documentación oficial: *Filter Sensitive Data*.

---

## 8. Resolución de problemas

### El agente no envía datos al Controller

- Comprobar que el **proxy** esté en ejecución (`runSDKProxy.sh`).
- Verificar **conectividad** al Controller (puerto, firewall, proxy HTTP si aplica).
- Revisar `LD_LIBRARY_PATH` y que las librerías del SDK se encuentren.
- Revisar logs del proxy y del agente en `<agent_install_directory>/logs`.

### Errores o ausencia de logs / directorios

- Verificar **`/dev/random`** y **`/dev/urandom`**.
- Verificar **locale** (`LANG`, `LC_ALL`).
- Comprobar **permisos** en `<agent_install_directory>/logs` para el usuario de IHS.

### Límite de descriptores de archivo

- Ajustar **ulimit** según [Antes de comenzar](#13-entorno-del-sistema).
- Revisar `limits.conf` o la configuración del servicio de IHS.

### IHS con módulos `libstdc++.so.5`

- Revisar [Special Considerations for Apache Web Servers with libstdc++.so.5 Modules](https://docs.appdynamics.com/appd/24.x/24.7/en/application-monitoring/install-app-server-agents/apache-web-server-agent/install-the-apache-agent).
- En 64-bit con Apache 32-bit, usar agente 32-bit y `libstdc++` 32-bit; si hace falta, `LD_PRELOAD` al path correcto antes de `runSDKProxy.sh`.

### Problemas con el proxy

- Consultar *Dynamic Language Agent Proxy* en la documentación para diagnóstico y solución de errores de conexión al Controller.

### Extension de Apache / Machine Agent

Si se usa la **Apache Monitoring Extension** con el Machine Agent, se puede seguir usando. Puede ser necesario **reiniciar el Machine Agent** tras instalar el Apache Agent.

---

## Referencias

- [Install the Apache Agent](https://docs.appdynamics.com/appd/24.x/24.7/en/application-monitoring/install-app-server-agents/apache-web-server-agent/install-the-apache-agent)
- [Download Splunk AppDynamics Software](https://docs.appdynamics.com/appd/24.x/24.7/en/application-monitoring/install-app-server-agents/apache-web-server-agent/install-the-apache-agent)
- [Install the Machine Agent](https://docs.appdynamics.com/appd/24.x/24.7/en/application-monitoring/install-app-server-agents/apache-web-server-agent/install-the-apache-agent)
- [SELinux Installation Issues](https://docs.appdynamics.com/appd/24.x/24.7/en/application-monitoring/install-app-server-agents/apache-web-server-agent/install-the-apache-agent)

---

**Fecha del manual:** Enero 2026  
**Versión documentación AppDynamics:** 24.7
