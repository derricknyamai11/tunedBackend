import os
from datetime import timedelta
from dotenv import load_dotenv
from typing import Literal, Optional

load_dotenv()

class BaseConfig:
    APP_VERSION: str = "1.0.0"
    FLASK_ENV: Literal["development", "testing", "production"] = "development"
    APP_NAME: str = "TunedEssays"
    SECRET_KEY: str = os.environ.get('SECRET_KEY') or os.urandom(32).hex()
    LOG_LEVEL: str = "DEBUG"
    LOG_FORMAT: Literal["text", "json"] = "json"
    
    REQUIRE_EMAIL_VERIFICATION: bool = os.environ.get('REQUIRE_EMAIL_VERIFICATION', 'True').lower() not in ('false', '0', 'no')

    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False
    SQLALCHEMY_RECORD_QUERIES: bool = True
    SQLALCHEMY_ECHO: bool = False
    DATABASE_ECHO: bool = False
    JSON_SORT_KEYS: bool = False
    
    SESSION_COOKIE_NAME: str = 'tuned_session'
    SESSION_COOKIE_HTTPONLY: bool = True
    SESSION_COOKIE_SAMESITE: str = 'Lax'
    SESSION_COOKIE_PATH: str = '/'
    PERMANENT_SESSION_LIFETIME: timedelta = timedelta(days=7)
    
    REMEMBER_COOKIE_HTTPONLY: bool = True
    REMEMBER_COOKIE_DURATION: timedelta = timedelta(days=30)
    
    JWT_SECRET_KEY: str = os.environ.get('JWT_SECRET_KEY') or os.environ.get('SECRET_KEY') or os.urandom(32).hex()
    JWT_ACCESS_TOKEN_EXPIRES: timedelta = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES: timedelta = timedelta(days=30)
    JWT_TOKEN_LOCATION: list[str] = ['headers', 'cookies']
    JWT_COOKIE_SECURE: bool = True  # Only send over HTTPS
    JWT_COOKIE_CSRF_PROTECT: bool = True
    JWT_COOKIE_SAMESITE: str = 'Lax'
    JWT_ACCESS_COOKIE_NAME: str = 'tuned_access_token'
    JWT_REFRESH_COOKIE_NAME: str = 'tuned_refresh_token'
    JWT_COOKIE_PATH: str = '/'
    
    MAIL_SERVER: str = os.environ.get('EMAIL_HOST', 'smtp.hostinger.com')
    MAIL_PORT: int = int(os.environ.get('EMAIL_PORT', 587))
    MAIL_USE_TLS: bool = os.environ.get('EMAIL_USE_TLS', 'True').lower() == 'true'
    MAIL_USE_SSL: bool = os.environ.get('EMAIL_USE_SSL', 'False').lower() == 'true'
    MAIL_USERNAME: str = os.environ.get('MAIL_USERNAME') or ""
    MAIL_PASSWORD: str = os.environ.get('MAIL_PASSWORD') or ""
    MAIL_DEFAULT_SENDER: str = os.environ.get('MAIL_DEFAULT_SENDER', 'info@tunedessays.com')
    
    MAX_CONTENT_LENGTH: int = 16 * 1024 * 1024  # 16 MB max file size
    
    SOCKETIO_MESSAGE_QUEUE: Optional[str] = os.environ.get('SOCKETIO_MESSAGE_QUEUE')  # Redis URL for scaling
    
    REDIS_URL: str = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    CELERY_BROKER_URL: str = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/1')
    CELERY_RESULT_BACKEND: str = os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/2')
    CELERY_TASK_SERIALIZER: str = 'json'
    CELERY_RESULT_SERIALIZER: str = 'json'
    CELERY_ACCEPT_CONTENT: list[str] = ['json']
    CELERY_TIMEZONE: str = 'UTC'
    CELERY_ENABLE_UTC: bool = True
    
    JWT_BLACKLIST_ENABLED: bool = True
    JWT_BLACKLIST_TOKEN_CHECKS: list[str] = ['access', 'refresh']
    
    FRONTEND_URL: str = os.environ.get('FRONTEND_URL', 'http://localhost:3000')

    WORDS_PER_PAGE: int = 275