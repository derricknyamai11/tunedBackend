"""
Unit tests for refresh token endpoint.

Tests token refresh, token verification, and security features.
"""
import pytest
import json
from flask_jwt_extended import create_access_token, create_refresh_token


class TestRefreshTokenRoute:
    """Tests for JWT token refresh endpoint."""
    
    def test_successful_token_refresh(self, client, db, sample_user, app, mock_redis):
        """Test successful access token refresh."""
        with app.app_context():
            refresh_token = create_refresh_token(identity=str(sample_user.id))
        
        headers = {
            'Authorization': f'Bearer {refresh_token}',
            'Content-Type': 'application/json'
        }
        
        response = client.post('/api/auth/refresh', headers=headers)
        
        assert response.status_code == 200
        json_data = response.get_json()
        assert json_data['success'] is True
        assert 'access_token' in json_data['data']
        assert json_data['data']['token_type'] == 'Bearer'
        assert json_data['data']['expires_in'] == 3600
    
    def test_refresh_with_access_token_fails(self, client, db, sample_user, app):
        """Test that access token cannot be used for refresh."""
        with app.app_context():
            access_token = create_access_token(identity=str(sample_user.id))
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        response = client.post('/api/auth/refresh', headers=headers)
        
        # Should fail because it's an access token not refresh token
        assert response.status_code == 422  # Flask-JWT-Extended default
    
    def test_refresh_without_token(self, client, db):
        """Test refresh request without token."""
        response = client.post('/api/auth/refresh')
        
        assert response.status_code == 401
    
    def test_refresh_with_invalid_token(self, client, db):
        """Test refresh with invalid token."""
        headers = {
            'Authorization': 'Bearer invalid_token_string',
            'Content-Type': 'application/json'
        }
        
        response = client.post('/api/auth/refresh', headers=headers)
        
        assert response.status_code == 422
    
    def test_refresh_for_unverified_user(self, client, db, unverified_user, app):
        """Test that unverified users cannot refresh tokens."""
        with app.app_context():
            refresh_token = create_refresh_token(identity=str(unverified_user.id))
        
        headers = {
            'Authorization': f'Bearer {refresh_token}',
            'Content-Type': 'application/json'
        }
        
        response = client.post('/api/auth/refresh', headers=headers)
        
        assert response.status_code == 403
        json_data = response.get_json()
        assert 'email verification required' in json_data['message'].lower()
    
    def test_refresh_for_inactive_user(self, client, db, sample_user, app):
        """Test that inactive users cannot refresh tokens."""
        # Deactivate user
        sample_user.is_active = False
        db.session.commit()
        
        with app.app_context():
            refresh_token = create_refresh_token(identity=str(sample_user.id))
        
        headers = {
            'Authorization': f'Bearer {refresh_token}',
            'Content-Type': 'application/json'
        }
        
        response = client.post('/api/auth/refresh', headers=headers)
        
        assert response.status_code == 403
        json_data = response.get_json()
        assert 'deactivated' in json_data['message'].lower()


class TestTokenVerificationRoute:
    """Tests for token verification endpoint."""
    
    def test_verify_valid_access_token(self, client, db, sample_user, auth_headers):
        """Test verification of valid access token."""
        response = client.get('/api/auth/verify-token', headers=auth_headers)
        
        assert response.status_code == 200
        json_data = response.get_json()
        assert json_data['success'] is True
        assert json_data['data']['user_id'] == sample_user.id
        assert json_data['data']['email'] == sample_user.email
        assert json_data['data']['email_verified'] is True
    
    def test_verify_without_token(self, client, db):
        """Test verification without token."""
        response = client.get('/api/auth/verify-token')
        
        assert response.status_code == 401
    
    def test_verify_invalid_token(self, client, db):
        """Test verification with invalid token."""
        headers = {'Authorization': 'Bearer invalid_token'}
        
        response = client.get('/api/auth/verify-token', headers=headers)
        
        assert response.status_code == 422
    
    def test_verify_token_for_inactive_user(self, client, db, sample_user, auth_headers):
        """Test that inactive user's token is rejected."""
        sample_user.is_active = False
        db.session.commit()
        
        response = client.get('/api/auth/verify-token', headers=auth_headers)
        
        assert response.status_code == 403
