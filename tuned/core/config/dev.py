import os
from dotenv import load_dotenv
from tuned.core.config.base import BaseConfig

load_dotenv()

class DevelopmentConfig(BaseConfig):
    DEBUG: bool = True
    TESTING: bool = False

    SQLALCHEMY_DATABASE_URI: str = os.environ.get('SQLALCHEMY_DATABASE_URI') or 'sqlite:///app.db'
    SQLALCHEMY_ECHO: bool = False
    # Enable WAL mode for SQLite to allow concurrent reads/writes without locking
    SQLALCHEMY_ENGINE_OPTIONS: dict = {
        "connect_args": {"check_same_thread": False},
        "pool_pre_ping": True,
    }

    # In development without Redis: use in-memory Celery backend to avoid
    # connection retry hangs. Tasks are still dispatched but results not stored.
    CELERY_RESULT_BACKEND: str = 'cache+memory://'
    CELERY_TASK_STORE_ERRORS_EVEN_IF_IGNORED: bool = False

    CORS_ORIGINS: list[str] = [
        'http://localhost:3000',
    ]
    
    SESSION_COOKIE_SECURE: bool = False
    REMEMBER_COOKIE_SECURE: bool = False
    JWT_COOKIE_SECURE: bool = False
    
    PROXY_FIX: bool = False

