# Flask Patterns Guide

## Application Factory Pattern

The application factory pattern defers creation of the Flask application until needed. This allows for multiple app configurations and easier testing.

### Structure

```python
# app/__init__.py
from flask import Flask
from config import config_by_name

def create_app(config_name: str = "development") -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name])

    # Initialize extensions
    from app.models import db
    db.init_app(app)

    # Register blueprints
    from app.main import bp as main_bp
    app.register_blueprint(main_bp)

    return app
```

### Benefits

- **Multiple configurations**: Switch between development, testing, production easily
- **Testing**: Create separate app instances for tests without affecting development environment
- **Lazy loading**: Extensions initialize only when the app instance exists
- **Circular imports**: Avoid circular dependency issues by deferring imports

## Blueprints for Modular Routing

Blueprints allow you to organize code into logical modules that can be registered with the main app.

### Structure

```python
# app/main/routes.py
from flask import Blueprint, render_template

bp = Blueprint("main", __name__)

@bp.route("/")
def index():
    return render_template("index.html")

@bp.route("/about")
def about():
    return render_template("about.html")
```

```python
# app/auth/routes.py
from flask import Blueprint, redirect, url_for
from flask_login import login_required, logout_user

bp = Blueprint("auth", __name__, url_prefix="/auth")

@bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("main.index"))
```

### Best Practices

- **URL prefixes**: Use `url_prefix` to organize routes logically
- **Module organization**: Keep related routes together in a single blueprint
- **Separation of concerns**: auth, api, admin, etc. as separate blueprints

## Configuration Management

Use environment-based configuration to keep secrets and environment-specific settings separate.

### Config Classes

```python
# config.py
import os

class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-key")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///dev.db"

class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")

config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
}
```

### Using Configuration

```python
# wsgi.py
from app import create_app
import os

config_name = os.environ.get("FLASK_ENV", "production")
app = create_app(config_name)
```

## Database Models with SQLAlchemy

Define models using SQLAlchemy ORM.

### User Model Example

```python
# app/models/user.py
from app import db
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
```

### Key Principles

- **Never store passwords in plain text**: Use `werkzeug.security` hashing
- **Relationships**: Define foreign keys and relationships clearly
- **Timestamps**: Add `created_at` and `updated_at` columns for auditing
- **Validation**: Use SQLAlchemy validators or Pydantic for input validation

## Request Validation with Pydantic

Use Pydantic for strict input validation on API endpoints.

### Example

```python
from pydantic import BaseModel, EmailStr, validator

class UserCreateRequest(BaseModel):
    username: str
    email: EmailStr
    password: str

    @validator('username')
    def username_alphanumeric(cls, v):
        if not v.replace('_', '').isalnum():
            raise ValueError('Username must be alphanumeric')
        return v

    @validator('password')
    def password_strong(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        return v
```

## Authentication with Flask-Login

Flask-Login manages user sessions and authentication state.

### Setup

```python
# app/__init__.py
from flask_login import LoginManager
from app.models.user import User

login_manager = LoginManager()
login_manager.login_view = 'auth.login'

def create_app(config_name: str = "development"):
    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name])

    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(id):
        return User.query.get(int(id))

    return app
```

### Protecting Routes

```python
from flask_login import login_required, current_user

@bp.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html", user=current_user)
```

## Error Handling

Implement proper error handling for user-friendly responses.

### Error Handlers

```python
# app/__init__.py
def create_app(config_name: str = "development"):
    app = Flask(__name__)
    # ... other setup ...

    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('errors/500.html'), 500

    return app
```

## Logging

Configure structured logging for debugging and monitoring.

### Setup

```python
import logging
from logging.handlers import RotatingFileHandler

def create_app(config_name: str = "development"):
    app = Flask(__name__)
    # ... other setup ...

    if not app.debug and not app.testing:
        if not os.path.exists('logs'):
            os.mkdir('logs')

        file_handler = RotatingFileHandler('logs/app.log',
                                           maxBytes=10240,
                                           backupCount=10)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('Flask app startup')

    return app
```

## Testing Pattern

Use pytest for testing with fixtures and separated test configurations.

### Example

```python
# tests/conftest.py
import pytest
from app import create_app
from app.models import db

@pytest.fixture
def app():
    app = create_app("testing")

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

# tests/test_main.py
def test_index(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Welcome" in response.data
```
