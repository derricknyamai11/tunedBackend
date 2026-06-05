import os
from dotenv import load_dotenv
from typing import Optional
from tuned.core.config.base import BaseConfig

load_dotenv()


def _require_env(key: str, min_length: int = 32) -> str:
    value = os.environ.get(key, "")
    if not value or len(value) < min_length:
        raise RuntimeError(
            f"Production requires a strong {key} environment variable "
            f"(min {min_length} characters). "
            "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
        )
    return value


class ProductionConfig(BaseConfig):
    SECRET_KEY: str = _require_env("SECRET_KEY")
    JWT_SECRET_KEY: str = _require_env("JWT_SECRET_KEY")
    DEBUG: bool = False
    TESTING: bool = False
    
    SQLALCHEMY_DATABASE_URI: str = os.environ.get('DATABASE_URL') or \
        'postgresql://{user}:{password}@{host}:{port}/{dbname}'.format(
            user=os.environ.get('DB_USER', 'tunedop'),
            password=os.environ.get('DB_PASSWORD', ''),
            host=os.environ.get('DB_HOST', 'localhost'),
            port=os.environ.get('DB_PORT', '5432'),
            dbname=os.environ.get('DB_NAME', 'tunedessays')
        )

    # SERVER_NAME = os.environ.get('SERVER_NAME')  # e.g., 'tunedessays.com'
    SESSION_COOKIE_DOMAIN: Optional[str] = os.environ.get('SESSION_COOKIE_DOMAIN')
    
    CORS_ORIGINS: list[str] = os.environ.get('CORS_ORIGINS', 'https://tunedessays.com').split(',')
    SESSION_COOKIE_SECURE: bool = True
    REMEMBER_COOKIE_SECURE: bool = True
    JWT_COOKIE_SECURE: bool = True
    JWT_COOKIE_DOMAIN: Optional[str] = os.environ.get('JWT_COOKIE_DOMAIN')
    
    SSL_REDIRECT: bool = os.environ.get('SSL_REDIRECT', 'True').lower() == 'true'
    
    PROXY_FIX: bool = True
    
    SQLALCHEMY_RECORD_QUERIES: bool = False 
