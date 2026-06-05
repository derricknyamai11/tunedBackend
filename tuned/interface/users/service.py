from __future__ import annotations
from typing import Optional, TYPE_CHECKING, Any, Tuple, Dict, cast
from datetime import datetime, timezone
import logging
import os
import uuid
from flask_login import login_user
from flask import current_app
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename
from dataclasses import asdict

from tuned.repository.exceptions import AlreadyExists, DatabaseError, NotFound, InvalidCredentials
from tuned.dtos import (
    CreateUserDTO, LoginRequestDTO, UserResponseDTO, UpdateUserDTO,
    ActivityLogCreateDTO, EmailVerificationResendDTO, EmailVerifyConfirmDTO,
    ProfileResponseDTO, UpdateProfileRequestDTO, ChangePasswordRequestDTO
)
from tuned.dtos.base import BaseRequestDTO
from tuned.core.events import get_event_bus
from tuned.core.logging import get_logger
from tuned.utils.variables import Variables
from tuned.utils.auth import is_email_verified_required
from tuned.services.users import UserService as CoreUserService
from tuned.redis_client import redis_client
from tuned.interface.audit import AuditService

if TYPE_CHECKING:
    from tuned.repository import Repository

logger: logging.Logger = get_logger(__name__)
event_bus = get_event_bus()

class UserService:
    def __init__(self, repos: Repository):
        self._repo = repos.user
        self._audit = AuditService(repos=repos)
        self._core = CoreUserService(
            user_repo=repos.user,
            audit_service=self._audit.activity_log
        )

    def login_user(self, credentials: LoginRequestDTO) -> Tuple[bool, Dict[str, Any]]:
        try:
            user = self._core.authenticate_user(credentials)
            
            if is_email_verified_required() and not user.email_verified:
                logger.info(f'Login blocked — email not verified: {user.email}')
                raise InvalidCredentials("Email not verified.")

            login_user(user, remember=credentials.remember_me)
            
            user_dto = UserResponseDTO.from_model(user)
            return True, asdict(user_dto)
        except InvalidCredentials as e:
            logger.error(f"Login failed: {e}")
            raise e
        except Exception as e:
            logger.error(f"Unexpected login error: {e}")
            raise DatabaseError(str(e))

    def create_user(self, data: CreateUserDTO, locale: BaseRequestDTO, referred_by_code: Optional[str] = None) -> Dict[str, Any]:
        try:
            created_user = self._core.register_user(
                data,
                locale.ip_address or "unknown",
                locale.user_agent or "unknown"
            )

            # In dev mode (REQUIRE_EMAIL_VERIFICATION=False), auto-verify the user
            # so they can log in immediately without needing an email.
            from flask import current_app
            from tuned.extensions import db as _db
            if not is_email_verified_required():
                created_user.email_verified = True
                created_user.is_active = True
                _db.session.commit()
                logger.info(f'[create_user] Auto-verified {created_user.email} (dev mode)')
                return {'email': created_user.email, 'auto_verified': True}

            try:
                _user, raw_token = self._repo.generate_verification_token(str(created_user.id))
                event_bus.emit('user.registered', {
                    'user_id': created_user.id,
                    'raw_token': raw_token,
                    'email': created_user.email,
                    'name': created_user.get_name()
                })

                if referred_by_code is not None:
                    event_bus.emit('user.registered_with_referral', {
                        'new_user_id': str(created_user.id),
                        'referral_code': referred_by_code
                    })
            except Exception as token_exc:
                logger.error(f'[create_user] Token/email step failed for user {created_user.id}: {token_exc!r}')

            return {'email': created_user.email}
        except AlreadyExists as e:
            raise e
        except Exception as e:
            raise DatabaseError(str(e))

    def resend_verification_email(self, dto: EmailVerificationResendDTO) -> bool:
        cooldown_key = f'email_resend_cooldown:{dto.email}'
        try:
            if redis_client.exists(cooldown_key):
                ttl: int = int(cast(Any, redis_client.ttl(cooldown_key)))
                raise ValueError(f'rate_limited:{ttl}')
        except ValueError:
            raise
        except Exception:
            pass  # Redis unavailable — skip rate limiting

        user = self._repo.get_user_for_resend(dto.email)
        if user is None or user.email_verified:
            return True

        try:
            _user, raw_token = self._repo.generate_verification_token(str(user.id))
            event_bus.emit('user.resend_verification_email', {
                'user_id': _user.id,
                'raw_token': raw_token,
                'email': _user.email,
                'name': _user.get_name()
            })
        except AlreadyExists:
            return True
        except Exception as exc:
            logger.error(f'[resend] Token/email error for {dto.email}: {exc!r}')
            try:
                redis_client.setex(cooldown_key, 60, '1')
            except Exception:
                pass
            raise

        try:
            redis_client.setex(cooldown_key, 60, '1')
        except Exception:
            pass
        return True

    def confirm_email_verification(self, dto: EmailVerifyConfirmDTO) -> Tuple[bool, str]:
        try:
            verified_user = self._repo.confirm_email_verification(dto.uid, dto.token)
            
            self._audit.activity_log.log(ActivityLogCreateDTO(
                user_id=str(verified_user.id),
                action=Variables.EMAIL_VERIFICATION_ACTION,
                entity_type=Variables.USER_ENTITY_TYPE,
                entity_id=str(verified_user.id),
                before=None,
                after=asdict(UserResponseDTO.from_model(verified_user)),
                ip_address=dto.ip_address,
                user_agent=dto.user_agent,
                created_by=str(verified_user.id),
            ))
            self._repo.save()

            event_bus.emit('user.email_verified', {'user_id': verified_user.id})
            return True, Variables.OK
        except (NotFound, AlreadyExists) as e:
            return False, str(e)
        except ValueError as e:
            return False, str(e)

    def get_user_by_id(self, user_id: str) -> Dict[str, Any]:
        try:
            user = self._repo.get_user_by_id(user_id)
            return asdict(UserResponseDTO.from_model(user))
        except Exception as e:
            logger.error(f"Error fetching user by id {user_id}: {str(e)}")
            raise

    def get_user_by_email(self, email: str) -> Dict[str, Any]:
        user = self._repo.get_user_for_resend(email)
        if not user:
            raise NotFound("User not found")
        return asdict(UserResponseDTO.from_model(user))

    def get_profile(self, user_id: str) -> Dict[str, Any]:
        user = self._repo.get_user_by_id(user_id)
        return asdict(ProfileResponseDTO.from_model(user))

    def update_profile(self, user_id: str, data: UpdateProfileRequestDTO, locale: BaseRequestDTO) -> Dict[str, Any]:
        user = self._repo.get_user_by_id(user_id)
        before_snapshot = asdict(UserResponseDTO.from_model(user))

        update_dto = UpdateUserDTO(
            user_id=user_id,
            first_name=data.first_name,
            last_name=data.last_name,
            phone_number=data.phone_number,
            gender=data.gender
        )
        updated_user = self._repo.update_user(update_dto, actor_id=user_id)
        after_snapshot = asdict(UserResponseDTO.from_model(updated_user))
        
        self._audit.activity_log.log(ActivityLogCreateDTO(
            user_id=user_id,
            action=Variables.PROFILE_UPDATE_ACTION,
            entity_type=Variables.USER_ENTITY_TYPE,
            entity_id=user_id,
            before=before_snapshot,
            after=after_snapshot,
            ip_address=locale.ip_address,
            user_agent=locale.user_agent,
            created_by=user_id
        ))
        self._repo.save()
        return asdict(ProfileResponseDTO.from_model(updated_user))

    def change_password(self, user_id: str, data: ChangePasswordRequestDTO, locale: BaseRequestDTO) -> bool:
        user = self._repo.get_user_by_id(user_id)
        if not user.check_password(data.current_password):
            raise InvalidCredentials("Invalid current password.")
            
        new_hash = generate_password_hash(data.new_password)
        updated_user = self._repo.update_user(
            UpdateUserDTO(user_id=user_id, password_hash=new_hash),
            actor_id=user_id
        )
        
        self._audit.activity_log.log(ActivityLogCreateDTO(
            user_id=user_id,
            action=Variables.PASSWORD_CHANGE_ACTION,
            entity_type=Variables.USER_ENTITY_TYPE,
            entity_id=user_id,
            before=None,
            after=None,
            ip_address=locale.ip_address,
            user_agent=locale.user_agent,
            created_by=user_id
        ))
        self._repo.save()
        return True

    # Magic bytes (file signatures) for allowed image types
    _ALLOWED_IMAGE_SIGNATURES: Dict[bytes, str] = {
        b'\xff\xd8\xff': '.jpg',
        b'\x89PNG\r\n\x1a\n': '.png',
        b'GIF87a': '.gif',
        b'GIF89a': '.gif',
        b'RIFF': '.webp',   # WebP starts with RIFF....WEBP
        b'\x00\x00\x00\x0cjP  ': '.jp2',  # JPEG 2000
    }
    _ALLOWED_EXTENSIONS: frozenset = frozenset({'.jpg', '.jpeg', '.png', '.gif', '.webp'})
    _MAX_AVATAR_SIZE: int = 5 * 1024 * 1024  # 5 MB

    def _validate_image_magic_bytes(self, file: Any) -> str:
        """Read the first 12 bytes and check against known image signatures.
        Returns the validated extension or raises ValueError."""
        header = file.read(12)
        file.seek(0)  # Reset stream so the full file can be saved

        for magic, ext in self._ALLOWED_IMAGE_SIGNATURES.items():
            if header.startswith(magic):
                # Special check for WebP: bytes 8-11 must be 'WEBP'
                if magic == b'RIFF' and header[8:12] != b'WEBP':
                    continue
                return ext

        raise ValueError("File is not a recognised image format (JPEG, PNG, GIF, WebP).")

    def upload_avatar(self, user_id: str, file: Any, locale: BaseRequestDTO) -> Dict[str, Any]:
        user = self._repo.get_user_by_id(user_id)

        # ── Security: validate file size ─────────────────────────────────
        file.seek(0, 2)
        size = file.tell()
        file.seek(0)
        if size > self._MAX_AVATAR_SIZE:
            raise ValueError(f"Avatar must be under {self._MAX_AVATAR_SIZE // (1024*1024)} MB.")

        # ── Security: validate magic bytes (not just Content-Type) ───────
        validated_ext = self._validate_image_magic_bytes(file)

        # ── Security: also validate the declared extension ────────────────
        original_filename = getattr(file, "filename", "avatar.png") or "avatar.png"
        filename = secure_filename(original_filename)
        declared_ext = os.path.splitext(filename)[1].lower()
        if declared_ext not in self._ALLOWED_EXTENSIONS:
            declared_ext = validated_ext  # fall back to magic-byte-determined extension

        unique_filename = f"{uuid.uuid4().hex}{declared_ext}"

        static_folder = current_app.static_folder or "static"
        upload_folder = os.path.join(static_folder, 'client/assets/profile_pics')
        os.makedirs(upload_folder, exist_ok=True)

        file_path = os.path.join(upload_folder, unique_filename)
        file.save(file_path)
        
        updated_user = self._repo.update_user(
            UpdateUserDTO(user_id=user_id, profile_pic=unique_filename),
            actor_id=user_id
        )
        
        self._audit.activity_log.log(ActivityLogCreateDTO(
            user_id=user_id,
            action=Variables.AVATAR_UPLOAD_ACTION,
            entity_type=Variables.USER_ENTITY_TYPE,
            entity_id=user_id,
            before=None,
            after=None,
            ip_address=locale.ip_address,
            user_agent=locale.user_agent,
            created_by=user_id
        ))
        self._repo.save()
        return {"profile_pic_url": updated_user.get_profile_pic_url()}

    def delete_avatar(self, user_id: str, locale: BaseRequestDTO) -> Dict[str, Any]:
        user = self._repo.get_user_by_id(user_id)
        updated_user = self._repo.update_user(
            UpdateUserDTO(user_id=user_id, profile_pic="default.png"),
            actor_id=user_id
        )
        self._audit.activity_log.log(ActivityLogCreateDTO(
            user_id=user_id,
            action=Variables.AVATAR_DELETE_ACTION,
            entity_type=Variables.USER_ENTITY_TYPE,
            entity_id=user_id,
            before=None,
            after=None,
            ip_address=locale.ip_address,
            user_agent=locale.user_agent,
            created_by=user_id
        ))
        self._repo.save()
        return {"profile_pic_url": updated_user.get_profile_pic_url()}
