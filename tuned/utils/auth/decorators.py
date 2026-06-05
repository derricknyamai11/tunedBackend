from functools import wraps
from flask import g
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity, get_jwt
from tuned.models.user import User
from tuned.utils.responses import error_response, unauthorized_response, forbidden_response
from typing import Callable, Any


def jwt_required_fresh(f: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(f)
    def wrapped(*args: Any, **kwargs: Any) -> Any:
        # Verify JWT and check freshness
        verify_jwt_in_request(fresh=True)
        
        user_id = get_jwt_identity()
        user = User.query.get(str(user_id))
        
        if not user:
            return unauthorized_response('User not found')
        
        g.current_user = user
        
        return f(*args, **kwargs)
    
    return wrapped


def admin_required(f: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(f)
    def wrapped(*args: Any, **kwargs: Any) -> Any:
        verify_jwt_in_request()

        user_id = get_jwt_identity()
        user = User.query.get(str(user_id))

        if not user:
            return unauthorized_response('User not found')

        if not user.is_admin:
            return forbidden_response('Admin privileges required')

        g.current_user = user

        return f(*args, **kwargs)

    return wrapped


def verified_email_required(f: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(f)
    def wrapped(*args: Any, **kwargs: Any) -> Any:
        # Get current user from JWT
        user_id = get_jwt_identity()
        user = User.query.get(str(user_id))
        
        if not user:
            return unauthorized_response('User not found')
        
        if not user.email_verified:
            return error_response(
                'Email verification required. Please check your email for the verification link.',
                status=403
            )
        
        g.current_user = user
        
        return f(*args, **kwargs)
    
    return wrapped


def active_user_required(f: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(f)
    def wrapped(*args: Any, **kwargs: Any) -> Any:
        # Get current user from JWT
        user_id = get_jwt_identity()
        user = User.query.get(str(user_id))
        
        if not user:
            return unauthorized_response('User not found')
        
        if not user.is_active or user.deleted_at:
            return forbidden_response('Account is deactivated')
        
        g.current_user = user
        
        return f(*args, **kwargs)
    
    return wrapped


def combined_auth_check(require_verified: bool = True, require_admin: bool = False) -> Callable[..., Any]:
    def decorator(f: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(f)
        def wrapped(*args: Any, **kwargs: Any) -> Any:
            # Verify JWT
            verify_jwt_in_request()
            
            user_id = get_jwt_identity()
            user = User.query.get(str(user_id))
            
            if not user:
                return unauthorized_response('User not found')
            
            # Check if active
            if not user.is_active or user.deleted_at:
                return forbidden_response('Account is deactivated')
            
            # Check email verification if required
            if require_verified and not user.email_verified:
                return error_response(
                    'Email verification required',
                    status=403
                )
            
            # Check admin if required
            if require_admin and not user.is_admin:
                return forbidden_response('Admin privileges required')
            
            g.current_user = user
            
            return f(*args, **kwargs)
        
        return wrapped
    return decorator
