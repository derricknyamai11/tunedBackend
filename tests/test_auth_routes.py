"""
Unit tests for authentication routes.

Tests registration, login, logout, email verification, and password reset endpoints.
"""
import pytest
import json
from tuned.models.user import User
from tuned.utils.tokens import generate_verification_token, generate_password_reset_token


class TestRegistrationRoute:
    """Tests for user registration endpoint."""
    
    def test_successful_registration(self, client, db, mock_mail, mock_redis):
        """Test successful user registration."""
        data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'SecurePass123!',
            'confirm_password': 'SecurePass123!',
            'first_name': 'New',
            'last_name': 'User',
            'gender': 'male',
            'phone_number': '+1234567890'
        }
        
        response = client.post('/api/auth/register', 
                              data=json.dumps(data),
                              content_type='application/json')
        
        assert response.status_code == 201
        json_data = response.get_json()
        assert json_data['success'] is True
        assert 'data' in json_data
        assert json_data['data']['email'] == 'newuser@example.com'
        assert json_data['data']['email_verified'] is False
        
        # Verify user created in database
        user = User.query.filter_by(email='newuser@example.com').first()
        assert user is not None
        assert user.username == 'newuser'
    
    def test_registration_duplicate_email(self, client, db, sample_user, mock_redis):
        """Test registration with duplicate email."""
        data = {
            'username': 'differentuser',
            'email': sample_user.email,
            'password': 'SecurePass123!',
            'confirm_password': 'SecurePass123!',
            'first_name': 'Different',
            'last_name': 'User',
            'gender': 'male'
        }
        
        response = client.post('/api/auth/register',
                              data=json.dumps(data),
                              content_type='application/json')
        
        assert response.status_code == 422
        json_data = response.get_json()
        assert json_data['success'] is False
        assert 'email' in json_data['errors']
    
    def test_registration_password_mismatch(self, client, db, mock_redis):
        """Test registration with mismatched passwords."""
        data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'SecurePass123!',
            'confirm_password': 'DifferentPass123!',
            'first_name': 'New',
            'last_name': 'User',
            'gender': 'male'
        }
        
        response = client.post('/api/auth/register',
                              data=json.dumps(data),
                              content_type='application/json')
        
        assert response.status_code == 422
        json_data = response.get_json()
        errors_str = str(json_data.get('errors', {}))
        assert 'confirmPassword' in errors_str or 'confirm_password' in errors_str


class TestLoginRoute:
    """Tests for user login endpoint."""
    
    def test_successful_login(self, client, db, sample_user, mock_redis):
        """Test successful login with verified user."""
        data = {
            'email': sample_user.email,
            'password': 'TestPass123!'
        }
        
        response = client.post('/api/auth/login',
                              data=json.dumps(data),
                              content_type='application/json')
        
        assert response.status_code == 200
        json_data = response.get_json()
        assert json_data['success'] is True
        assert 'access_token' in json_data['data']
        assert 'refresh_token' in json_data['data']
        assert json_data['data']['user']['email'] == sample_user.email
    
    def test_login_with_unverified_email(self, client, db, unverified_user, mock_redis):
        """Test that unverified users cannot login."""
        data = {
            'email': unverified_user.email,
            'password': 'TestPass123!'
        }
        
        response = client.post('/api/auth/login',
                              data=json.dumps(data),
                              content_type='application/json')
        
        assert response.status_code == 403
        json_data = response.get_json()
        assert 'verify your email' in json_data['message'].lower()
    
    def test_login_with_wrong_password(self, client, db, sample_user, mock_redis):
        """Test login with incorrect password."""
        data = {
            'email': sample_user.email,
            'password': 'WrongPassword123!'
        }
        
        response = client.post('/api/auth/login',
                              data=json.dumps(data),
                              content_type='application/json')
        
        assert response.status_code == 401
        json_data = response.get_json()
        assert 'invalid' in json_data['message'].lower()
    
    def test_login_with_nonexistent_user(self, client, db, mock_redis):
        """Test login with non-existent user."""
        data = {
            'email': 'nonexistent@example.com',
            'password': 'TestPass123!'
        }
        
        response = client.post('/api/auth/login',
                              data=json.dumps(data),
                              content_type='application/json')
        
        assert response.status_code == 401
        json_data = response.get_json()
        assert 'invalid' in json_data['message'].lower()


class TestLogoutRoute:
    """Tests for user logout endpoint."""
    
    def test_successful_logout(self, client, db, sample_user, auth_headers, mock_redis):
        """Test successful logout."""
        response = client.post('/api/auth/logout',
                              headers=auth_headers)
        
        assert response.status_code == 200
        json_data = response.get_json()
        assert json_data['success'] is True
        
        # Verify token was blacklisted
        mock_redis.setex.assert_called()
    
    def test_logout_without_token(self, client, db):
        """Test logout without JWT token."""
        response = client.post('/api/auth/logout')
        
        assert response.status_code == 401


class TestEmailVerificationRoute:
    """Tests for email verification endpoint."""
    
    def test_successful_email_verification(self, client, db, unverified_user, app, mock_mail):
        """Test successful email verification."""
        with app.app_context():
            token = generate_verification_token(unverified_user.id, unverified_user.email)
        
        data = {'token': token}
        
        response = client.post('/api/auth/verify-email',
                              data=json.dumps(data),
                              content_type='application/json')
        
        assert response.status_code == 200
        json_data = response.get_json()
        assert json_data['success'] is True
        
        # Verify user is now verified
        db.session.refresh(unverified_user)
        assert unverified_user.email_verified is True
    
    def test_verify_with_invalid_token(self, client, db):
        """Test verification with invalid token."""
        data = {'token': 'invalid_token'}
        
        response = client.post('/api/auth/verify-email',
                              data=json.dumps(data),
                              content_type='application/json')
        
        assert response.status_code == 400
        json_data = response.get_json()
        assert 'invalid' in json_data['message'].lower()
    
    def test_verify_already_verified_email(self, client, db, sample_user, app):
        """Test verifying an already verified email."""
        with app.app_context():
            token = generate_verification_token(sample_user.id, sample_user.email)
        
        data = {'token': token}
        
        response = client.post('/api/auth/verify-email',
                              data=json.dumps(data),
                              content_type='application/json')
        
        assert response.status_code == 200
        json_data = response.get_json()
        assert 'already verified' in json_data['message'].lower()


class TestPasswordResetRoute:
    """Tests for password reset endpoints."""
    
    def test_password_reset_request_success(self, client, db, sample_user, mock_mail, mock_redis):
        """Test successful password reset request."""
        data = {'email': sample_user.email}
        
        response = client.post('/api/auth/password-reset/request',
                              data=json.dumps(data),
                              content_type='application/json')
        
        assert response.status_code == 200
        json_data = response.get_json()
        assert json_data['success'] is True
    
    def test_password_reset_request_nonexistent_email(self, client, db, mock_redis):
        """Test reset request with non-existent email (generic response)."""
        data = {'email': 'nonexistent@example.com'}
        
        response = client.post('/api/auth/password-reset/request',
                              data=json.dumps(data),
                              content_type='application/json')
        
        # Should still return success for security
        assert response.status_code == 200
    
    def test_password_reset_confirm_success(self, client, db, sample_user, app, mock_redis):
        """Test successful password reset confirmation."""
        with app.app_context():
            token = generate_password_reset_token(sample_user.id, sample_user.email)
        
        data = {
            'token': token,
            'new_password': 'NewSecurePass456!',
            'confirm_password': 'NewSecurePass456!'
        }
        
        response = client.post('/api/auth/password-reset/confirm',
                              data=json.dumps(data),
                              content_type='application/json')
        
        assert response.status_code == 200
        json_data = response.get_json()
        assert json_data['success'] is True
        
        # Verify password was changed (uses werkzeug hashing consistent with User model)
        from werkzeug.security import check_password_hash
        db.session.refresh(sample_user)
        assert check_password_hash(sample_user.password_hash, 'NewSecurePass456!')
    
    def test_password_reset_confirm_invalid_token(self, client, db):
        """Test reset confirmation with invalid token."""
        data = {
            'token': 'invalid_token',
            'new_password': 'NewSecurePass456!',
            'confirm_password': 'NewSecurePass456!'
        }
        
        response = client.post('/api/auth/password-reset/confirm',
                              data=json.dumps(data),
                              content_type='application/json')
        
        assert response.status_code == 400
        json_data = response.get_json()
        assert 'invalid' in json_data['message'].lower()
    
    def test_password_reset_confirm_password_mismatch(self, client, db, sample_user, app):
        """Test reset confirmation with mismatched passwords."""
        with app.app_context():
            token = generate_password_reset_token(sample_user.id, sample_user.email)
        
        data = {
            'token': token,
            'new_password': 'NewSecurePass456!',
            'confirm_password': 'DifferentPass789!'
        }
        
        response = client.post('/api/auth/password-reset/confirm',
                              data=json.dumps(data),
                              content_type='application/json')
        
        assert response.status_code == 422
        json_data = response.get_json()
        errors_str = str(json_data.get('errors', {}))
        assert 'confirm_password' in errors_str or 'confirmPassword' in errors_str
