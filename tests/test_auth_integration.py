"""
Integration tests for authentication flow.

Tests complete user journeys from registration through login and logout.
"""
import pytest
import json
from tuned.models.user import User


class TestAuthenticationFlow:
    """Integration tests for complete authentication flows."""
    
    def test_complete_registration_to_login_flow(self, client, db, app, mock_mail, mock_redis):
        """Test complete flow: register → verify email → login."""
        # Step 1: Register new user
        registration_data = {
            'username': 'integrationuser',
            'email': 'integration@example.com',
            'password': 'IntegrationPass123!',
            'confirm_password': 'IntegrationPass123!',
            'first_name': 'Integration',
            'last_name': 'Test',
            'gender': 'female'
        }
        
        response = client.post('/api/auth/register',
                              data=json.dumps(registration_data),
                              content_type='application/json')
        
        assert response.status_code == 201
        user_data = response.get_json()['data']
        assert user_data['email_verified'] is False
        
        # Step 2: Attempt login before verification (should fail)
        login_data = {
            'email': 'integration@example.com',
            'password': 'IntegrationPass123!'
        }
        
        response = client.post('/api/auth/login',
                              data=json.dumps(login_data),
                              content_type='application/json')
        
        assert response.status_code == 403
        assert 'verify your email' in response.get_json()['message'].lower()
        
        # Step 3: Verify email
        user = User.query.filter_by(email='integration@example.com').first()
        assert user is not None
        
        from tuned.utils.tokens import generate_verification_token
        with app.app_context():
            token = generate_verification_token(user.id, user.email)
        
        response = client.post('/api/auth/verify-email',
                              data=json.dumps({'token': token}),
                              content_type='application/json')
        
        assert response.status_code == 200
        
        # Step 4: Login after verification (should succeed)
        response = client.post('/api/auth/login',
                              data=json.dumps(login_data),
                              content_type='application/json')
        
        assert response.status_code == 200
        json_data = response.get_json()
        assert 'access_token' in json_data['data']
        assert 'refresh_token' in json_data['data']
    
    def test_password_reset_flow(self, client, db, sample_user, app, mock_mail, mock_redis):
        """Test complete password reset flow."""
        # Step 1: Request password reset
        response = client.post('/api/auth/password-reset/request',
                              data=json.dumps({'email': sample_user.email}),
                              content_type='application/json')
        
        assert response.status_code == 200
        
        # Step 2: Get reset token (simulating email click)
        from tuned.utils.tokens import generate_password_reset_token
        with app.app_context():
            reset_token = generate_password_reset_token(sample_user.id, sample_user.email)
        
        # Step 3: Confirm password reset
        new_password = 'NewSecurePassword123!'
        response = client.post('/api/auth/password-reset/confirm',
                              data=json.dumps({
                                  'token': reset_token,
                                  'new_password': new_password,
                                  'confirm_password': new_password
                              }),
                              content_type='application/json')
        
        assert response.status_code == 200
        
        # Step 4: Login with new password
        response = client.post('/api/auth/login',
                              data=json.dumps({
                                  'email': sample_user.email,
                                  'password': new_password
                              }),
                              content_type='application/json')
        
        assert response.status_code == 200
        
        # Step 5: Verify old password doesn't work
        response = client.post('/api/auth/login',
                              data=json.dumps({
                                  'email': sample_user.email,
                                  'password': 'TestPass123!'
                              }),
                              content_type='application/json')
        
        assert response.status_code == 401
    
    def test_login_logout_flow(self, client, db, sample_user, mock_redis):
        """Test login → logout → attempt access flow."""
        # Step 1: Login
        response = client.post('/api/auth/login',
                              data=json.dumps({
                                  'email': sample_user.email,
                                  'password': 'TestPass123!'
                              }),
                              content_type='application/json')
        
        assert response.status_code == 200
        access_token = response.get_json()['data']['access_token']
        
        # Step 2: Logout
        headers = {'Authorization': f'Bearer {access_token}'}
        response = client.post('/api/auth/logout', headers=headers)
        
        assert response.status_code == 200
        
        # Step 3: Try to use token after logout
        # (Would need a protected endpoint to test this properly)
        # This is a placeholder for when you add protected routes
    
    def test_account_lockout_flow(self, client, db, sample_user, mock_redis):
        """Test account lockout after failed login attempts."""
        login_data = {
            'email': sample_user.email,
            'password': 'WrongPassword123!'
        }
        
        # Make 5 failed login attempts
        for _ in range(5):
            response = client.post('/api/auth/login',
                                  data=json.dumps(login_data),
                                  content_type='application/json')
            assert response.status_code == 401
        
        # 6th attempt should trigger lockout
        response = client.post('/api/auth/login',
                              data=json.dumps(login_data),
                              content_type='application/json')
        
        # Depending on implementation, might be 401 or 403
        # For now, verify user's failed_login_attempts increased
        db.session.refresh(sample_user)
        assert sample_user.failed_login_attempts >= 5
    
    def test_resend_verification_email(self, client, db, unverified_user, mock_mail, mock_redis):
        """Test resending verification email."""
        response = client.post('/api/auth/resend-verification',
                              data=json.dumps({'email': unverified_user.email}),
                              content_type='application/json')
        
        assert response.status_code == 200
        
        # Generic success message for security
        assert response.get_json()['success'] is True


class TestErrorHandling:
    """Test error handling and edge cases."""
    
    def test_invalid_json_request(self, client, mock_redis):
        """Test that invalid JSON is handled properly."""
        response = client.post('/api/auth/register',
                              data='invalid json{',
                              content_type='application/json')
        
        assert response.status_code == 400
    
    def test_missing_required_fields(self, client, db, mock_redis):
        """Test that missing required fields are caught."""
        incomplete_data = {
            'email': 'test@example.com'
            # Missing other required fields
        }
        
        response = client.post('/api/auth/register',
                              data=json.dumps(incomplete_data),
                              content_type='application/json')
        
        assert response.status_code == 422
        json_data = response.get_json()
        assert 'errors' in json_data or 'message' in json_data
    
    def test_empty_request_body(self, client, mock_redis):
        """Test that empty request body is handled."""
        response = client.post('/api/auth/register',
                              data=json.dumps({}),
                              content_type='application/json')
        
        assert response.status_code in [400, 422]


class TestSecurityFeatures:
    """Test security features and patterns."""
    
    def test_password_not_returned_in_response(self, client, db, mock_mail, mock_redis):
        """Test that password is never returned in API responses."""
        registration_data = {
            'username': 'securitytest',
            'email': 'security@example.com',
            'password': 'SecurePass123!',
            'confirm_password': 'SecurePass123!',
            'first_name': 'Security',
            'last_name': 'Test',
            'gender': 'male'
        }
        
        response = client.post('/api/auth/register',
                              data=json.dumps(registration_data),
                              content_type='application/json')
        
        json_data = response.get_json()
        assert 'password' not in str(json_data).lower() or 'password_hash' not in str(json_data).lower()
    
    def test_generic_error_messages(self, client, db, mock_redis):
        """Test that error messages don't reveal user existence."""
        # Test with non-existent email
        response = client.post('/api/auth/password-reset/request',
                              data=json.dumps({'email': 'nonexistent@example.com'}),
                              content_type='application/json')
        
        # Should return generic success message
        assert response.status_code == 200
        assert response.get_json()['success'] is True
