# Instrucciones: Configuración de Certificado SSL para IHSStatus Plugin

## Problema
El plugin `ihs_status_to_appd.py` falla con certificados SSL autofirmados mostrando el error:
```
SSLError: certificate verify failed: self-signed certificate in certificate chain
```

## Solución

### Paso 1: Actualizar el archivo Python

**Reemplazar el archivo:**
```bash
cd /app/agent_machine_ihs/monitors/IHSStatus
# Descargar o copiar el nuevo archivo ihs_status_to_appd.py desde el repositorio
# https://github.com/ulix1808/appdyIBMIHS/blob/main/alternativas-hpux/IHSStatus/ihs_status_to_appd.py
```

### Paso 2: Configurar el certificado SSL

Tienes **dos opciones**:

#### Opción A: Deshabilitar verificación SSL (rápido, menos seguro)

Agregar en el archivo de variables de entorno (ej. `env.sh` o donde se definan las variables del Machine Agent):

```bash
export SSL_VERIFY="false"
```

**Nota:** Esto desactiva la verificación de certificados SSL. Úsalo solo en entornos controlados.

#### Opción B: Cargar certificado CA (recomendado para producción)

1. **Obtener el certificado del servidor IHS:**
   ```bash
   # Desde el host Linux donde corre el Machine Agent
   openssl s_client -showcerts -connect 10.10.10.94:40443 </dev/null 2>/dev/null | \
     openssl x509 -outform PEM > /app/agent_machine_ihs/monitors/IHSStatus/ihs-ca.pem
   ```
   
   Repetir para cada servidor IHS si tienen certificados diferentes, o usar el mismo certificado si comparten CA.

2. **Configurar la variable de entorno:**
   ```bash
   export SSL_CERT_PATH="/app/agent_machine_ihs/monitors/IHSStatus/ihs-ca.pem"
   ```

### Paso 3: Aplicar los cambios

1. **Si usas archivo `env.sh`:**
   ```bash
   source /app/agent_machine_ihs/monitors/IHSStatus/env.sh
   ```

2. **Reiniciar el Machine Agent** para que cargue las nuevas variables de entorno.

3. **Verificar que funciona:**
   ```bash
   cd /app/agent_machine_ihs/monitors/IHSStatus
   python3 ihs_status_to_appd.py
   ```

   Deberías ver:
   ```
   Posted X metrics (Y IHS) to Machine Agent listener.
   ```

## Variables de entorno actualizadas

El script ahora soporta estas variables adicionales:

- `SSL_VERIFY`: `"true"` (default) o `"false"` para deshabilitar verificación
- `SSL_CERT_PATH`: Ruta al archivo de certificado CA (`.pem` o `.crt`)

## Ejemplo completo de configuración

```bash
# En /app/agent_machine_ihs/monitors/IHSStatus/env.sh o similar

# Targets IHS (HTTPS con certificados autofirmados)
export IHS_TARGETS="https://10.10.10.94:40443/SSO/ui/SSOLogin.html|IHS-FINACLE-PROD-1,https://10.10.10.135:40443/SSO/ui/SSOLogin.html|IHS-FINACLE-PROD-2"

# Configuración SSL - Opción 1: Deshabilitar verificación
export SSL_VERIFY="false"

# O Opción 2: Usar certificado CA
# export SSL_CERT_PATH="/app/agent_machine_ihs/monitors/IHSStatus/ihs-ca.pem"

# Resto de configuración
export APPD_HTTP_LISTENER="http://127.0.0.1:8293/api/v1/metrics"
export METRIC_PREFIX="Custom Metrics|Web|IHS|HPUX"
```

## Referencias

- Repositorio: https://github.com/ulix1808/appdyIBMIHS
- Documentación completa: `alternativas-hpux/IHSStatus/README.md`
