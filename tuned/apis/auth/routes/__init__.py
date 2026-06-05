from tuned.apis.auth.routes.auth import (
    AuthCheck,
    Login,
    Logout,
    Register,
    TokenRefresh,
    VerifyToken,
    VerifyEmailPost,
    PasswordResetRequest,
    PasswordResetConfirm,
)
from tuned.apis.auth.routes.email_verification import (
    EmailVerificationResend,
    EmailVerifyConfirm,
)

from typing import Any

ROUTES: list[dict[str, Any]] = [
    # Auth state
    {'url_rule': '/auth/me',        'view_func': AuthCheck.as_view('auth_check'),      'methods': ['GET']},

    # Login / Register / Logout
    {'url_rule': '/auth/login',     'view_func': Login.as_view('login'),               'methods': ['POST']},
    {'url_rule': '/auth/logout',    'view_func': Logout.as_view('logout'),             'methods': ['POST']},
    {'url_rule': '/auth/register',  'view_func': Register.as_view('register'),         'methods': ['POST']},

    # JWT token management
    {'url_rule': '/auth/refresh',       'view_func': TokenRefresh.as_view('token_refresh'),  'methods': ['POST']},
    {'url_rule': '/auth/verify-token',  'view_func': VerifyToken.as_view('verify_token'),     'methods': ['GET']},

    # Email verification
    {
        'url_rule': '/auth/verify-email',
        'view_func': VerifyEmailPost.as_view('verify_email_post'),
        'methods': ['POST'],
    },
    {
        'url_rule': '/auth/email/verify/resend',
        'view_func': EmailVerificationResend.as_view('email_verify_resend'),
        'methods': ['POST'],
    },
    {
        'url_rule': '/auth/email/verify/confirm',
        'view_func': EmailVerifyConfirm.as_view('email_verify_confirm'),
        'methods': ['GET'],
    },
    # Resend alias
    {
        'url_rule': '/auth/resend-verification',
        'view_func': EmailVerificationResend.as_view('email_resend_verification'),
        'methods': ['POST'],
    },

    # Password reset
    {
        'url_rule': '/auth/password-reset/request',
        'view_func': PasswordResetRequest.as_view('password_reset_request'),
        'methods': ['POST'],
    },
    {
        'url_rule': '/auth/password-reset/confirm',
        'view_func': PasswordResetConfirm.as_view('password_reset_confirm'),
        'methods': ['POST'],
    },
]
