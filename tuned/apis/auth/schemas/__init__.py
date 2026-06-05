from tuned.apis.auth.schemas.registration import RegistrationSchema
from tuned.apis.auth.schemas.login import LoginSchema
from tuned.apis.auth.schemas.password_reset import PasswordResetRequestSchema, PasswordResetConfirmSchema
from tuned.apis.auth.schemas.email_verification import EmailVerifyResendSchema, EmailVerifyConfirmSchema

# Aliases for test compatibility
EmailVerificationSchema = EmailVerifyConfirmSchema
ResendVerificationSchema = EmailVerifyResendSchema

__all__ = [
    'RegistrationSchema',
    'LoginSchema',
    'PasswordResetRequestSchema',
    'PasswordResetConfirmSchema',
    'EmailVerifyResendSchema',
    'EmailVerifyConfirmSchema',
    'EmailVerificationSchema',
    'ResendVerificationSchema',
]
