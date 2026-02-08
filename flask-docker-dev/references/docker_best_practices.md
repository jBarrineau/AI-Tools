# Docker & Flask Best Practices

## Multi-Stage Builds

Multi-stage builds optimize image size and security by separating build artifacts from the final runtime image.

### Structure

```dockerfile
# Base stage: common setup
FROM python:3.11-slim as base
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
WORKDIR /app

# Development stage
FROM base as development
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["flask", "run", "--host=0.0.0.0"]

# Production stage
FROM base as production
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "wsgi:app"]
```

### Benefits

- **Smaller images**: Production image excludes development tools
- **Security**: Reduced attack surface with minimal dependencies
- **Consistency**: Both stages use same base configuration
- **Build caching**: Separate targets can be cached independently

## Security Hardening

### Non-Root User

Always run containers as a non-root user to limit damage from container escapes.

```dockerfile
RUN groupadd -r appuser && useradd -r -g appuser appuser
# ... (copy files)
RUN chown -R appuser:appuser /app
USER appuser
```

### Capability Dropping

Drop unnecessary Linux capabilities to reduce the attack surface.

```dockerfile
# Drop all capabilities and add only what's needed
RUN setcap -r /usr/sbin/setcap || true
# Flask doesn't need special capabilities
```

### Read-Only Filesystem

Use read-only root filesystem with a writable temp directory for logs.

In `docker-compose.yml`:
```yaml
services:
  web:
    read_only: true
    tmpfs:
      - /tmp
      - /run
    volumes:
      - ./logs:/app/logs
```

In production Kubernetes, use:
```yaml
securityContext:
  readOnlyRootFilesystem: true
```

### No New Privileges

Prevent child processes from gaining additional privileges.

```dockerfile
# In production Kubernetes securityContext
securityContext:
  allowPrivilegeEscalation: false
```

## Image Optimization

### Use Slim Base Images

```dockerfile
# Good: ~160MB
FROM python:3.11-slim

# Avoid: ~900MB
FROM python:3.11
```

### Cache Pip Dependencies

Order Dockerfile commands to maximize cache efficiency.

```dockerfile
# Copy requirements first (rarely changes)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code (changes frequently)
COPY . .
```

### Remove Package Manager Cache

```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*
```

### Use .dockerignore

```
__pycache__
*.pyc
*.pyo
.pytest_cache
.git
.gitignore
.env
.vscode
README.md
tests/
```

## Production Server: Gunicorn

Use Gunicorn instead of Flask's development server for production.

### Configuration

```dockerfile
CMD ["gunicorn", \
     "--bind", "0.0.0.0:5000", \
     "--workers", "4", \
     "--worker-class", "sync", \
     "--timeout", "60", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "wsgi:app"]
```

### Worker Calculation

Number of workers = (2 × CPU cores) + 1

For a 2-core container: 5 workers

```dockerfile
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "5", "wsgi:app"]
```

## Resource Limits

Prevent containers from consuming excessive resources.

### Docker Compose

```yaml
services:
  web:
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
        reservations:
          cpus: '0.25'
          memory: 256M
```

### Kubernetes

```yaml
resources:
  limits:
    cpu: 500m
    memory: 512Mi
  requests:
    cpu: 250m
    memory: 256Mi
```

## Health Checks

Health checks allow orchestrators to detect and restart unhealthy containers.

### Dockerfile

```dockerfile
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python healthcheck.py
```

### Health Check Script

```python
#!/usr/bin/env python
import sys
import requests

try:
    response = requests.get("http://localhost:5000/", timeout=3)
    if response.status_code == 200:
        sys.exit(0)
except Exception:
    pass

sys.exit(1)
```

### docker-compose.yml

```yaml
services:
  web:
    healthcheck:
      test: ["CMD", "python", "healthcheck.py"]
      interval: 30s
      timeout: 3s
      retries: 3
      start_period: 5s
```

## Environment Variables

Store configuration in environment variables, never in code.

### .env File (Development Only)

```
FLASK_ENV=development
FLASK_APP=wsgi.py
SECRET_KEY=dev-key-change-in-production
DATABASE_URL=sqlite:///app.db
```

### Docker Compose

```yaml
services:
  web:
    environment:
      - FLASK_ENV=production
      - SECRET_KEY=${SECRET_KEY}  # From host environment
    env_file:
      - .env.production
```

### Secrets Management

Never commit `.env` files with secrets. Use secrets management:

**Docker Compose** (development):
```yaml
services:
  web:
    environment:
      - SECRET_KEY=${SECRET_KEY}
```

**Docker Swarm** or **Kubernetes** (production):
```yaml
# Store secrets separately
kubectl create secret generic app-secret --from-literal=SECRET_KEY=xxx
```

## Logging

Configure logging to go to stdout/stderr for container orchestrators.

### Gunicorn Access Logs

```dockerfile
CMD ["gunicorn", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "wsgi:app"]
```

### Flask Application Logging

```python
import logging
import sys

def create_app(config_name: str = "development"):
    app = Flask(__name__)

    # Configure logging to stdout
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    app.logger.addHandler(handler)

    return app
```

## Docker Compose for Development

### Full Example

```yaml
version: '3.8'

services:
  web:
    build:
      context: .
      dockerfile: Dockerfile
      target: development
    container_name: myapp_dev
    ports:
      - "127.0.0.1:5000:5000"
    volumes:
      - .:/app
      - /app/__pycache__
    environment:
      - FLASK_ENV=development
      - FLASK_APP=wsgi.py
    env_file:
      - .env
    networks:
      - app-network
    healthcheck:
      test: ["CMD", "python", "healthcheck.py"]
      interval: 30s
      timeout: 3s
      retries: 3
      start_period: 5s

networks:
  app-network:
    driver: bridge
```

### Key Features

- **localhost binding**: `127.0.0.1:5000:5000` prevents external access
- **Volume mounts**: Live code reloading with `volumes: [., /app/__pycache__]`
- **env_file**: Load environment variables from file
- **networks**: Isolate services within the compose stack
- **healthcheck**: Automatic restart on unhealthy status

## Building and Running

### Development

```bash
# Build and start
docker-compose up --build

# Run in background
docker-compose up -d

# View logs
docker-compose logs -f web

# Stop
docker-compose down
```

### Production (Build Only)

```bash
# Build production image
docker build --target production -t myapp:1.0.0 .

# Push to registry
docker push myapp:1.0.0

# Run with orchestrator (Kubernetes, Docker Swarm, etc.)
```

## Debugging in Docker

### Interactive Shell

```bash
docker-compose exec web bash
```

### Python Debugger

```python
# In your Flask route
import pdb
pdb.set_trace()  # Will pause at this line
```

Then attach:
```bash
docker-compose exec web python -i wsgi.py
```

### Print Debugging

View container logs in real-time:
```bash
docker-compose logs -f web
```

### Inspect Running Container

```bash
# View environment
docker-compose exec web env

# Check process list
docker-compose exec web ps aux

# Check network
docker-compose exec web ifconfig
```

## Common Issues

### Port Already in Use

If port 5000 is already in use:

```yaml
services:
  web:
    ports:
      - "127.0.0.1:8000:5000"  # Map 8000 -> 5000
```

### Permission Denied on Volumes

The container runs as `appuser` (non-root). If you can't write to volumes:

```bash
# Make directory writable by your user
chmod 777 ./logs
```

### Module Not Found in Container

Rebuild the image after adding new dependencies:

```bash
docker-compose up --build
```

### Slow Performance on Windows/Mac

Docker on Windows/Mac uses a VM. Performance is degraded with volume mounts. Consider:
- Using named volumes for better performance
- Keeping code inside the container for CI/CD
- Using WSL2 on Windows for better performance

```yaml
volumes:
  app-code:

services:
  web:
    volumes:
      - app-code:/app
```
