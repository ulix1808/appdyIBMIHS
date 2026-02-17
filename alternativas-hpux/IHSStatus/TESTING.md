# Guía de Pruebas para SSL con Certificados Autofirmados

Esta guía explica cómo probar que el script `ihs_status_to_appd.py` funciona correctamente con certificados SSL autofirmados antes de desplegarlo en producción.

## Prueba Rápida en el Servidor Productivo

### Opción 1: Prueba Manual con el Script de Prueba

El script `test_ssl_manual.py` prueba directamente con tus servidores IHS reales:

```bash
# 1. Asegúrate de tener las variables de entorno configuradas
export IHS_TARGETS="https://10.10.10.94:40443/server-status?auto|IHS-FINACLE-PROD-1,https://10.10.10.135:40443/server-status?auto|IHS-FINACLE-PROD-2"

# 2. Prueba con SSL_VERIFY=false (debe funcionar)
SSL_VERIFY=false python3 test_ssl_manual.py

# 3. Verifica que todas las conexiones sean exitosas
```

**Resultado esperado con SSL_VERIFY=false:**
```
✓ [IHS-FINACLE-PROD-1]: Éxito
✓ [IHS-FINACLE-PROD-2]: Éxito
Resultados: 2/2 exitosos
✓ TODAS LAS PRUEBAS PASARON
```

### Opción 2: Prueba Directa con el Script Principal

```bash
# 1. Configura SSL_VERIFY=false
export SSL_VERIFY="false"
export IHS_TARGETS="https://10.10.10.94:40443/server-status?auto|IHS-FINACLE-PROD-1,https://10.10.10.135:40443/server-status?auto|IHS-FINACLE-PROD-2"

# 2. Ejecuta el script
python3 ihs_status_to_appd.py

# 3. Verifica que no haya errores SSL
```

**Resultado esperado:**
```
Posted X metrics (2 IHS) to Machine Agent listener.
```

**Si ves errores SSL:**
```
[IHS-FINACLE-PROD-1] Error SSL: certificado autofirmado detectado...
```
Significa que `SSL_VERIFY` no está configurado correctamente. Verifica:
```bash
echo $SSL_VERIFY  # Debe mostrar "false"
```

## Verificación de la Configuración

### Verificar que SSL_VERIFY está configurado

```bash
# Verificar valor actual
echo $SSL_VERIFY

# Si está vacío o muestra "true", configúralo:
export SSL_VERIFY="false"

# Verificar que se guardó
echo $SSL_VERIFY  # Debe mostrar "false"
```

### Verificar que la variable persiste

Si usas `.bash_profile` o `.bashrc`, verifica que la variable esté exportada:

```bash
# Editar .bash_profile
vi ~/.bash_profile

# Agregar la línea:
export SSL_VERIFY="false"

# Recargar configuración
source ~/.bash_profile

# Verificar
echo $SSL_VERIFY
```

## Prueba de Integración Completa

Si tienes acceso a OpenSSL, puedes ejecutar una prueba de integración completa:

```bash
python3 test_ssl_integration.py
```

Este script:
1. Crea un servidor HTTPS local con certificado autofirmado
2. Prueba que el script funciona con `SSL_VERIFY=false`
3. Verifica que falla correctamente con `SSL_VERIFY=true`

## Checklist Antes de Desplegar

- [ ] `SSL_VERIFY="false"` está configurado en el entorno
- [ ] `test_ssl_manual.py` pasa todas las pruebas
- [ ] `ihs_status_to_appd.py` se ejecuta sin errores SSL
- [ ] Las métricas se publican correctamente al Machine Agent
- [ ] La variable `SSL_VERIFY` persiste después de reiniciar sesión

## Solución de Problemas

### Error: "certificate verify failed: self-signed certificate"

**Causa:** `SSL_VERIFY` no está configurado como `"false"` o no está exportado correctamente.

**Solución:**
```bash
export SSL_VERIFY="false"
python3 ihs_status_to_appd.py
```

### Error: "could not read Username for 'https://...'"

**Causa:** Problema de autenticación, no relacionado con SSL.

**Solución:** Verifica que los servidores IHS sean accesibles desde el servidor donde ejecutas el script.

### Las pruebas pasan pero el script sigue fallando

**Causa:** La variable de entorno no está disponible en el contexto donde se ejecuta el script (por ejemplo, en un cron job o systemd service).

**Solución:** Configura la variable en el archivo de servicio o script que ejecuta el monitor:

```bash
# En el script de inicio o systemd service
Environment="SSL_VERIFY=false"
```

## Notas de Seguridad

⚠️ **ADVERTENCIA:** Deshabilitar la verificación SSL (`SSL_VERIFY=false`) hace que el script acepte cualquier certificado, incluyendo certificados inválidos o maliciosos. Esto es aceptable en entornos controlados donde confías en los servidores IHS, pero no debe usarse en entornos públicos o no confiables.

**Alternativa más segura:** Si es posible, configura `SSL_CERT_PATH` con la ruta al certificado CA de tus servidores IHS:

```bash
export SSL_CERT_PATH="/ruta/al/certificado-ca.pem"
```

Esto permite verificar el certificado contra tu CA específica en lugar de deshabilitar completamente la verificación.
