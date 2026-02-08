---
name: flask-docker-dev
description: "Comprehensive guide for developing modern Flask applications in Docker containers with security best practices. Use when you need to: (1) Create new Flask projects with proper app factory and blueprint patterns, (2) Set up Docker environments for development and production, (3) Configure containerized Flask apps with security hardening (non-root user, read-only filesystem, capability dropping), (4) Debug Flask apps running in containers, (5) Deploy Flask apps with comprehensive security and resource management. Covers Flask patterns, Docker multi-stage builds, container security, debugging techniques, and production deployment strategies."
---

# Flask Docker Development

Develop modern Flask applications with complete Docker support, security hardening, and best practices for development, testing, and production deployment.

## Quick Start

### Create a New Project

```bash
python scripts/scaffold_project.py myproject --with-database --with-auth
cd myproject
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Run Locally

```bash
# With Flask development server
flask run

# With Docker Compose (hot reload)
docker-compose up
```

The app will be available at `http://localhost:5000`

### Deploy to Production

```bash
# Build production image
docker build --target production -t myapp:1.0.0 .

# Push to registry
docker push myapp:1.0.0

# Deploy with orchestrator (Docker Swarm, Kubernetes, etc.)
```

## Core Workflows

### 1. Scaffold a New Flask Project

Use the `scaffold_project.py` script to generate a modern Flask project with proper structure:

```bash
python scripts/scaffold_project.py <project_name> [--path .] [--with-database] [--with-auth]
```

**Examples:**
- Basic project: `python scripts/scaffold_project.py blog`
- With database: `python scripts/scaffold_project.py blog --with-database`
- Full stack: `python scripts/scaffold_project.py blog --with-database --with-auth`

**What you get:**
- App factory pattern for flexible configuration
- Blueprint-based routing system
- Environment-based configuration (development/testing/production)
- docker-compose.yml for local development
- Multi-stage Dockerfile for production
- Health check support
- Modern project structure with tests

### 2. Develop Locally with Docker

The generated `docker-compose.yml` provides:
- **Hot reload**: Code changes visible immediately
- **Volume mounting**: Edit files on your host, changes reflect in container
- **Environment isolation**: Separate environment from your machine
- **Port binding to localhost**: Security - app only accessible locally

```bash
# Start development environment
docker-compose up

# In another terminal, interact with the container
docker-compose exec web bash        # Get shell access
docker-compose exec web flask shell # Interactive Flask shell
docker-compose exec web pytest      # Run tests
```

### 3. Debug Issues

**Local debugging (before Docker):**

Test without containers first to isolate issues:

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
flask run
```

**Docker debugging:**

View logs:
```bash
docker-compose logs -f web
```

Interactive bash:
```bash
docker-compose exec web bash
```

Python debugger in code:
```python
import pdb; pdb.set_trace()
```

See `references/debugging_deployment.md` for detailed debugging strategies.

### 4. Add Features with Flask Patterns

The generated project uses modern Flask patterns. Understand them to extend your app:

**Blueprints** - Organize code into modules:
```python
# app/api/routes.py
bp = Blueprint("api", __name__, url_prefix="/api")

@bp.route("/users")
def get_users():
    return {"users": []}
```

**Database models** - Define your data structure:
```python
# app/models/user.py
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True)
```

**Configuration** - Manage environment-specific settings:
```python
# config.py
class DevelopmentConfig:
    DEBUG = True
    DATABASE_URL = "sqlite:///dev.db"
```

See `references/flask_patterns.md` for comprehensive pattern reference.

### 5. Deploy to Production

**Build production image:**
```bash
docker build --target production -t myapp:1.0.0 .
```

**Key production features included:**
- Non-root user: Container runs as `appuser`
- Read-only filesystem: Better security
- Resource limits: Prevent runaway consumption
- Health checks: Automatic restart on failure
- Gunicorn: Production-grade WSGI server
- Security headers: Protection against XSS, clickjacking, etc.

**Set required environment variables:**
```bash
export FLASK_ENV=production
export SECRET_KEY=$(python -c 'import secrets; print(secrets.token_hex(32))')
export DATABASE_URL=postgresql://user:pass@host/db
```

**Deploy with Kubernetes:**
```bash
# Create secrets
kubectl create secret generic app-secrets --from-literal=SECRET_KEY=xxx

# Deploy
kubectl apply -f deployment.yaml
```

See `references/debugging_deployment.md` for detailed deployment strategies.

## Security Checklist

The generated Dockerfile and docker-compose.yml include:

- ✅ **Non-root user**: App runs as `appuser`, not root
- ✅ **Minimal base image**: `python:3.11-slim` (~160MB)
- ✅ **Multi-stage builds**: Production image excludes dev tools
- ✅ **Health checks**: Automated failure detection
- ✅ **Resource limits**: CPU and memory constraints
- ✅ **Read-only filesystem**: (add to production deployment)
- ✅ **Localhost binding**: Ports only accessible internally
- ✅ **Environment isolation**: Secrets in env vars, not code

See `references/docker_best_practices.md` for comprehensive security guidelines.

## Reference Documentation

### Flask Patterns (`references/flask_patterns.md`)

- Application factory pattern
- Blueprint-based routing
- Configuration management
- SQLAlchemy database models
- Flask-Login authentication
- Error handling and logging
- Testing patterns

### Docker Best Practices (`references/docker_best_practices.md`)

- Multi-stage builds
- Security hardening (non-root, capabilities, read-only FS)
- Image optimization
- Gunicorn configuration
- Resource limits
- Health checks
- Environment management
- docker-compose setup

### Debugging & Deployment (`references/debugging_deployment.md`)

- Local debugging (pdb, ipdb, logging)
- Docker debugging (logs, bash, interactive)
- Testing in containers
- Production deployment checklist
- Security headers
- HTTPS/TLS setup
- Docker Swarm deployment
- Kubernetes deployment
- Monitoring and metrics

## Common Tasks

### Add a New Route

```python
# app/api/routes.py
from flask import Blueprint, jsonify

bp = Blueprint("api", __name__, url_prefix="/api")

@bp.route("/status")
def status():
    return jsonify({"status": "ok"})
```

Register in `app/__init__.py`:
```python
from app.api import bp as api_bp
app.register_blueprint(api_bp)
```

### Add Database Model

```python
# app/models/post.py
class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
```

Create migration:
```bash
flask db migrate -m "Add Post model"
flask db upgrade
```

### Protect Route with Authentication

```python
from flask_login import login_required, current_user

@bp.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html", user=current_user)
```

### Run Tests

```bash
# Local
pytest tests/

# Docker
docker-compose exec web pytest

# With coverage
docker-compose exec web pytest --cov=app tests/
```

### Debug in Container

Add breakpoint to your code:
```python
import pdb; pdb.set_trace()
```

Run and attach:
```bash
docker-compose up
# In another terminal
docker-compose exec web python -i wsgi.py
```

## Project Structure

```
myproject/
├── app/
│   ├── __init__.py           # App factory
│   ├── main.py               # Main blueprint
│   ├── models/               # Database models
│   ├── auth/                 # Auth blueprint (if --with-auth)
│   ├── static/               # CSS, JS, images
│   └── templates/            # HTML templates
├── migrations/               # Database migrations (if --with-database)
├── tests/                    # Test files
├── config.py                 # Configuration classes
├── wsgi.py                   # WSGI entry point
├── healthcheck.py            # Health check script
├── Dockerfile                # Multi-stage Docker build
├── docker-compose.yml        # Local development setup
├── requirements.txt          # Python dependencies
├── .env.example              # Environment variables template
├── .dockerignore              # Docker build exclusions
├── .gitignore                # Git exclusions
└── README.md                 # Project README
```

## Troubleshooting

### "Address already in use"
Change the port in docker-compose.yml:
```yaml
ports:
  - "127.0.0.1:8000:5000"  # Map 8000 -> 5000
```

### "Module not found in container"
Rebuild after adding dependencies:
```bash
docker-compose up --build
```

### "Permission denied on volume"
Container runs as non-root user. Make directory writable:
```bash
chmod 777 ./directory
```

### Container exits immediately
Check logs:
```bash
docker-compose logs web
```

Common causes:
- Missing environment variables
- Database connection failed
- Import errors in Flask app

### Slow on Windows/Mac
Volume performance is degraded in Docker Desktop. Options:
- Use WSL2 on Windows (much faster)
- Use named volumes for better performance
- Accept slower performance for dev-only local testing

## Next Steps

1. **Create a project**: `python scripts/scaffold_project.py myapp --with-database --with-auth`
2. **Read Flask patterns**: See `references/flask_patterns.md` to understand the structure
3. **Read Docker best practices**: See `references/docker_best_practices.md` for security and optimization
4. **Start developing**: Edit code, run `flask run` or `docker-compose up`, and iterate
5. **Before deploying**: See `references/debugging_deployment.md` for deployment checklist
