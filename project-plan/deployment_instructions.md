# Deployment Instructions for Linear MCP Server

## Overview

This document provides detailed instructions for deploying the Linear MCP Server in various environments. It covers deployment options, configuration, security considerations, and maintenance procedures to ensure a reliable and secure operation of the server.

## Deployment Options

### Docker Deployment (Recommended)

Docker provides the simplest and most consistent way to deploy the Linear MCP Server.

#### Prerequisites

- Docker Engine (version 20.10.0 or later)
- Docker Compose (version 2.0.0 or later) - optional but recommended
- Linear API key
- Network access to port 8080 (or your configured port)

#### Deployment Steps

1. **Create a Docker Compose File**

   Create a file named `docker-compose.yml` with the following content:

   ```yaml
   version: '3.8'

   services:
     linear-mcp-server:
       image: linearapp/mcp-server:latest
       container_name: linear-mcp-server
       restart: unless-stopped
       ports:
         - "8080:8080"
       environment:
         - LINEAR_API_KEY=your_linear_api_key
         - LINEAR_MCP_SERVER_PORT=8080
         - LINEAR_MCP_LOG_LEVEL=info
       volumes:
         - ./config:/app/config
         - ./logs:/app/logs
   ```

2. **Create a Configuration Directory**

   ```bash
   mkdir -p config logs
   ```

3. **Create a Configuration File (Optional)**

   Create a file named `config/config.yaml` with your custom configuration:

   ```yaml
   server:
     port: 8080
     max_connections: 100

   linear:
     auth:
       method: "api_key"
       # API key provided via LINEAR_API_KEY environment variable

   logging:
     level: "info"
     file: "/app/logs/server.log"
   ```

4. **Start the Server**

   ```bash
   docker-compose up -d
   ```

5. **Verify Deployment**

   ```bash
   # Check if container is running
   docker ps

   # Check logs
   docker logs linear-mcp-server

   # Test server health
   curl http://localhost:8080/health
   ```

#### Updating the Server

To update to a new version:

```bash
# Pull the latest image
docker-compose pull

# Restart the container
docker-compose up -d
```

### Kubernetes Deployment

For production environments, Kubernetes provides scalability and reliability.

#### Prerequisites

- Kubernetes cluster (version 1.19 or later)
- kubectl configured to access your cluster
- Linear API key stored as a Kubernetes secret

#### Deployment Steps

1. **Create a Namespace**

   ```bash
   kubectl create namespace linear-mcp
   ```

2. **Create a Secret for the API Key**

   ```bash
   kubectl create secret generic linear-api-key \
     --from-literal=api-key=your_linear_api_key \
     --namespace linear-mcp
   ```

3. **Create a ConfigMap for Configuration**

   Create a file named `configmap.yaml`:

   ```yaml
   apiVersion: v1
   kind: ConfigMap
   metadata:
     name: linear-mcp-config
     namespace: linear-mcp
   data:
     config.yaml: |
       server:
         port: 8080
         max_connections: 100
       linear:
         auth:
           method: "api_key"
         rate_limit:
           max_retries: 3
           retry_delay: 1000
       logging:
         level: "info"
   ```

   Apply the ConfigMap:

   ```bash
   kubectl apply -f configmap.yaml
   ```

4. **Create a Deployment**

   Create a file named `deployment.yaml`:

   ```yaml
   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: linear-mcp-server
     namespace: linear-mcp
     labels:
       app: linear-mcp-server
   spec:
     replicas: 2
     selector:
       matchLabels:
         app: linear-mcp-server
     template:
       metadata:
         labels:
           app: linear-mcp-server
       spec:
         containers:
         - name: linear-mcp-server
           image: linearapp/mcp-server:latest
           ports:
           - containerPort: 8080
           env:
           - name: LINEAR_API_KEY
             valueFrom:
               secretKeyRef:
                 name: linear-api-key
                 key: api-key
           - name: LINEAR_MCP_SERVER_PORT
             value: "8080"
           - name: LINEAR_MCP_LOG_LEVEL
             value: "info"
           volumeMounts:
           - name: config-volume
             mountPath: /app/config
           resources:
             requests:
               memory: "256Mi"
               cpu: "100m"
             limits:
               memory: "512Mi"
               cpu: "500m"
           livenessProbe:
             httpGet:
               path: /health
               port: 8080
             initialDelaySeconds: 30
             periodSeconds: 10
           readinessProbe:
             httpGet:
               path: /health
               port: 8080
             initialDelaySeconds: 5
             periodSeconds: 5
         volumes:
         - name: config-volume
           configMap:
             name: linear-mcp-config
   ```

   Apply the Deployment:

   ```bash
   kubectl apply -f deployment.yaml
   ```

5. **Create a Service**

   Create a file named `service.yaml`:

   ```yaml
   apiVersion: v1
   kind: Service
   metadata:
     name: linear-mcp-server
     namespace: linear-mcp
   spec:
     selector:
       app: linear-mcp-server
     ports:
     - port: 80
       targetPort: 8080
     type: ClusterIP
   ```

   Apply the Service:

   ```bash
   kubectl apply -f service.yaml
   ```

6. **Create an Ingress (Optional)**

   If you want to expose the server externally, create an Ingress:

   ```yaml
   apiVersion: networking.k8s.io/v1
   kind: Ingress
   metadata:
     name: linear-mcp-server
     namespace: linear-mcp
     annotations:
       kubernetes.io/ingress.class: nginx
       cert-manager.io/cluster-issuer: letsencrypt-prod
   spec:
     tls:
     - hosts:
       - mcp.yourdomain.com
       secretName: linear-mcp-tls
     rules:
     - host: mcp.yourdomain.com
       http:
         paths:
         - path: /
           pathType: Prefix
           backend:
             service:
               name: linear-mcp-server
               port:
                 number: 80
   ```

   Apply the Ingress:

   ```bash
   kubectl apply -f ingress.yaml
   ```

7. **Verify Deployment**

   ```bash
   # Check deployment status
   kubectl get deployments -n linear-mcp

   # Check pods
   kubectl get pods -n linear-mcp

   # Check logs
   kubectl logs -n linear-mcp deployment/linear-mcp-server
   ```

### Manual Deployment

For development or testing environments, you can deploy the server manually.

#### Prerequisites

- Python 3.8 or later
- pip (Python package manager)
- Linear API key
- Git (optional)

#### Deployment Steps

1. **Clone the Repository (or Download the Source Code)**

   ```bash
   git clone https://github.com/linearapp/mcp-server.git
   cd mcp-server
   ```

2. **Create a Virtual Environment**

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Create a Configuration File**

   Create a file named `config/config.yaml`:

   ```yaml
   server:
     port: 8080
     max_connections: 100

   linear:
     auth:
       method: "api_key"
       api_key: "your_linear_api_key"  # Replace with your actual API key

   logging:
     level: "info"
     file: "logs/server.log"
   ```

5. **Create Log Directory**

   ```bash
   mkdir -p logs
   ```

6. **Start the Server**

   ```bash
   python src/main.py --config config/config.yaml
   ```

7. **Verify Deployment**

   ```bash
   # Test server health
   curl http://localhost:8080/health
   ```

#### Running as a Service

To run the server as a system service on Linux, create a systemd service file:

1. **Create a Service File**

   ```bash
   sudo nano /etc/systemd/system/linear-mcp.service
   ```

   Add the following content:

   ```
   [Unit]
   Description=Linear MCP Server
   After=network.target

   [Service]
   User=ubuntu
   WorkingDirectory=/path/to/mcp-server
   ExecStart=/path/to/mcp-server/venv/bin/python src/main.py --config config/config.yaml
   Restart=on-failure
   Environment=LINEAR_API_KEY=your_linear_api_key

   [Install]
   WantedBy=multi-user.target
   ```

2. **Enable and Start the Service**

   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable linear-mcp
   sudo systemctl start linear-mcp
   ```

3. **Check Service Status**

   ```bash
   sudo systemctl status linear-mcp
   ```

## Security Considerations

### Network Security

1. **Use TLS/SSL**

   For production deployments, always enable TLS/SSL:

   ```yaml
   security:
     ssl:
       enabled: true
       cert_file: "/path/to/cert.pem"
       key_file: "/path/to/key.pem"
   ```

   With Docker, mount the certificate files:

   ```yaml
   volumes:
     - ./certs:/app/certs
   ```

2. **Firewall Configuration**

   Restrict access to the server port:

   ```bash
   # Allow only specific IPs
   sudo ufw allow from 192.168.1.0/24 to any port 8080
   ```

3. **Reverse Proxy**

   Consider using a reverse proxy like Nginx:

   ```nginx
   server {
       listen 443 ssl;
       server_name mcp.yourdomain.com;

       ssl_certificate /path/to/cert.pem;
       ssl_certificate_key /path/to/key.pem;

       location / {
           proxy_pass http://localhost:8080;
           proxy_http_version 1.1;
           proxy_set_header Upgrade $http_upgrade;
           proxy_set_header Connection "upgrade";
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```

### API Key Security

1. **Use Environment Variables**

   Prefer environment variables over configuration files:

   ```bash
   export LINEAR_API_KEY=your_linear_api_key
   ```

2. **Restrict API Key Permissions**

   In Linear, create an API key with only the necessary permissions.

3. **Regular Key Rotation**

   Rotate your API keys regularly:

   ```bash
   # Update the key in your deployment
   kubectl create secret generic linear-api-key \
     --from-literal=api-key=your_new_linear_api_key \
     --namespace linear-mcp \
     --dry-run=client -o yaml | kubectl apply -f -

   # Restart the deployment
   kubectl rollout restart deployment/linear-mcp-server -n linear-mcp
   ```

### Server Authentication

For public deployments, enable server authentication:

```yaml
security:
  api_key: "your_mcp_server_api_key"
```

Provide this key to MCP clients when connecting.

## Monitoring and Maintenance

### Logging

Configure comprehensive logging for troubleshooting:

```yaml
logging:
  level: "info"  # Use "debug" for more detailed logs
  file: "/app/logs/server.log"
  max_size: 10  # MB
  backup_count: 5
  log_requests: true
  log_api_calls: true
```

### Health Checks

The server provides a health endpoint at `/health` that returns:

```json
{
  "status": "ok",
  "version": "1.0.0",
  "uptime": 3600,
  "linear_api_status": "connected"
}
```

Use this endpoint for monitoring:

```bash
# Check server health
curl http://localhost:8080/health
```

### Metrics (Optional)

For advanced monitoring, the server can expose Prometheus metrics at `/metrics`.

Enable metrics in the configuration:

```yaml
monitoring:
  metrics:
    enabled: true
    endpoint: "/metrics"
```

### Backup and Restore

The server is stateless, so backups primarily concern configuration:

1. **Backup Configuration**

   ```bash
   # Docker deployment
   cp -r config config.bak

   # Kubernetes deployment
   kubectl get configmap linear-mcp-config -n linear-mcp -o yaml > config-backup.yaml
   ```

2. **Backup Secrets**

   ```bash
   # Kubernetes deployment
   kubectl get secret linear-api-key -n linear-mcp -o yaml > secret-backup.yaml
   ```

### Scaling

For high-traffic environments, scale the server:

```bash
# Kubernetes scaling
kubectl scale deployment/linear-mcp-server --replicas=5 -n linear-mcp
```

With Docker Compose, use the `--scale` option:

```bash
docker-compose up -d --scale linear-mcp-server=3
```

Note: When scaling, ensure proper load balancing and session affinity if needed.

## Troubleshooting

### Common Issues

1. **Connection Refused**

   ```
   Error: Connection refused
   ```

   **Solution:**
   - Verify the server is running
   - Check the port configuration
   - Ensure firewall rules allow access

2. **Authentication Failed**

   ```
   Error: Authentication failed with Linear API
   ```

   **Solution:**
   - Verify your Linear API key
   - Check if the key has the necessary permissions
   - Ensure the key hasn't expired

3. **WebSocket Connection Failed**

   ```
   Error: WebSocket connection failed
   ```

   **Solution:**
   - Check if the server supports WebSocket
   - Verify proxy configurations
   - Ensure the correct protocol (ws:// or wss://)

### Diagnostic Commands

```bash
# Check server logs
docker logs linear-mcp-server

# Check server status
docker ps | grep linear-mcp-server

# Test WebSocket connection
wscat -c ws://localhost:8080
```

### Getting Support

If you encounter issues:

1. Check the server logs for detailed error messages
2. Verify your configuration against the documentation
3. Search for similar issues in the GitHub repository
4. Contact support with detailed information about your issue

## Advanced Deployment Scenarios

### High Availability Setup

For mission-critical deployments, implement a high availability setup:

1. **Multiple Replicas**

   Deploy multiple server instances behind a load balancer.

2. **Geographic Distribution**

   Deploy instances in multiple regions for global availability.

3. **Automatic Failover**

   Configure health checks and automatic failover.

### Custom Authentication Integration

To integrate with your organization's authentication system:

1. **Implement Custom Authenticator**

   Create a custom authenticator class that integrates with your auth system.

2. **Configure the Server**

   ```yaml
   security:
     auth:
       type: "custom"
       module: "my_auth_module"
       class: "MyAuthenticator"
   ```

3. **Deploy Custom Module**

   Include your custom authentication module in the deployment.

## Conclusion

This document provides comprehensive instructions for deploying the Linear MCP Server in various environments. By following these guidelines, you can ensure a secure, reliable, and maintainable deployment that meets your organization's needs.

For additional information, refer to:

- [Server Configuration](server_configuration.md)
- [Server Usage Documentation](server_usage_documentation.md)
- [Implementation Blueprint](implementation_blueprint.md)

Remember to regularly update your deployment to benefit from the latest features and security improvements.
