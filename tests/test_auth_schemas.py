"""
Unit tests for Marshmallow authentication schemas.

Tests validation logic for registration, login, password reset, etc.
"""
import pytest
from marshmallow import ValidationError
from tuned.apis.auth.schemas import (
    RegistrationSchema,
    LoginSchema,
    PasswordResetRequestSchema,
    PasswordResetConfirmSchema,
    EmailVerificationSchema,
    ResendVerificationSchema,
)
from tuned.models.user import User


class TestRegistrationSchema:
    """Tests for user registration schema."""
    
    def test_valid_registration_data(self, db):
        """Test that valid registration data passes validation."""
        schema = RegistrationSchema()
        data = {
            'username': 'newuser',
            'email': 'new@example.com',
            'password': 'SecurePass123!',
            'confirm_password': 'SecurePass123!',
            'first_name': 'John',
            'last_name': 'Doe',
            'gender': 'male',
            'phone_number': '+1234567890'
        }
        
        result = schema.load(data)
        
        assert result['username'] == 'newuser'
        assert result['email'] == 'new@example.com'
        assert 'password' in result
    
    def test_registration_password_mismatch(self, db):
        """Test that mismatched passwords fail validation."""
        schema = RegistrationSchema()
        data = {
            'username': 'newuser',
            'email': 'new@example.com',
            'password': 'SecurePass123!',
            'confirm_password': 'DifferentPass123!',
            'first_name': 'John',
            'last_name': 'Doe',
            'gender': 'male'
        }
        
        with pytest.raises(ValidationError) as exc_info:
            schema.load(data)

        messages_str = str(exc_info.value.messages)
        assert 'do not match' in messages_str.lower() or 'confirmPassword' in exc_info.value.messages
    
    def test_registration_duplicate_email(self, db, sample_user):
        """Test that duplicate email fails validation."""
        schema = RegistrationSchema()
        data = {
            'username': 'differentuser',
            'email': sample_user.email,  # Duplicate
            'password': 'SecurePass123!',
            'confirm_password': 'SecurePass123!',
            'first_name': 'John',
            'last_name': 'Doe',
            'gender': 'male'
        }
        
        with pytest.raises(ValidationError) as exc_info:
            schema.load(data)
        
        assert 'email' in exc_info.value.messages
        assert 'already exists' in str(exc_info.value.messages)
    
    def test_registration_duplicate_username(self, db, sample_user):
        """Test that duplicate username fails validation."""
        schema = RegistrationSchema()
        data = {
            'username': sample_user.username,  # Duplicate
            'email': 'different@example.com',
            'password': 'SecurePass123!',
            'confirm_password': 'SecurePass123!',
            'first_name': 'John',
            'last_name': 'Doe',
            'gender': 'male'
        }
        
        with pytest.raises(ValidationError) as exc_info:
            schema.load(data)
        
        assert 'username' in exc_info.value.messages
        assert 'already exists' in str(exc_info.value.messages)
    
    def test_registration_weak_password(self, db):
        """Test that weak password fails validation."""
        schema = RegistrationSchema()
        data = {
            'username': 'newuser',
            'email': 'new@example.com',
            'password': 'weak',
            'confirm_password': 'weak',
            'first_name': 'John',
            'last_name': 'Doe',
            'gender': 'male'
        }
        
        with pytest.raises(ValidationError) as exc_info:
            schema.load(data)
        
        assert 'password' in exc_info.value.messages
    
    def test_registration_invalid_email(self, db):
        """Test that invalid email fails validation."""
        schema = RegistrationSchema()
        data = {
            'username': 'newuser',
            'email': 'notanemail',
            'password': 'SecurePass123!',
            'confirm_password': 'SecurePass123!',
            'first_name': 'John',
            'last_name': 'Doe',
            'gender': 'male'
        }
        
        with pytest.raises(ValidationError) as exc_info:
            schema.load(data)
        
        assert 'email' in exc_info.value.messages
    
    def test_registration_invalid_gender(self, db):
        """Schema normalizes unknown genders to 'unknown' — no error raised."""
        schema = RegistrationSchema()
        data = {
            'username': 'newuser',
            'email': 'new@example.com',
            'password': 'SecurePass123!',
            'confirm_password': 'SecurePass123!',
            'first_name': 'John',
            'last_name': 'Doe',
            'gender': 'invalid'
        }
        result = schema.load(data)
        assert result['gender'] == 'unknown'
    
    def test_registration_invalid_phone(self, db):
        """Test that invalid phone number fails validation."""
        schema = RegistrationSchema()
        data = {
            'username': 'newuser',
            'email': 'new@example.com',
            'password': 'SecurePass123!',
            'confirm_password': 'SecurePass123!',
            'first_name': 'John',
            'last_name': 'Doe',
            'gender': 'male',
            'phone_number': 'invalid'
        }
        
        with pytest.raises(ValidationError) as exc_info:
            schema.load(data)
        
        assert 'phone_number' in exc_info.value.messages


class TestLoginSchema:
    """Tests for login schema."""
    
    def test_valid_login_data(self):
        """Test that valid login data passes validation."""
        schema = LoginSchema()
        data = {
            'identifier': 'test@example.com',
            'password': 'TestPass123!',
            'remember_me': True
        }

        result = schema.load(data)

        assert result['identifier'] == 'test@example.com'
        assert result['password'] == 'TestPass123!'
        assert result['remember_me'] is True

    def test_login_without_remember_me(self):
        """Test that remember_me defaults to False."""
        schema = LoginSchema()
        data = {
            'identifier': 'test@example.com',
            'password': 'TestPass123!'
        }

        result = schema.load(data)

        assert result['remember_me'] is False

    def test_login_missing_email(self):
        """Test that missing identifier fails validation."""
        schema = LoginSchema()
        data = {
            'password': 'TestPass123!'
        }

        with pytest.raises(ValidationError) as exc_info:
            schema.load(data)

        assert 'identifier' in exc_info.value.messages

    def test_login_missing_password(self):
        """Test that missing password fails validation."""
        schema = LoginSchema()
        data = {
            'identifier': 'test@example.com'
        }

        with pytest.raises(ValidationError) as exc_info:
            schema.load(data)

        assert 'password' in exc_info.value.messages


class TestPasswordResetSchemas:
    """Tests for password reset schemas."""
    
    def test_valid_reset_request(self):
        """Test that valid reset request passes validation."""
        schema = PasswordResetRequestSchema()
        data = {
            'email': 'test@example.com'
        }
        
        result = schema.load(data)
        
        assert result['email'] == 'test@example.com'
    
    def test_reset_request_invalid_email(self):
        """Test that invalid email fails validation."""
        schema = PasswordResetRequestSchema()
        data = {
            'email': 'notanemail'
        }
        
        with pytest.raises(ValidationError) as exc_info:
            schema.load(data)
        
        assert 'email' in exc_info.value.messages
    
    def test_valid_reset_confirm(self):
        """Test that valid reset confirmation passes validation."""
        schema = PasswordResetConfirmSchema()
        data = {
            'token': 'valid_token_string',
            'new_password': 'NewSecurePass123!',
            'confirm_password': 'NewSecurePass123!'
        }
        
        result = schema.load(data)
        
        assert result['token'] == 'valid_token_string'
        assert result['new_password'] == 'NewSecurePass123!'
    
    def test_reset_confirm_password_mismatch(self):
        """Test that mismatched passwords fail validation."""
        schema = PasswordResetConfirmSchema()
        data = {
            'token': 'valid_token_string',
            'new_password': 'NewSecurePass123!',
            'confirm_password': 'DifferentPass123!'
        }
        
        with pytest.raises(ValidationError) as exc_info:
            schema.load(data)
        
        assert 'confirm_password' in exc_info.value.messages
    
    def test_reset_confirm_weak_password(self):
        """Test that weak password fails validation."""
        schema = PasswordResetConfirmSchema()
        data = {
            'token': 'valid_token_string',
            'new_password': 'weak',
            'confirm_password': 'weak'
        }
        
        with pytest.raises(ValidationError) as exc_info:
            schema.load(data)
        
        assert 'new_password' in exc_info.value.messages


class TestEmailVerificationSchemas:
    """Tests for email verification schemas."""
    
    def test_valid_verification_token(self):
        """Test that valid uid + token passes validation."""
        schema = EmailVerificationSchema()
        token_value = 'a' * 40  # must be >= 40 chars
        data = {
            'uid': 'some-user-uid-value',
            'token': token_value,
        }

        result = schema.load(data)

        assert result['token'] == token_value
        assert result['uid'] == 'some-user-uid-value'

    def test_verification_missing_token(self):
        """Test that missing token fails validation."""
        schema = EmailVerificationSchema()
        data = {'uid': 'some-user-uid-value'}

        with pytest.raises(ValidationError) as exc_info:
            schema.load(data)

        assert 'token' in exc_info.value.messages
    
    def test_valid_resend_verification(self):
        """Test that valid resend request passes validation."""
        schema = ResendVerificationSchema()
        data = {
            'email': 'test@example.com'
        }
        
        result = schema.load(data)
        
        assert result['email'] == 'test@example.com'
    
    def test_resend_verification_invalid_email(self):
        """Test that invalid email fails validation."""
        schema = ResendVerificationSchema()
        data = {
            'email': 'notanemail'
        }
        
        with pytest.raises(ValidationError) as exc_info:
            schema.load(data)
        
        assert 'email' in exc_info.value.messages
