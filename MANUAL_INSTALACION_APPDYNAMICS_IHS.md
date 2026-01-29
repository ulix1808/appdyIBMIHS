# Manual de Instalación del Agente AppDynamics para IBM HTTP Server (IHS)

Este manual describe los pasos para instalar y configurar el **Apache Agent** de Splunk AppDynamics en **IBM HTTP Server (IHS)**. El agente instrumenta el servidor web y envía datos de rendimiento a un **proxy** (proceso Java separado), que a su vez los envía al Controller.

**Referencia local (todo en este repo):** [docs/REFERENCIA_APPDYNAMICS_APACHE_AGENT.md](docs/REFERENCIA_APPDYNAMICS_APACHE_AGENT.md) — plataformas, libstdc++, AIX, SELinux, proxy, descargas, etc.

---

## Tabla de contenidos

0. [Conceptos clave: Apache Agent vs Java Agent](#0-conceptos-clave-apache-agent-vs-java-agent)
1. [Antes de comenzar](#1-antes-de-comenzar)
2. [Plataformas soportadas y HP-UX / Itanium](#2-plataformas-soportadas-y-hp-ux--itanium) — incl. [§2.3 Alternativas HP-UX](#23-alternativas-para-hp-ux-sin-agente-nativo) y [§2.3.1 Manual mod_status + Machine Agent + Python](#231-manual-de-implementación-paso-a-paso-mod_status--machine-agent--python)
3. [Descargar e instalar el agente](#3-descargar-e-instalar-el-agente)
4. [Configurar el agente Apache](#4-configurar-el-agente-apache)
5. [Iniciar el proxy](#5-iniciar-el-proxy)
6. [Configurar IHS para AppDynamics](#6-configurar-ihs-para-appdynamics)
7. [Mapear Virtual Hosts a Tiers](#7-mapear-virtual-hosts-a-tiers-appdynamics)
8. [Directivas adicionales](#8-directivas-adicionales)
9. [Logging, permisos y troubleshooting](#9-logging-permisos-y-troubleshooting)
10. [Resolución de problemas](#10-resolución-de-problemas)

---

## 0. Conceptos clave: Apache Agent vs Java Agent

### El Apache Web Server Agent **no** es Java

El **Apache Agent** es un agente **nativo (C/C++)** cargado como módulo DSO vía `LoadModule`. **No** usa `JAVA_HOME`, `javaagent.jar` ni opciones JVM.

- **No aplicar aquí:** `-javaagent:...`, `APPDYNAMICS_AGENT_*` de Java Agent, `controller-info.xml` del Java Agent.
- **Java solo es relevante** si:
  - Hay **WebSphere Application Server (WAS)** detrás de IHS y lo instrumentas con el **Java Agent**.
  - Quieres **correlación E2E** (IHS → WAS): el Apache Agent ve el tráfico HTTP; el Java Agent ve la app en WAS.

El **proxy** (`runSDKProxy.sh`) sí es un proceso Java que recibe datos del agente nativo y los envía al Controller. Para ese proxy se necesita JRE (p. ej. `--jre-dir` en AIX o cuando se lanza manualmente). La instrumentación del propio IHS es 100 % nativa.

**Evitar mezclar** en el mismo manual conceptos del Apache Agent con los del Java Agent; genera confusión y configuraciones erróneas.

---

## 1. Antes de comenzar

### 1.1 IHS ≠ Apache “vanilla”

**IBM HTTP Server** está basado en Apache (p. ej. IHS 9.0.5.11 ≈ Apache 2.4.x “IBM customized”), pero no es Apache genérico. La documentación oficial de AppDynamics aplica **conceptualmente** a IHS, no de forma literal (rutas, paths, plataformas).

Para que el Apache Agent funcione con IHS hace falta:

- **MPM:** `prefork` o `worker` (**no** `event`).
- **mod_so (DSO):** habilitado para cargar `.so` dinámicamente.
- **Módulo `.so`** compilado para la **arquitectura y SO exactos** del servidor (véase [§2](#2-plataformas-soportadas-y-hp-ux--itanium)).

### 1.2 Requisitos de software y sistema

- **Versión de IHS:** Comprobar que la versión y el sistema operativo estén soportados. Ver [Plataformas y versiones soportadas](docs/REFERENCIA_APPDYNAMICS_APACHE_AGENT.md#1-plataformas-y-versiones-soportadas-supported-apache-web-servers) en la referencia local.
- **Módulo según versión de IHS:**
  - **IHS 7.x – 8.x:** módulo Apache 2.2 → `libmod_appdynamics22.so`
  - **IHS 9.x:** módulo Apache 2.4 → `libmod_appdynamics.so`
- **Linux con `libstdc++.so.5`:** Si IHS usa módulos que dependen de `libstdc++.so.5`, ver [Consideraciones libstdc++.so.5](docs/REFERENCIA_APPDYNAMICS_APACHE_AGENT.md#2-consideraciones-libstdcso5-ihs--ohs) en la referencia local. Es habitual en IHS y OHS.
- **AIX:** Ver [Prerrequisitos en AIX](docs/REFERENCIA_APPDYNAMICS_APACHE_AGENT.md#3-prerrequisitos-en-aix) en la referencia local si aplica.

### 1.3 Usuario y permisos

- Instalar y ejecutar el agente con el **mismo usuario y grupo** con el que IHS arranca los procesos worker.
- El usuario que ejecuta IHS debe tener **lectura y escritura** en el directorio de logs del agente: `<agent_install_directory>/logs`.

### 1.4 Entorno del sistema

- **`/dev/random` o `/dev/urandom`:** Deben estar correctamente configurados. El agente usa generación de números aleatorios; si no, pueden fallar creación de logs, directorios o el envío de datos al Controller.
- **Límite de descriptores de archivo (`ulimit -n`):**
  - **MPM_Worker:** `1024 + ServerLimit + (2 × ServerLimit × ThreadsPerChild)`
  - **Otros modos:** `(Número total de workers Apache activos concurrentemente × 2) + 1024`
  - Configurar en `/etc/security/limits.conf` (Linux; requiere reinicio) o con `ulimit -n` en la sesión del usuario. En **HP-UX** el mecanismo equivalente según el entorno (p. ej. `limits` en `/etc/login` o parámetros del subsistema).
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

### 1.5 Información necesaria del Controller

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

### 1.6 APR y compatibilidad binaria

El Apache Agent se enlaza dinámicamente contra **APR** (Apache Portable Runtime). Si tu IHS usa, por ejemplo, **APR 1.5.1** y **APR-UTIL 1.5.2**, el `.so` del agente debe ser compatible con esas versiones y con el **toolchain / ABI** del entorno.

- **Incompatibilidad:** Un `.so` compilado con otra versión de APR, otro compilador o otro ABI puede **cargar** y luego **fallar en runtime** (crashes, símbolos no resueltos). Es uno de los fallos más difíciles de diagnosticar.
- **Validar dependencias:**
  - **Linux:** `ldd <ruta>/libmod_appdynamics.so` (o `libmod_appdynamics22.so`) y revisar que las libs (APR, libc, etc.) se resuelvan correctamente.
  - **HP-UX:** `chatr <ruta>/libmod_appdynamics.so` (y análogo para el `.so` del SDK) para inspeccionar dependencias compartidas.
- **Documentar:** Versión de APR y APR-UTIL del IHS y, si el `.so` es custom, con qué APR/toolchain se compiló.

---

## 2. Plataformas soportadas y HP-UX / Itanium

### 2.1 Plataformas con binario oficial

AppDynamics publica binarios del Apache Agent para plataformas como:

- **Linux** x86_64 (y variantes 32-bit donde aplique)
- **AIX** (Power)
- **Solaris** (SPARC)
- **Windows**

Ver [Plataformas soportadas](docs/REFERENCIA_APPDYNAMICS_APACHE_AGENT.md#1-plataformas-y-versiones-soportadas-supported-apache-web-servers) y [Descargas](docs/REFERENCIA_APPDYNAMICS_APACHE_AGENT.md#8-descargas-del-apache-agent) en la referencia local.

### 2.2 HP-UX e Itanium (IA-64): **no hay “happy path”**

**HP-UX en Itanium (IA-64)** **no** está listado como plataforma soportada para el Apache Agent. En la práctica:

- **No existe binario `.so` oficial precompilado** para HP-UX Itanium.
- Quien diga *“solo descárgalo y ya”* en este entorno **está equivocado**.

**Implicaciones:**

- Un `.so` compilado para **linux-x86_64**, **aix-ppc**, **solaris-sparc**, etc. **no** se cargará en Itanium. En HP-UX suelen aparecer errores como:
  - `Exec format error`
  - `Cannot load module ...`
  - `Symbol not found`
- La **arquitectura debe coincidir exactamente**: IA-64 ≠ x86_64.

Si en tu entorno hay **IHS sobre HP-UX Itanium** (p. ej. Apache 2.4.12 IBM customized, APR 1.5.1, Itanium 64-bit):

1. **Documentar siempre el origen del `.so`**: si es build interno, port realizado por alguien, o binary de otro OS/arquitectura (en cuyo caso no es válido).
2. **No asumir** que el paquete estándar de AppDynamics sirve “tal cual” en HP-UX Itanium.
3. Valorar con AppDynamics / Soporte si existe build especial o roadmap para HP-UX Itanium.

### 2.3 Alternativas para HP-UX (sin agente nativo)

Como el Apache Agent **no corre de forma nativa** en HP-UX, se pueden usar estas opciones para obtener visibilidad sobre IHS sin binarios propietarios en el host HP-UX.

**Requisitos para el manual de implementación (mod_status + Machine Agent + Python):** se necesita un **host Linux** con **mínimo 1 CPU y 4 GB RAM** para desplegar el **Machine Agent** de AppDynamics y el **script Python** que hace scraping de `server-status` y envía métricas al Controller. En HP-UX solo se modifica la configuración de IHS (mod_status); no se instalan binarios ni forwarders.

---

#### Opción A: Métricas “tipo salud” del IHS (sin agente)

Habilitar **`mod_status`** en IHS y recolectar métricas **desde fuera** (scraping).

**En IHS (`httpd.conf`):**

1. Habilitar `mod_status`: asegurarse de que esté cargado (`LoadModule status_module ...`) y de tener `ExtendedStatus On` para que `?auto` incluya métricas detalladas.
2. Exponer **`/server-status?auto`** solo a la IP del collector (ACL estricta). Ejemplo (Apache 2.4 / IHS 9.x):

   ```apache
   <Location /server-status>
       SetHandler server-status
       Require ip 10.0.0.50
   </Location>
   ExtendedStatus On
   ```

   Ajustar `Require ip` a la IP del host que hace scraping. En IHS 7.x/8.x (Apache 2.2) usar `Order`, `Allow from`, `Deny from` en su lugar. Evitar exponer `server-status` a redes públicas.

**En un host Linux** (donde sí corre OTel Collector, Telegraf, Prometheus, etc.):

- Hacer **scraping** de `http://<ihs-host>:<puerto>/server-status?auto`.
- Convertir la salida a métricas: requests, busy/idle workers, scoreboard, bytes servidos, etc.

**Ventaja:** cero binarios en HP-UX; solo configuración de IHS.  
**Limitación:** no proporciona **trazas** (transacciones end-to-end); es salud, throughput y utilización.

**Si por política no pueden exponer `server-status`:** usar como alternativa métricas derivadas de **parsing de `access_log`** (ver opción B) más **checks de puertos** (p. ej. que el puerto HTTP/HTTPS responda) para un mínimo de “salud”.

---

#### Opción B: Logs de acceso y error (la fuente de verdad del webserver)

Los logs son la fuente de verdad para IHS legacy:

- **`access_log`:** latencia (si se agrega `%D` en `LogFormat` — tiempo en µs por petición), bytes, códigos de estado, URL, user-agent, etc. Ejemplo de `LogFormat` con `%D`:  
  `LogFormat "%h %l %u %t \"%r\" %>s %b %D" combined`
- **`error_log`:** fallos de backend, SSL, timeouts, problemas de plugins.

**Recomendación:** **no** ejecutar un forwarder nuevo en HP-UX IA-64. Mejor:

- **Recolectar logs de forma remota** y parsear en un host Linux (o en el mismo collector):
  - **Syslog:** enviar `access_log` y `error_log` vía syslog desde IHS/HP-UX hacia un servidor Linux que concentra logs (rsyslog, syslog-ng, etc.) y desde ahí a OTel/Telegraf/Prometheus/Loki o tu stack de observabilidad.
  - **Copia remota:** `rsync` o `scp` periódicos de los archivos de log a un host Linux que los procesa (tail + parser, Filebeat, Fluent Bit, etc.).
  - **NFS u otro almacenamiento compartido:** montar el directorio de logs de IHS en un host Linux y hacer tail/lectura desde ahí.
  - **Infraestructura existente:** si ya hay recolección de logs (SIEM, centralizada), consumir desde ahí y extraer métricas o eventos.

Con el parsing de `access_log` se pueden derivar series de tiempo (requests/s, latencias, códigos 4xx/5xx, etc.). Con `error_log`, alertas y eventos de fallos. Todo sin correr agentes ni forwarders adicionales en HP-UX.

---

#### 2.3.1 Manual de implementación paso a paso (mod_status + Machine Agent + Python)

Este manual detalla cómo obtener métricas “tipo salud” de IHS en HP-UX usando **mod_status**, un **Machine Agent** en un host Linux y un **script Python** que hace scraping y publica métricas al HTTP Listener del Machine Agent. Los archivos de la extensión (config, script, README) están en el repo en [alternativas-hpux/IHSStatus/](alternativas-hpux/IHSStatus/).

**Requisitos:** host Linux con **mínimo 1 CPU y 4 GB RAM**, Machine Agent de AppDynamics, Python 3 y `requests`. En HP-UX solo cambios de config en IHS.

---

##### A) Config en IBM HTTP Server (IHS) – HP-UX

1. Habilitar **mod_status** (asegurarse de que el módulo esté cargado).
2. Añadir un **`Location`** para `server-status` con **ACL restringida solo al host Linux** donde corre el Machine Agent.

Ejemplo (ajusta paths y ACL a tu estándar; en IHS el módulo puede ser `mod_status.so` o `mod_status.sl` según versión):

```apache
# 1) Asegurar que mod_status esté activo
LoadModule status_module modules/mod_status.so

# 2) Endpoint de status
ExtendedStatus On

<Location "/server-status">
    SetHandler server-status

    # Solo permitir al collector Linux
    Require ip 10.10.10.50
</Location>
```

En IHS 7.x/8.x (Apache 2.2) usar `Order`, `Allow from`, `Deny from` en lugar de `Require ip`. La ACL debe restringir el acceso **únicamente** al host que hace el scraping.

**Validación:**

```bash
apachectl -M | grep status
curl "http://localhost:<PUERTO>/server-status?auto"
```

Sustituir `<PUERTO>` por el puerto de IHS. Comprobar que la salida incluye líneas como `BusyWorkers`, `IdleWorkers`, `ReqPerSec`, etc.

---

##### B) Machine Agent (Linux) – habilitar HTTP Listener

El Machine Agent debe exponer el **HTTP Listener** para recibir métricas que el script Python envía por POST.

- Directorio de despliegue típico: `/opt/appdynamics/machine-agent/`
- Añadir al arranque del Machine Agent (JVM / script de inicio) las propiedades:

```
-Dmetric.http.listener=true
-Dmetric.http.listener.port=8293
-Dmetric.http.listener.host=127.0.0.1
```

El listener quedará escuchando en `127.0.0.1:8293` (solo local). Reiniciar el Machine Agent y validar:

```bash
ss -lntp | grep 8293
curl -i http://127.0.0.1:8293/
```

---

##### C) Extensión “script-based” para ejecutar Python cada minuto (Machine Agent)

Estructura bajo el Machine Agent:

```
/opt/appdynamics/machine-agent/monitors/IHSStatus/
  ├── config.yml
  ├── ihs_status_to_appd.py
  └── README.md
```

Los archivos listos para copiar están en el repo en [alternativas-hpux/IHSStatus/](alternativas-hpux/IHSStatus/).

**`config.yml`** (ejemplo; ajusta `IHS_STATUS_URL` a la IP/puerto de tu IHS en HP-UX):

```yaml
extensionName: "IHSStatus"
version: "1.0.0"
language: "python"

executionFrequencyInSeconds: 60
timeoutInSeconds: 20

command: ["python3", "ihs_status_to_appd.py"]

env:
  IHS_STATUS_URL: "http://10.10.10.20:80/server-status?auto"
  APPD_HTTP_LISTENER: "http://127.0.0.1:8293/api/v1/metrics"
  METRIC_PREFIX: "Custom Metrics|Web|IHS|HPUX"
```

El script **`ihs_status_to_appd.py`** hace `GET` a `IHS_STATUS_URL`, parsea `server-status?auto`, construye el payload de métricas y hace `POST` a `APPD_HTTP_LISTENER`. Las métricas se publican con el prefijo `METRIC_PREFIX`.

**Dependencias en el host Linux:**

```bash
python3 -m pip install requests
```

El contrato exacto de `config.yml` puede variar según la versión del Machine Agent y el framework de extensiones (script-based). Si usas otro estilo de extensión, adapta `command` y `env` según la documentación de tu instalación.

---

##### D) Dónde ver las métricas en AppDynamics (clásico)

En el Controller de AppDynamics:

- **Metric Browser** → buscar por ejemplo:
  - `Custom Metrics|Web|IHS|HPUX|BusyWorkers`
  - `Custom Metrics|Web|IHS|HPUX|IdleWorkers`
  - `Custom Metrics|Web|IHS|HPUX|ReqPerSec`
  - `Custom Metrics|Web|IHS|HPUX|BytesPerSec`
  - `Custom Metrics|Web|IHS|HPUX|TotalAccesses`
  - `Custom Metrics|Web|IHS|HPUX|UptimeSec`
  - etc.

---

## 3. Descargar e instalar el agente

### 3.1 Descarga

1. Descargar el **Apache Agent** desde el **Getting Started** del Controller o desde el **portal de descargas** de AppDynamics (ver [Descargas del Apache Agent](docs/REFERENCIA_APPDYNAMICS_APACHE_AGENT.md#8-descargas-del-apache-agent) en la referencia local).
2. Elegir el paquete según **SO y arquitectura exactas** (p. ej. `64bit-linux`, `64bit-aix`). **No** usar un binario de otra arquitectura (p. ej. x86_64 en Itanium/IA-64): no cargará.

### 3.2 Extracción

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

### 3.3 Permisos en logs

```bash
chown -R <usuario_ihs>:<grupo_ihs> <agent_install_directory>/logs
chmod -R u+rwX <agent_install_directory>/logs
```

Asegurar que el usuario de IHS tenga lectura y escritura en `logs`.

### 3.4 Variables de entorno para librerías

Antes de instalar y de arrancar el proxy, exportar (y se recomienda añadir a `~/.bashrc`):

```bash
export LD_LIBRARY_PATH=<agent_install_directory>/sdk_lib/lib
```

Ejemplo:

```bash
export LD_LIBRARY_PATH=/opt/appdynamics-sdk-native/sdk_lib/lib
```

En **HP-UX** el equivalente suele ser `SHLIB_PATH` (y en algunos casos `LD_LIBRARY_PATH`); revisar la documentación del entorno.

### 3.5 Ejecutar el instalador

El script `install.sh` instala el **proxy** del agente:

```bash
<agent_install_directory>/install.sh
```

Ejemplo:

```bash
/opt/appdynamics-sdk-native/install.sh
```

---

## 4. Configurar el agente Apache

### 4.1 Crear el archivo de configuración

Crear un archivo de configuración del agente en el directorio de configuración de IHS, por ejemplo:

```bash
touch /opt/IBM/HTTPServer/conf/appdynamics_agent.conf
```

Ajustar la ruta según la instalación real de IHS (`httpd.conf`, etc.).

### 4.2 Contenido mínimo de `appdynamics_agent.conf`

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

### 4.3 Parámetros principales

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

### 4.4 Proxy HTTP (opcional)

Si el agente se conecta al Controller a través de un proxy HTTP:

```apache
AppDynamicsProxyHost <proxy-host>
AppDynamicsProxyPort <proxy-puerto>
```

### 4.5 Múltiples instancias de IHS

- Cada instancia debe usar un `appdynamics_agent.conf` **distinto** y un **directorio de instalación** distinto si hay más de un agente.
- Cada proxy debe tener un **directorio de comunicación** (`AppDynamicsProxyCommDir`) **diferente**.
- Los **nombres de nodo** deben ser **únicos** en la aplicación.

---

## 5. Iniciar el proxy

El **proxy** (proceso Java) debe estar en ejecución para que el agente envíe datos al Controller. El agente en IHS es nativo; solo el proxy usa JRE.

### 5.1 Exportar librerías

```bash
export LD_LIBRARY_PATH=<agent_install_directory>/sdk_lib/lib
```

### 5.2 Inicio manual del proxy

Ejecutar como el **mismo usuario** que los workers de IHS:

```bash
nohup <agent_install_directory>/runSDKProxy.sh >>/dev/null 2><agent_install_directory>/logs/proxy.out &
```

Con JRE específico (por ejemplo en AIX cuando se usa `AppDynamicsLaunchProxy`):

```bash
nohup <agent_install_directory>/runSDKProxy.sh --jre-dir=<ruta-jre> >>/dev/null 2><agent_install_directory>/logs/proxy.out &
```

**Recomendación:** Crear un **servicio de sistema** (systemd, init, etc.) que inicie el proxy al arrancar el servidor.

### 5.3 Inicio automático por IHS (`AppDynamicsLaunchProxy`)

En `appdynamics_agent.conf`:

```apache
AppDynamicsLaunchProxy On
```

Si se usan reinicios gracefully (log rotate, etc.) o carga alta, AppDynamics recomienda `AppDynamicsLaunchProxy Off` y **arrancar el proxy manualmente** (o vía servicio).

### 5.4 Host ID único (opcional)

Para definir un **Unique Host ID** en los agentes, editar `runProxy` y añadir:

```bash
set -- "$@" -Dappdynamics.agent.uniqueHostId="<your-unique-host-id>"
```

Tras actualizar el agente, revisar que esta línea siga presente.

---

## 6. Configurar IHS para AppDynamics

### 6.1 Incluir la configuración del agente

En el archivo principal de IHS (`httpd.conf` o el que corresponda), incluir el `appdynamics_agent.conf` **después** de los módulos que se quieran instrumentar. Los módulos cargados **después** del agente no se instrumentan.

**Rutas típicas en IHS:** el manual oficial suele asumir `modules/` genérico. En IHS es frecuente usar `$IHS_HOME/modules` o `$IHS_HOME/libexec`. Usar **rutas absolutas** en `LoadModule` / `LoadFile` para evitar ambigüedades. Ajustar según tu instalación.

Añadir al final del archivo (ajustar ruta si es necesario):

```apache
# Include AppDynamics Apache Agent
Include conf/appdynamics_agent.conf
```

Si hay varias instancias con distintos archivos de configuración:

```apache
Include conf/appdynamics_agent1.conf
```

#### Validar `mod_so` (DSO) antes de cargar el agente

El agente se carga como módulo DSO. Si `mod_so` no está disponible, `LoadModule` fallará.

- Ejecutar `apachectl -l` (o el equivalente en tu IHS, p. ej. `$IHS_HOME/bin/apachectl -l`).
- Comprobar que **`mod_so.c`** aparece en la lista de módulos compilados.
- Si no está, no se podrá cargar ningún `.so` vía `LoadModule`; hay que recompilar IHS/Apache con DSO o usar una instalación que lo incluya.

Sin esta validación, el riesgo es hacer una **configuración ciega**: incluir el `Include` y al reiniciar encontrarse con errores de carga del módulo.

### 6.2 Reiniciar IHS

```bash
# Ejemplo genérico; ajustar según instalación IHS
apachectl -k restart
# o
/opt/IBM/HTTPServer/bin/apachectl -k restart
```

### 6.3 Generar tráfico

Aplicar carga al servidor web para que el agente detecte transacciones y las envíe al Controller.

---

## 7. Mapear Virtual Hosts a Tiers AppDynamics

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

## 8. Directivas adicionales

Algunas directivas opcionales útiles en `appdynamics_agent.conf`:

| Directiva | Descripción | Ejemplo |
|-----------|-------------|---------|
| `AppDynamicsBackendNameSegments` | Segmentos de URL usados en el nombre del backend (reverse proxy). Por defecto `0`. | `AppDynamicsBackendNameSegments 2` |
| `AppDynamicsResolveBackends` | Si `On`, los backends de módulos se muestran como downstream; si `Off`, aparecen en el mapa de flujo. Por defecto `On`. | `AppDynamicsResolveBackends Off` |
| `AppDynamicsTraceAsError` | Si `On`, los tracepoints se escriben como errores en los logs de Apache. Por defecto `Off`. | `AppDynamicsTraceAsError Off` |
| `AppDynamicsReportAllInstrumentedModules` | Si `On`, se reportan módulos en todas las fases; si `Off`, solo en fase `HANDLER`. Por defecto `Off`. | `AppDynamicsReportAllInstrumentedModules Off` |
| `AppDynamicsLaunchProxy` | `On` = el agente inicia el proxy; `Off` = hay que iniciarlo manualmente. Por defecto `Off`. | `AppDynamicsLaunchProxy Off` |
| `AppDynamicsProxyCommDir` | Directorio del socket de comunicación con el proxy. Por defecto `<agent_install_directory>/logs/appd-sdk`. En **Linux** la ruta no debe superar **107 caracteres** (límite del socket); en HP-UX u otros SO el límite puede diferir—evitar paths muy largos. | `AppDynamicsProxyCommDir /ruta/altcommdir` |
| `AppDynamicsRequestCacheCleanupInterval` | Intervalo en ms para limpieza de la caché de requests del proxy (por defecto 60000). | `AppDynamicsRequestCacheCleanupInterval 120000` |
| `AppDynamicsTlsProtocol` | TLS para la conexión al Controller. Por defecto TLS 1.2. | `AppDynamicsTlsProtocol TLSv1.3` |
| `AppDynamicsCustomTags` | Tags personalizados clave=valor, separados por coma. | `AppDynamicsCustomTags Env=Prod,DC=DC1` |

Para **filtrado de datos sensibles**, ver [Filtrado de datos sensibles](docs/REFERENCIA_APPDYNAMICS_APACHE_AGENT.md#6-filtrado-de-datos-sensibles-filter-sensitive-data) en la referencia local.

---

## 9. Logging, permisos y troubleshooting

La documentación oficial suele citar `LogLevel info` y un archivo tipo `appdynamics_agent.log`. En entornos IHS (y sobre todo **HP-UX**), los problemas de **permisos y rutas de log** son frecuentes y pueden hacer que el agente **cargue** pero **no reporte nada** (silencio total en el Controller).

### 9.1 Ownership y permisos del directorio de logs

- El directorio de logs del agente (p. ej. `<agent_install_directory>/logs`) debe ser **propiedad del usuario que ejecuta IHS** (y opcionalmente del grupo adecuado).
- Ese usuario debe tener **lectura y escritura** en el directorio y en los ficheros que el agente y el proxy crean (logs, sockets, etc.).
- Comandos típicos (ajustar usuario/grupo y ruta):

  ```bash
  chown -R <usuario_ihs>:<grupo_ihs> <agent_install_directory>/logs
  chmod -R u+rwX <agent_install_directory>/logs
  ```

### 9.2 Ruta absoluta del log

- Usar **rutas absolutas** para cualquier directorio o archivo de log que se configure (agent, proxy, appd-sdk, etc.).
- Evitar depender del directorio de trabajo o de rutas relativas; en IHS/HP-UX el contexto de ejecución puede variar y provocar que los logs se escriban en sitios inesperados o que falle la escritura.

### 9.3 HP-UX: permisos y Trusted HP-UX

- En **HP-UX**, los fallos de permisos de escritura en logs son habituales. Revisar `umask`, ownership y ACLs si se usan.
- **SELinux** no existe en HP-UX; si en tu entorno se usa **Trusted HP-UX** u otros mecanismos de seguridad (MAC, etc.), pueden restringir escritura en determinados paths. Asegurarse de que el usuario de IHS tenga permiso para escribir en `<agent_install_directory>/logs` y en sockets bajo ese árbol.

### 9.4 El agente “carga” pero no reporta nada

Si el módulo carga (`LoadModule` OK) pero no aparece actividad en el Controller:

1. Comprobar **ownership y permisos** del directorio de logs y archivos creados por el agente/proxy.
2. Verificar que la **ruta de log** es absoluta y escribible.
3. Revisar logs del **proxy** y del agente (p. ej. `proxy.out`, `appdynamics_agent.log` si existe) en busca de errores de conexión o escritura.
4. Confirmar que el **proxy** está en ejecución y que `AppDynamicsProxyCommDir` (si se usa) es accesible y con permisos correctos.

---

## 10. Resolución de problemas

### El agente no envía datos al Controller

- Comprobar que el **proxy** esté en ejecución (`runSDKProxy.sh`).
- Verificar **conectividad** al Controller (puerto, firewall, proxy HTTP si aplica).
- Revisar `LD_LIBRARY_PATH` (o `SHLIB_PATH` en HP-UX) y que las librerías del SDK se encuentren.
- Revisar logs del proxy y del agente en `<agent_install_directory>/logs`.
- Si el módulo **carga** pero no hay datos en el Controller, ver [§9 Logging, permisos y troubleshooting](#9-logging-permisos-y-troubleshooting) (ownership, permisos, ruta absoluta del log).

### Errores o ausencia de logs / directorios

- Verificar **`/dev/random`** y **`/dev/urandom`**.
- Verificar **locale** (`LANG`, `LC_ALL`).
- Comprobar **permisos** en `<agent_install_directory>/logs` para el usuario de IHS.

### Límite de descriptores de archivo

- Ajustar **ulimit** según [§1.4 Entorno del sistema](#14-entorno-del-sistema).
- Revisar `limits.conf` o la configuración del servicio de IHS.

### IHS con módulos `libstdc++.so.5`

- Ver [Consideraciones libstdc++.so.5](docs/REFERENCIA_APPDYNAMICS_APACHE_AGENT.md#2-consideraciones-libstdcso5-ihs--ohs) en la referencia local.
- En 64-bit con Apache 32-bit, usar agente 32-bit y `libstdc++` 32-bit; si hace falta, `LD_PRELOAD` al path correcto antes de `runSDKProxy.sh`.

### Errores al cargar el módulo: `Exec format error`, `Cannot load module`, `Symbol not found`

- Suele indicar que el **`.so` no corresponde a la arquitectura o SO** del servidor (p. ej. .so para x86_64 usado en Itanium/IA-64). Ver [§2 Plataformas y HP-UX/Itanium](#2-plataformas-soportadas-y-hp-ux--itanium). Solo se puede usar un binario compilado para la arquitectura exacta.

### Problemas con el proxy

- Ver [Proxy (Dynamic Language Agent Proxy) y troubleshooting](docs/REFERENCIA_APPDYNAMICS_APACHE_AGENT.md#7-proxy-dynamic-language-agent-proxy-y-troubleshooting) en la referencia local.

### Extension de Apache / Machine Agent

Si se usa la **Apache Monitoring Extension** con el Machine Agent, se puede seguir usando. Puede ser necesario **reiniciar el Machine Agent** tras instalar el Apache Agent. Ver [Machine Agent y Apache Monitoring Extension](docs/REFERENCIA_APPDYNAMICS_APACHE_AGENT.md#4-machine-agent-y-apache-monitoring-extension) en la referencia local.

---

## Referencias (todo en este repo)

- [Referencia AppDynamics Apache Agent](docs/REFERENCIA_APPDYNAMICS_APACHE_AGENT.md): plataformas soportadas, libstdc++.so.5, AIX, SELinux, filtrado de datos sensibles, proxy, descargas.
- [Checklist de instalación](CHECKLIST_INSTALACION_IHS.md).
- [README](README.md).

---

**Fecha del manual:** Enero 2026  
**Versión documentación AppDynamics:** 24.7
