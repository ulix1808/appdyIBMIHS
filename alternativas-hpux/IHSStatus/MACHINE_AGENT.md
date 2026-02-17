# Guía de Referencia: Machine Agent de AppDynamics

Este documento contiene información de referencia sobre cómo iniciar y gestionar el Machine Agent de AppDynamics en el servidor productivo.

## Iniciar el Machine Agent

### Comando de Inicio

```bash
nohup /app/agent_machine_ihs/jdk-17.0.18/bin/java \
  -Dmetric.http.listener=true \
  -Dmetric.http.listener.port=8293 \
  -Dmetric.http.listener.host=127.0.0.1 \
  -jar /app/agent_machine_ihs/machineagent.jar \
  > machineagent.out 2>&1 &
```

### Explicación de Parámetros

- **`nohup`**: Ejecuta el proceso en segundo plano y lo protege de que se termine cuando se cierra la sesión
- **`/app/agent_machine_ihs/jdk-17.0.18/bin/java`**: Ruta al ejecutable de Java (JDK 17.0.18)
- **`-Dmetric.http.listener=true`**: Habilita el HTTP Listener para recibir métricas personalizadas
- **`-Dmetric.http.listener.port=8293`**: Puerto donde el HTTP Listener escuchará las peticiones (puerto 8293)
- **`-Dmetric.http.listener.host=127.0.0.1`**: Dirección IP donde el listener escuchará (localhost)
- **`-jar /app/agent_machine_ihs/machineagent.jar`**: Archivo JAR del Machine Agent
- **`> machineagent.out 2>&1`**: Redirige stdout y stderr al archivo `machineagent.out`
- **`&`**: Ejecuta el proceso en segundo plano

### URL del HTTP Listener

Con esta configuración, el HTTP Listener estará disponible en:
```
http://127.0.0.1:8293/api/v1/metrics
```

Esta es la URL que usa el script `ihs_status_to_appd.py` para publicar métricas (configurada en `APPD_HTTP_LISTENER`).

## Verificar que el Machine Agent está Ejecutándose

### Verificar el Proceso

```bash
ps aux | grep machineagent.jar
```

Deberías ver un proceso Java ejecutándose con el Machine Agent.

### Verificar el Puerto

```bash
netstat -tlnp | grep 8293
# o
ss -tlnp | grep 8293
```

Deberías ver que el puerto 8293 está en estado LISTEN.

### Verificar los Logs

```bash
tail -f /app/agent_machine_ihs/machineagent.out
```

O si el log está en otra ubicación:
```bash
tail -f /app/agent_machine_ihs/logs/machine-agent.log
```

### Probar el HTTP Listener

```bash
curl http://127.0.0.1:8293/api/v1/metrics
```

Si el listener está funcionando, deberías recibir una respuesta (posiblemente vacía o con métricas).

## Detener el Machine Agent

### Encontrar el PID

```bash
ps aux | grep machineagent.jar | grep -v grep | awk '{print $2}'
```

### Detener el Proceso

```bash
# Opción 1: Usando kill con el PID
kill <PID>

# Opción 2: Usando pkill
pkill -f machineagent.jar

# Opción 3: Forzar si no responde
kill -9 <PID>
```

## Reiniciar el Machine Agent

```bash
# 1. Detener el proceso actual
pkill -f machineagent.jar

# 2. Esperar unos segundos
sleep 3

# 3. Iniciar nuevamente
nohup /app/agent_machine_ihs/jdk-17.0.18/bin/java \
  -Dmetric.http.listener=true \
  -Dmetric.http.listener.port=8293 \
  -Dmetric.http.listener.host=127.0.0.1 \
  -jar /app/agent_machine_ihs/machineagent.jar \
  > machineagent.out 2>&1 &
```

## Configuración como Servicio (Opcional)

Para que el Machine Agent se inicie automáticamente al arrancar el servidor, puedes crear un servicio systemd:

### Crear archivo de servicio

```bash
sudo vi /etc/systemd/system/machine-agent.service
```

### Contenido del archivo de servicio

```ini
[Unit]
Description=AppDynamics Machine Agent
After=network.target

[Service]
Type=simple
User=splunk_agent
Group=splunk_agent
WorkingDirectory=/app/agent_machine_ihs
ExecStart=/app/agent_machine_ihs/jdk-17.0.18/bin/java \
  -Dmetric.http.listener=true \
  -Dmetric.http.listener.port=8293 \
  -Dmetric.http.listener.host=127.0.0.1 \
  -jar /app/agent_machine_ihs/machineagent.jar
StandardOutput=file:/app/agent_machine_ihs/machineagent.out
StandardError=file:/app/agent_machine_ihs/machineagent.out
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Comandos para gestionar el servicio

```bash
# Recargar configuración de systemd
sudo systemctl daemon-reload

# Habilitar el servicio para que inicie al arrancar
sudo systemctl enable machine-agent

# Iniciar el servicio
sudo systemctl start machine-agent

# Ver estado
sudo systemctl status machine-agent

# Ver logs
sudo journalctl -u machine-agent -f

# Detener el servicio
sudo systemctl stop machine-agent

# Reiniciar el servicio
sudo systemctl restart machine-agent
```

## Variables de Entorno Importantes

Si el Machine Agent necesita variables de entorno específicas, puedes agregarlas al archivo de servicio:

```ini
[Service]
Environment="SSL_VERIFY=false"
Environment="IHS_TARGETS=https://10.10.10.94:40443/server-status?auto|IHS-FINACLE-PROD-1,https://10.10.10.135:40443/server-status?auto|IHS-FINACLE-PROD-2"
```

## Troubleshooting

### El Machine Agent no inicia

1. Verificar que Java esté instalado y accesible:
   ```bash
   /app/agent_machine_ihs/jdk-17.0.18/bin/java -version
   ```

2. Verificar que el archivo JAR exista:
   ```bash
   ls -la /app/agent_machine_ihs/machineagent.jar
   ```

3. Verificar permisos:
   ```bash
   ls -la /app/agent_machine_ihs/
   ```

4. Revisar los logs:
   ```bash
   tail -100 /app/agent_machine_ihs/machineagent.out
   ```

### El HTTP Listener no responde

1. Verificar que el puerto no esté en uso:
   ```bash
   netstat -tlnp | grep 8293
   ```

2. Verificar firewall:
   ```bash
   # En RHEL/CentOS
   sudo firewall-cmd --list-ports
   
   # Verificar iptables
   sudo iptables -L -n | grep 8293
   ```

3. Probar conectividad local:
   ```bash
   telnet 127.0.0.1 8293
   ```

### El script no puede publicar métricas

1. Verificar que el Machine Agent esté ejecutándose (ver sección anterior)

2. Verificar la URL del listener:
   ```bash
   curl -X POST http://127.0.0.1:8293/api/v1/metrics \
     -H "Content-Type: application/json" \
     -d '[{"metricName":"Test|Metric","aggregatorType":"OBSERVATION","value":1}]'
   ```

3. Verificar que el script tenga la URL correcta:
   ```bash
   echo $APPD_HTTP_LISTENER
   # Debe mostrar: http://127.0.0.1:8293/api/v1/metrics
   ```

## Notas Adicionales

- El archivo `machineagent.out` puede crecer con el tiempo. Considera implementar rotación de logs.
- El Machine Agent necesita acceso de red para comunicarse con el Controller de AppDynamics (si está configurado).
- El HTTP Listener solo acepta conexiones desde localhost (127.0.0.1) por seguridad.
- Asegúrate de que el usuario que ejecuta el Machine Agent tenga los permisos necesarios.
