"""
Pytest configuration and shared fixtures.

Provides reusable fixtures for testing the Flask application.
"""
import pytest
import os
from tuned import create_app
from tuned.extensions import db as _db
from tuned.models.user import User, GenderEnum
from tuned.utils.auth import hash_password
from werkzeug.security import generate_password_hash as _wp_hash
from datetime import datetime, timezone
import sys
from unittest.mock import MagicMock
sys.modules['celery'] = MagicMock()

@pytest.fixture(scope='session')
def app():
    """
    Create and configure a Flask app instance for testing.
    
    Uses a separate test database and configuration.
    """
    # Set test environment
    os.environ['FLASK_ENV'] = 'testing'
    
    # Create app
    app = create_app()
    
    # Override config for testing
    app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',  # In-memory database
        'WTF_CSRF_ENABLED': False,
        'CELERY_TASK_ALWAYS_EAGER': True,  # Run Celery tasks synchronously
        'REDIS_URL': 'redis://localhost:6379/15',  # Separate Redis DB for tests
        'JWT_SECRET_KEY': 'test-secret-key-for-testing-only',
        'SECRET_KEY': 'test-secret-key-for-testing-only',
        'JWT_TOKEN_LOCATION': ['headers'],
        'JWT_HEADER_NAME': 'Authorization',
        'JWT_HEADER_TYPE': 'Bearer',
    })
    
    # Create application context
    with app.app_context():
        _db.create_all()
        yield app
        _db.session.remove()
        _db.drop_all()


@pytest.fixture(scope='function')
def client(app):
    """
    Create a test client for making HTTP requests.
    """
    return app.test_client()


@pytest.fixture(scope='function')
def db(app):
    """
    Provide a fresh database for each test function.
    """
    with app.app_context():
        _db.create_all()
        yield _db
        _db.session.remove()
        _db.drop_all()


@pytest.fixture(scope='function')
def sample_user(db):
    """
    Create a sample user for testing.
    
    Returns:
        User: Test user with verified email
    """
    user = User(
        username='testuser',
        email='test@example.com',
        first_name='Test',
        last_name='User',
        gender=GenderEnum.MALE,
        phone_number='+1234567890',
        email_verified=True,
        is_active=True,
        created_at=datetime.now(timezone.utc)
    )
    user.password_hash = _wp_hash('TestPass123!')
    user.referral_code = 'TESTREF1'
    
    db.session.add(user)
    db.session.commit()
    
    return user


@pytest.fixture(scope='function')
def unverified_user(db):
    """
    Create a user with unverified email.
    
    Returns:
        User: Test user without email verification
    """
    user = User(
        username='unverified',
        email='unverified@example.com',
        first_name='Unverified',
        last_name='User',
        gender=GenderEnum.FEMALE,
        email_verified=False,
        is_active=True,
        created_at=datetime.now(timezone.utc)
    )
    user.password_hash = _wp_hash('TestPass123!')
    user.referral_code = 'TESTREF2'
    
    db.session.add(user)
    db.session.commit()
    
    return user


@pytest.fixture(scope='function')
def admin_user(db):
    """
    Create an admin user for testing.
    
    Returns:
        User: Test admin user
    """
    user = User(
        username='admin',
        email='admin@example.com',
        first_name='Admin',
        last_name='User',
        gender=GenderEnum.MALE,
        is_admin=True,
        email_verified=True,
        is_active=True,
        created_at=datetime.now(timezone.utc)
    )
    user.password_hash = _wp_hash('AdminPass123!')
    user.referral_code = 'ADMINREF'
    
    db.session.add(user)
    db.session.commit()
    
    return user


@pytest.fixture(scope='function')
def auth_headers(sample_user, app):
    """
    Create authentication headers with JWT token.
    
    Returns:
        dict: Headers with Authorization Bearer token
    """
    from flask_jwt_extended import create_access_token
    
    with app.app_context():
        access_token = create_access_token(identity=str(sample_user.id))
    
    return {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }


@pytest.fixture(scope='function')
def mock_redis(mocker):
    """
    Mock Redis client for testing.
    """
    mock = mocker.patch('tuned.redis_client.redis_client')
    mock.get.return_value = None
    mock.setex.return_value = True
    mock.exists.return_value = 0
    mock.incr.return_value = 1
    return mock


@pytest.fixture(scope='function')
def mock_celery(mocker):
    """
    Mock Celery task execution.
    """
    return mocker.patch('tuned.celery_app.celery_app.task')


@pytest.fixture(scope='function')
def mock_mail(mocker):
    """
    Mock Flask-Mail for email testing.
    """
    return mocker.patch('tuned.extensions.mail.send')
