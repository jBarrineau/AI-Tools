#!/usr/bin/env python3
"""
Flask project scaffold generator.
Creates a modern Flask project with proper structure, factory pattern, and Docker setup.

Usage: python scaffold_project.py <project_name> [--path .] [--with-database] [--with-auth]
"""

import argparse
import os
import sys
from pathlib import Path


def create_project_structure(project_root: Path, project_name: str, with_database: bool, with_auth: bool):
    """Create the Flask project directory structure."""

    # Create directories
    dirs = [
        project_root / "app",
        project_root / "app" / "templates",
        project_root / "app" / "static" / "css",
        project_root / "app" / "static" / "js",
        project_root / "tests",
    ]

    if with_database:
        dirs.extend([
            project_root / "migrations",
            project_root / "app" / "models",
        ])

    if with_auth:
        dirs.extend([
            project_root / "app" / "auth",
        ])

    for dir_path in dirs:
        dir_path.mkdir(parents=True, exist_ok=True)

    # Create __init__.py files
    (project_root / "app" / "__init__.py").write_text(_create_app_init(with_database, with_auth))
    (project_root / "tests" / "__init__.py").write_text("")

    if with_database:
        (project_root / "app" / "models" / "__init__.py").write_text("")
        (project_root / "app" / "models" / "user.py").write_text(_create_user_model())

    if with_auth:
        (project_root / "app" / "auth" / "__init__.py").write_text("")
        (project_root / "app" / "auth" / "routes.py").write_text(_create_auth_routes())

    # Create main files
    (project_root / "app" / "main.py").write_text(_create_main_blueprint())
    (project_root / "config.py").write_text(_create_config())
    (project_root / "wsgi.py").write_text(_create_wsgi())
    (project_root / "requirements.txt").write_text(_create_requirements(with_database, with_auth))
    (project_root / ".env.example").write_text(_create_env_example())
    (project_root / ".dockerignore").write_text(_create_dockerignore())
    (project_root / "Dockerfile").write_text(_create_dockerfile())
    (project_root / "docker-compose.yml").write_text(_create_docker_compose(project_name))
    (project_root / "healthcheck.py").write_text(_create_healthcheck())
    (project_root / "app" / "templates" / "base.html").write_text(_create_base_template(project_name))
    (project_root / "app" / "templates" / "index.html").write_text(_create_index_template())
    (project_root / "tests" / "test_main.py").write_text(_create_test_main())
    (project_root / ".gitignore").write_text(_create_gitignore())
    (project_root / "README.md").write_text(_create_readme(project_name, with_database, with_auth))


def _create_app_init(with_database: bool, with_auth: bool) -> str:
    imports = "from flask import Flask"
    config = """
from config import config_by_name

def create_app(config_name: str = "development") -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name])
"""

    if with_database:
        imports += "\nfrom flask_sqlalchemy import SQLAlchemy\n"
        config += "\n    from app.models import db\n    db.init_app(app)"

    if with_auth:
        imports += "\nfrom flask_login import LoginManager\n"
        config += "\n    from flask_login import LoginManager\n    login_manager = LoginManager()\n    login_manager.init_app(app)"

    config += """

    # Register blueprints
    from app.main import bp as main_bp
    app.register_blueprint(main_bp)
"""

    if with_auth:
        config += "    from app.auth import bp as auth_bp\n    app.register_blueprint(auth_bp)\n"

    config += """
    return app
"""

    return imports + config


def _create_user_model() -> str:
    return """from app import db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)
"""


def _create_auth_routes() -> str:
    return """from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required

bp = Blueprint("auth", __name__, url_prefix="/auth")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        # TODO: Implement login logic
        flash("Login functionality coming soon")
    return render_template("auth/login.html")


@bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("main.index"))
"""


def _create_main_blueprint() -> str:
    return """from flask import Blueprint, render_template

bp = Blueprint("main", __name__)


@bp.route("/")
def index():
    return render_template("index.html", title="Home")
"""


def _create_config() -> str:
    return """import os
from datetime import timedelta


class Config:
    \"\"\"Base configuration.\"\"\"
    SECRET_KEY = os.environ.get("SECRET_KEY") or "dev-key-change-in-production"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Session
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"


class DevelopmentConfig(Config):
    \"\"\"Development configuration.\"\"\"
    DEBUG = True
    TESTING = False
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL") or "sqlite:///dev.db"
    SESSION_COOKIE_SECURE = False  # Allow HTTP in development


class ProductionConfig(Config):
    \"\"\"Production configuration.\"\"\"
    DEBUG = False
    TESTING = False
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")
    if not SQLALCHEMY_DATABASE_URI:
        raise ValueError("DATABASE_URL environment variable must be set in production")


class TestingConfig(Config):
    \"\"\"Testing configuration.\"\"\"
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False


config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}
"""


def _create_wsgi() -> str:
    return """import os
from app import create_app

config_name = os.environ.get("FLASK_ENV", "production")
app = create_app(config_name)

if __name__ == "__main__":
    app.run()
"""


def _create_requirements(with_database: bool, with_auth: bool) -> str:
    reqs = [
        "Flask==3.0.0",
        "gunicorn==21.2.0",
        "python-dotenv==1.0.0",
    ]

    if with_database:
        reqs.extend([
            "Flask-SQLAlchemy==3.1.1",
            "alembic==1.13.0",
        ])

    if with_auth:
        reqs.extend([
            "Flask-Login==0.6.3",
            "WTForms==3.1.1",
            "email-validator==2.1.0",
        ])

    return "\n".join(reqs) + "\n"


def _create_env_example() -> str:
    return """FLASK_ENV=development
FLASK_APP=wsgi.py
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///app.db
"""


def _create_dockerfile() -> str:
    return """# Multi-stage build for production
FROM python:3.11-slim as base

# Security: create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \\
    curl \\
    && rm -rf /var/lib/apt/lists/*

# Development stage
FROM base as development
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
USER appuser
EXPOSE 5000
CMD ["flask", "run", "--host=0.0.0.0"]

# Production stage
FROM base as production
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN chown -R appuser:appuser /app
USER appuser

# Security: drop unnecessary capabilities
RUN setcap -r /usr/sbin/setcap || true

EXPOSE 5000
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \\
    CMD python healthcheck.py

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--timeout", "60", "--access-logfile", "-", "wsgi:app"]
"""


def _create_docker_compose(project_name: str) -> str:
    return f"""version: '3.8'

services:
  web:
    build:
      context: .
      dockerfile: Dockerfile
      target: development
    container_name: {project_name}_dev
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
"""


def _create_healthcheck() -> str:
    return """#!/usr/bin/env python
\"\"\"Health check for Flask application.\"\"\"

import sys
import requests

try:
    response = requests.get("http://localhost:5000/", timeout=3)
    if response.status_code == 200:
        sys.exit(0)
except Exception:
    pass

sys.exit(1)
"""


def _create_base_template(project_name: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{% block title %}} - {project_name}{{% endblock %}}</title>
</head>
<body>
    <header>
        <h1>{project_name}</h1>
    </header>

    <main>
        {{% block content %}}{{% endblock %}}
    </main>

    <footer>
        <p>&copy; 2024 {project_name}</p>
    </footer>
</body>
</html>
"""


def _create_index_template() -> str:
    return """{% extends "base.html" %}

{% block title %}Home{% endblock %}

{% block content %}
<h2>Welcome</h2>
<p>Your Flask app is running!</p>
{% endblock %}
"""


def _create_test_main() -> str:
    return """def test_index(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Welcome" in response.data
"""


def _create_gitignore() -> str:
    return """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# IDE
.vscode/
.idea/
*.swp
*.swo

# Testing
.pytest_cache/
.coverage
htmlcov/

# Environment
.env
.env.local

# Database
*.db
*.sqlite

# Docker
.dockerignore
"""


def _create_dockerignore() -> str:
    return """__pycache__
*.pyc
*.pyo
.pytest_cache
.coverage
htmlcov
.git
.gitignore
.env
.env.local
.vscode
.idea
*.swp
*.swo
README.md
tests/
migrations/
"""


def _create_readme(project_name: str, with_database: bool, with_auth: bool) -> str:
    setup_steps = """
## Development Setup

1. Clone and enter the project:
   ```
   cd {project_name}
   ```

2. Create and activate virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\\Scripts\\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Set up environment:
   ```
   cp .env.example .env
   ```
"""

    if with_database:
        setup_steps += """
5. Initialize database:
   ```
   flask db init
   flask db migrate -m "Initial migration"
   flask db upgrade
   ```
"""

    setup_steps += """
6. Run development server:
   ```
   flask run
   ```

   Or with Docker:
   ```
   docker-compose up
   ```

The app will be available at http://localhost:5000
"""

    return f"""# {project_name}

A modern Flask application with Docker support.

## Features

- Application factory pattern
- Blueprints for modular routing
- Environment-based configuration
- Docker & docker-compose setup
- Production-ready with gunicorn
- Security best practices
"""  + ("""- SQLAlchemy ORM with migrations
- Database support
""" if with_database else "") + ("""- User authentication
- Flask-Login integration
""" if with_auth else "") + setup_steps


def main():
    parser = argparse.ArgumentParser(description="Flask project scaffold generator")
    parser.add_argument("project_name", help="Name of the project")
    parser.add_argument("--path", default=".", help="Path where to create the project (default: current directory)")
    parser.add_argument("--with-database", action="store_true", help="Include SQLAlchemy and database setup")
    parser.add_argument("--with-auth", action="store_true", help="Include Flask-Login and authentication")

    args = parser.parse_args()

    project_root = Path(args.path) / args.project_name

    if project_root.exists():
        print(f"Error: Directory '{project_root}' already exists", file=sys.stderr)
        sys.exit(1)

    try:
        create_project_structure(project_root, args.project_name, args.with_database, args.with_auth)
        print(f"✅ Project '{args.project_name}' created at {project_root}")
        print(f"\nNext steps:")
        print(f"  cd {project_root}")
        print(f"  python -m venv venv")
        print(f"  source venv/bin/activate")
        print(f"  pip install -r requirements.txt")
        print(f"  flask run")
    except Exception as e:
        print(f"Error creating project: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
