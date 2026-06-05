from __future__ import annotations

from tuned.models import GenderEnum
from tuned.dtos.base import BaseRequestDTO
from flask import request, current_app, session, make_response, Response, g
from flask_login import current_user, login_required, logout_user
from flask.views import MethodView
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    verify_jwt_in_request,
    get_jwt_identity,
    get_jwt,
    jwt_required,
    set_access_cookies,
    set_refresh_cookies,
    unset_jwt_cookies,
)
from tuned.utils.dependencies import get_services
from tuned.utils.responses import (
    error_response,
    success_response,
    validation_error_response,
    unauthorized_response,
)
from tuned.utils.auth import get_user_ip, get_user_agent
from tuned.utils.decorators import rate_limit
from tuned.core.exceptions import InvalidCredentials as CoreInvalidCredentials
from tuned.core.exceptions import NotFound as CoreNotFound
from tuned.repository.exceptions import (
    AlreadyExists,
    InvalidCredentials as RepoInvalidCredentials,
    NotFound as RepoNotFound,
    DatabaseError as RepoDatabaseError,
)

# Unify: catch either version
InvalidCredentials = (CoreInvalidCredentials, RepoInvalidCredentials)
NotFound = (CoreNotFound, RepoNotFound)
from tuned.core.logging import get_logger
from tuned.apis.auth.schemas.login import LoginSchema
from tuned.apis.auth.schemas.registration import RegistrationSchema
from tuned.apis.auth.schemas.password_reset import (
    PasswordResetRequestSchema,
    PasswordResetConfirmSchema,
)
from tuned.dtos import UserResponseDTO, LoginRequestDTO, CreateUserDTO
from dataclasses import asdict
from marshmallow import ValidationError
import logging
from typing import Any

logger: logging.Logger = get_logger(__name__)

JWT_ACCESS_EXPIRES = 3600  # 1 hour in seconds


class AuthCheck(MethodView):
    def get(self) -> tuple[Any, int]:
        from tuned.models.user import User as _User

        # Primary: JWT cookie/header (set by Login endpoint)
        try:
            verify_jwt_in_request(optional=True)
            user_id = get_jwt_identity()
            if user_id:
                user = _User.query.get(str(user_id))
                if user and user.is_active and not user.deleted_at:
                    data = UserResponseDTO.from_model(user)
                    return success_response(asdict(data))
        except Exception:
            pass

        # Fallback: Flask-Login session (kept for backwards compatibility)
        if current_user.is_authenticated:
            data = UserResponseDTO.from_model(current_user)
            return success_response(asdict(data))

        return error_response('User is not authenticated', status=401)


class Login(MethodView):
    decorators = [rate_limit(max_requests=5, window=60)]

    def post(self) -> tuple[Any, int]:
        try:
            schema = LoginSchema()
            data = request.get_json(silent=True)
            if data is None:
                return error_response('Invalid or missing JSON body', status=400)
            data = schema.load(data)

        except ValidationError as err:
            logger.error(f'Validation error: {str(err)}')
            return validation_error_response(err.messages)

        try:
            from tuned.models.user import User
            dto_data = LoginRequestDTO(
                **data, ip_address=get_user_ip(), user_agent=get_user_agent()
            )
            success, user_dict = get_services().user.login_user(dto_data)

            if not success:
                return error_response('Login failed. Please try again.', status=500)

            # Look up the user to issue JWT tokens
            user = User.query.filter_by(email=user_dict.get('email')).first()
            if not user:
                return error_response('Login failed.', status=500)

            access_token = create_access_token(identity=str(user.id))
            refresh_token = create_refresh_token(identity=str(user.id))

            logger.info(f'User {user_dict.get("email")} logged in successfully')

            # Build the response body first, then attach JWT cookies
            resp_body, status_code = success_response({
                'access_token': access_token,
                'refresh_token': refresh_token,
                'token_type': 'Bearer',
                'expires_in': JWT_ACCESS_EXPIRES,
                'user': user_dict,
            })
            # Set JWT as httpOnly cookies so the server-side auth check can read them
            set_access_cookies(resp_body, access_token)
            set_refresh_cookies(resp_body, refresh_token)
            return resp_body, status_code

        except NotFound:
            return error_response('Invalid credentials', status=401)
        except (CoreInvalidCredentials, RepoInvalidCredentials) as e:
            msg = str(e)
            if 'not verified' in msg.lower():
                return error_response(
                    'Please verify your email before logging in.', status=403
                )
            return unauthorized_response('Invalid credentials')
        except Exception as e:
            # DatabaseError wrapping InvalidCredentials or NotFound (wrong password / user not found)
            msg = str(e)
            if any(k in msg for k in ('Invalid password', 'Invalid email', 'Account locked',
                                      'User not found', 'not found', 'Invalid email or username')):
                return unauthorized_response('Invalid credentials')
            logger.error(f"Login error: {str(e)}")
            return error_response('Login failed. Please try again.', status=500)


class Logout(MethodView):
    def post(self) -> tuple[Any, int] | Response:
        jwt_present = False

        try:
            verify_jwt_in_request()
            jwt_present = True
        except Exception:
            pass

        if not jwt_present and not current_user.is_authenticated:
            return unauthorized_response('Authentication required')

        try:
            if jwt_present:
                jwt_data = get_jwt()
                jti = jwt_data.get('jti')
                if jti:
                    try:
                        exp = jwt_data.get('exp', 0)
                        import time
                        from tuned.redis_client import add_token_to_blacklist
                        ttl = max(int(exp - time.time()), 1)
                        add_token_to_blacklist(jti, ttl)
                    except Exception:
                        pass  # Redis unavailable — token expires naturally

            if current_user.is_authenticated:
                logout_user()
            session.clear()

            resp_body, status_code = success_response('Logged out successfully')
            unset_jwt_cookies(resp_body)
            return resp_body, status_code

        except Exception as e:
            logger.error(f'Logout error: {str(e)}')
            return error_response('Logout failed', status=500)


class Register(MethodView):
    decorators = [rate_limit(max_requests=3, window=300)]

    def post(self) -> tuple[Any, int]:
        try:
            if current_user.is_authenticated:
                logger.debug(f'User {current_user.email} is already authenticated')
                return error_response('Already authenticated', status=409)

            schema = RegistrationSchema()
            data = request.get_json(silent=True)
            if data is None:
                return error_response('Invalid or missing JSON body', status=400)
            data = schema.load(data)

        except ValidationError as err:
            logger.error(f'Validation error: {str(err)}')
            return validation_error_response(err.messages)

        try:
            referred_by_code = None
            if 'confirm_password' in data:
                del data['confirm_password']

            if 'referred_by_code' in data:
                referred_by_code = data['referred_by_code']
                del data['referred_by_code']

            if 'gender' in data:
                data['gender'] = GenderEnum(data['gender'])

            user_dto = CreateUserDTO(**data)
            locale = BaseRequestDTO(
                ip_address=get_user_ip(), user_agent=get_user_agent()
            )
            result = get_services().user.create_user(
                user_dto, locale, referred_by_code=referred_by_code
            )

            auto_verified = bool(result.get('auto_verified'))
            logger.info(f'User {result.get("email")} registered successfully (auto_verified={auto_verified})')
            return success_response(
                {
                    'email': result.get('email'),
                    'email_verified': auto_verified,
                    'auto_verified': auto_verified,
                    'message': 'Account created. You can log in now.' if auto_verified else 'Registration successful. Please verify your email.',
                },
                status=201,
            )

        except AlreadyExists:
            logger.error(f'User {data.get("email")} already exists')
            return error_response(
                'An account with that email or username already exists.', status=409
            )
        except Exception as e:
            logger.error(f'Registration error: {str(e)}')
            return error_response('Registration failed. Please try again.', status=500)


class TokenRefresh(MethodView):
    """Refresh an expired access token using a refresh token."""

    def post(self) -> tuple[Any, int]:
        try:
            verify_jwt_in_request(refresh=True)
        except Exception as e:
            msg = str(e).lower()
            if 'only refresh tokens' in msg or 'wrong token type' in msg:
                return error_response('Only refresh tokens are accepted here', status=422)
            if 'invalid' in msg or 'malformed' in msg or 'decode' in msg or 'signature' in msg:
                return error_response('Invalid token', status=422)
            if 'missing' in msg or 'no token' in msg or 'authorization' in msg:
                return unauthorized_response('Valid refresh token required')
            return error_response('Token validation failed', status=422)

        user_id = get_jwt_identity()

        from tuned.models.user import User
        user = User.query.get(str(user_id))

        if not user:
            return unauthorized_response('User not found')

        if not user.is_active or user.deleted_at:
            return error_response('Account is deactivated', status=403)

        if not user.email_verified:
            return error_response('Email verification required', status=403)

        access_token = create_access_token(identity=str(user.id))

        return success_response({
            'access_token': access_token,
            'token_type': 'Bearer',
            'expires_in': JWT_ACCESS_EXPIRES,
        })


class VerifyToken(MethodView):
    """Verify a JWT access token and return user info."""

    def get(self) -> tuple[Any, int]:
        try:
            verify_jwt_in_request()
        except Exception as e:
            msg = str(e).lower()
            # 401 = no token / expired; 422 = malformed/invalid token
            if 'missing' in msg or 'no authorization' in msg or 'expired' in msg:
                return unauthorized_response('Valid access token required')
            return error_response('Invalid token', status=422)

        user_id = get_jwt_identity()

        from tuned.models.user import User
        user = User.query.get(str(user_id))

        if not user:
            return unauthorized_response('User not found')

        if not user.is_active or user.deleted_at:
            return error_response('Account is deactivated', status=403)

        return success_response({
            'user_id': str(user.id),
            'email': user.email,
            'email_verified': user.email_verified,
            'is_admin': user.is_admin,
        })


class VerifyEmailPost(MethodView):
    """POST-based email verification using itsdangerous token."""

    def post(self) -> tuple[Any, int]:
        try:
            data = request.get_json(silent=True) or {}
            token = data.get('token', '').strip()
            if not token:
                return error_response('Verification token is required', status=400)

            from tuned.utils.tokens import verify_verification_token
            payload = verify_verification_token(token)
            if payload is None:
                return error_response(
                    'Invalid or expired verification token', status=400
                )

            from tuned.models.user import User
            user_id = payload.get('user_id')
            user = User.query.get(str(user_id)) if user_id else None
            if not user:
                user = User.query.filter_by(email=payload.get('email')).first()

            if not user:
                return error_response('User not found', status=404)

            if user.email_verified:
                return success_response(
                    {'verified': True, 'already_verified': True},
                    message='Email already verified',
                )

            user.email_verified = True
            user.email_verification_token = None
            from tuned.extensions import db
            db.session.commit()

            return success_response({'verified': True})

        except Exception as e:
            logger.error(f'Email verify error: {str(e)}')
            return error_response('Verification failed', status=500)


class PasswordResetRequest(MethodView):
    decorators = [rate_limit(max_requests=3, window=300)]

    def post(self) -> tuple[Any, int]:
        try:
            schema = PasswordResetRequestSchema()
            data = request.get_json(silent=True) or {}
            data = schema.load(data)
        except ValidationError as e:
            return validation_error_response(e.messages)

        try:
            from tuned.models.user import User
            from tuned.utils.tokens import generate_password_reset_token
            user = User.query.filter_by(email=data['email'], is_deleted=False).first()

            if user:
                token = generate_password_reset_token(str(user.id), user.email)
                # In production, send this token via email
                # For now just log it (email service handles this)
                try:
                    from tuned.core.events import get_event_bus
                    get_event_bus().emit('user.password_reset_requested', {
                        'user_id': str(user.id),
                        'email': user.email,
                        'token': token,
                    })
                except Exception:
                    pass

            # Always return success (don't reveal user existence)
            return success_response(
                {'message': 'If that email is registered, a reset link has been sent.'}
            )

        except Exception as e:
            logger.error(f'Password reset request error: {str(e)}')
            return success_response(
                {'message': 'If that email is registered, a reset link has been sent.'}
            )


class PasswordResetConfirm(MethodView):
    def post(self) -> tuple[Any, int]:
        try:
            schema = PasswordResetConfirmSchema()
            data = request.get_json(silent=True) or {}
            data = schema.load(data)
        except ValidationError as e:
            return validation_error_response(e.messages)

        try:
            from tuned.utils.tokens import verify_password_reset_token
            from tuned.models.user import User
            from tuned.extensions import db

            payload = verify_password_reset_token(data['token'])
            if payload is None:
                return error_response('Invalid or expired reset token', status=400)

            user_id = payload.get('user_id')
            user = User.query.get(str(user_id)) if user_id else None
            if not user:
                user = User.query.filter_by(email=payload.get('email')).first()

            if not user:
                return error_response('User not found', status=404)

            from werkzeug.security import generate_password_hash
            user.password_hash = generate_password_hash(data['new_password'])
            db.session.commit()

            logger.info(f'Password reset for user {user.email}')
            return success_response({'message': 'Password has been reset successfully.'})

        except Exception as e:
            logger.error(f'Password reset confirm error: {str(e)}')
            return error_response('Password reset failed', status=500)
