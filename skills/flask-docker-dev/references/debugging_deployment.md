# Debugging and Deployment Guide

## Development: Local Debugging

### Using Flask's Debug Mode

Flask's debug mode provides auto-reload and better error pages.

```python
# config.py
class DevelopmentConfig(Config):
    DEBUG = True
    TESTING = False
```

Then run:
```bash
flask run
```

The app auto-reloads on file changes.

### Python Debugger (pdb)

Add breakpoints in your code:

```python
@bp.route("/debug-example")
def debug_route():
    result = expensive_operation()
    import pdb; pdb.set_trace()  # Execution pauses here
    return result
```

Run Flask:
```bash
flask run
```

The debugger will pause at the breakpoint in your terminal.

### Better: ipdb

Install and use ipdb for better debugging:

```bash
pip install ipdb
```

```python
@bp.route("/debug-example")
def debug_route():
    import ipdb; ipdb.set_trace()
    return result
```

### Docker: Debugging in Containers

#### Option 1: Interactive Bash

```bash
docker-compose exec web bash
```

Then inside the container:
```bash
python -m pdb wsgi.py
```

#### Option 2: Run with Debugger

Modify docker-compose.yml:

```yaml
services:
  web:
    command: flask run --host=0.0.0.0
    # or
    command: python -m pdb wsgi.py
```

#### Option 3: Print Logging

The simplest approach - use logging:

```python
@bp.route("/debug")
def debug():
    app.logger.info("Debug message: variable=%s", variable)
    return "OK"
```

View logs:
```bash
docker-compose logs -f web
```

### Testing Locally Before Docker

Test without Docker first to isolate issues:

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
flask run
```

If it works locally but fails in Docker, the issue is likely:
- **Missing dependencies**: Check requirements.txt
- **Environment variables**: Check .env or docker-compose.yml
- **Database connection**: Check DATABASE_URL
- **Permissions**: Check if appuser can access files

## Debugging in Docker Compose

### View Container Logs

```bash
# Follow logs in real-time
docker-compose logs -f web

# View last 100 lines
docker-compose logs --tail=100 web

# View with timestamps
docker-compose logs -f --timestamps web
```

### Inspect Container State

```bash
# Check if container is running
docker-compose ps

# View container processes
docker-compose exec web ps aux

# Check environment variables
docker-compose exec web env

# Test network connectivity
docker-compose exec web ping web  # Ping by service name
docker-compose exec web curl http://localhost:5000/
```

### Rebuild After Changes

```bash
# Rebuild without cache
docker-compose up --build

# Force complete rebuild
docker-compose down
docker system prune -f
docker-compose up --build
```

### Common Docker Issues

#### "Connection refused"
- Service may not be ready yet
- Check health checks: `docker-compose ps`
- Wait longer before connecting: Add `start_period: 10s` to healthcheck

#### "No such file or directory"
- Volume mount issue
- Check: `docker-compose exec web ls -la /app`
- Verify paths in docker-compose.yml

#### "Permission denied"
- Container runs as `appuser` (non-root)
- Check file permissions: `docker-compose exec web ls -la`
- Make writable: `chmod 777 ./directory`

#### "Out of memory"
- Set resource limits in docker-compose.yml
- Monitor with: `docker stats`

## Testing in Docker

### Run Tests in Container

```bash
docker-compose exec web pytest
```

### Run Specific Test

```bash
docker-compose exec web pytest tests/test_main.py::test_index
```

### With Coverage

```bash
docker-compose exec web pytest --cov=app tests/
```

### Create Test Container

Separate test container for CI/CD:

```dockerfile
FROM base as testing
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt pytest pytest-cov
COPY . .
USER appuser
CMD ["pytest", "tests/"]
```

Build and run:
```bash
docker build --target testing -t myapp:test .
docker run myapp:test
```

## Deployment

### Pre-Deployment Checklist

- [ ] All tests passing: `pytest tests/`
- [ ] No debug mode: `DEBUG = False` in production config
- [ ] SECRET_KEY set: `export SECRET_KEY=<random-string>`
- [ ] DATABASE_URL set: `export DATABASE_URL=postgresql://...`
- [ ] Logging configured to stdout
- [ ] Health checks configured
- [ ] Resource limits set
- [ ] Non-root user configured
- [ ] Security headers enabled (see below)

### Security Headers

Add security headers to Flask app:

```python
def create_app(config_name: str = "development"):
    app = Flask(__name__)

    @app.after_request
    def set_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        return response

    return app
```

### HTTPS/TLS

Always use HTTPS in production. Options:

#### Docker with Nginx Reverse Proxy

```yaml
services:
  web:
    ports:
      - "127.0.0.1:5000:5000"  # Only internal

  nginx:
    image: nginx:alpine
    ports:
      - "0.0.0.0:443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - web
```

#### Kubernetes Ingress

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: app-ingress
spec:
  tls:
    - hosts:
        - example.com
      secretName: app-tls
  rules:
    - host: example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: app
                port:
                  number: 5000
```

### Environment Configuration for Production

```bash
# Set required environment variables
export FLASK_ENV=production
export SECRET_KEY=$(python -c 'import secrets; print(secrets.token_hex(32))')
export DATABASE_URL=postgresql://user:password@db.example.com/appdb
export LOG_LEVEL=INFO
```

### Database Migrations

Run migrations before starting the application:

```dockerfile
# In Dockerfile, use entrypoint script
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "wsgi:app"]
```

```bash
#!/bin/bash
# entrypoint.sh
set -e

echo "Running database migrations..."
flask db upgrade

echo "Starting application..."
exec "$@"
```

### Deployment with Docker Swarm

```bash
# Initialize swarm
docker swarm init

# Create stack from compose file
docker stack deploy -c docker-compose.prod.yml myapp

# Scale service
docker service scale myapp_web=3

# Update service
docker service update --image myapp:v2.0.0 myapp_web

# Monitor
docker service logs myapp_web
```

### Deployment with Kubernetes

#### Minimal Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: app
  template:
    metadata:
      labels:
        app: app
    spec:
      containers:
      - name: app
        image: myapp:1.0.0
        ports:
        - containerPort: 5000
        env:
        - name: FLASK_ENV
          value: production
        - name: SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: secret-key
        resources:
          requests:
            cpu: 250m
            memory: 256Mi
          limits:
            cpu: 500m
            memory: 512Mi
        livenessProbe:
          httpGet:
            path: /
            port: 5000
          initialDelaySeconds: 10
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /
            port: 5000
          initialDelaySeconds: 5
          periodSeconds: 10
        securityContext:
          runAsNonRoot: true
          readOnlyRootFilesystem: true
          allowPrivilegeEscalation: false
          capabilities:
            drop:
              - ALL
        volumeMounts:
        - name: tmp
          mountPath: /tmp
        - name: logs
          mountPath: /app/logs
      volumes:
      - name: tmp
        emptyDir: {}
      - name: logs
        emptyDir: {}
---
apiVersion: v1
kind: Service
metadata:
  name: app
spec:
  type: ClusterIP
  selector:
    app: app
  ports:
  - port: 80
    targetPort: 5000
```

Create secrets before deploying:
```bash
kubectl create secret generic app-secrets \
  --from-literal=secret-key=$(python -c 'import secrets; print(secrets.token_hex(32))')
```

Deploy:
```bash
kubectl apply -f deployment.yaml
```

## Monitoring

### Container Metrics

```bash
# Watch resource usage
docker stats

# One-time metrics
docker stats --no-stream
```

### Logs Aggregation

Forward container logs to a centralized system:

```yaml
services:
  web:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

### Application Performance

Monitor with application-level logging:

```python
import time

@bp.before_request
def log_request_start():
    g.start_time = time.time()

@bp.after_request
def log_request_end(response):
    duration = time.time() - g.start_time
    app.logger.info(f"{request.method} {request.path} - {response.status_code} - {duration:.2f}s")
    return response
```

### Metrics Export

Use Prometheus for metrics:

```bash
pip install prometheus-flask-exporter
```

```python
from prometheus_flask_exporter import PrometheusMetrics

app = Flask(__name__)
metrics = PrometheusMetrics(app)
```

Metrics available at `/metrics`
