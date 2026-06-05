from __future__ import annotations

from datetime import timezone, datetime
from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING, Union
from tuned.models.enums import GenderEnum

if TYPE_CHECKING:
    from tuned.models.user import User

from tuned.dtos.base import BaseRequestDTO

@dataclass
class CreateUserDTO:
    username: str
    email: str
    password: str
    first_name: str
    last_name: str
    email_verified: bool = False
    gender: GenderEnum = GenderEnum.UNKNOWN
    is_admin: bool = False
    language: str = "en"
    timezone: str = "UTC"
    phone_number: Optional[str] = None
    # referred_by_code: Optional[str] = None

@dataclass
class LoginRequestDTO(BaseRequestDTO):
    identifier: str
    password: str
    remember_me: Optional[bool] = False

@dataclass
class UserResponseDTO:
    id: str
    name: str
    email: str
    avatar_url: str
    is_admin: bool = False
    is_writer: bool = False
    session_created_at: Optional[str] = None

    @classmethod
    def from_model(cls, obj: "User") -> "UserResponseDTO":
        return cls(
            id=str(obj.id),
            name=" ".join(filter(None, [obj.first_name, obj.last_name])),
            email=obj.email,
            avatar_url=obj.get_profile_pic_url(),
            is_admin=obj.is_admin,
            is_writer=getattr(obj, 'is_writer', False),
            session_created_at=datetime.now(timezone.utc).isoformat(),
        )
UserUpdateValue = Union[str, int, bool, datetime]

@dataclass
class UpdateUserDTO:
    user_id: str
    username: Optional[str] = None
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    gender: Optional[GenderEnum] = None
    phone_number: Optional[str] = None
    profile_pic: Optional[str] = None
    failed_login_attempts: Optional[int] = None
    reward_points: Optional[int] = None
    last_failed_login: Optional[datetime] = None
    last_login_at: Optional[datetime] = None
    language: Optional[str] = None
    timezone: Optional[str] = None
    password_hash: Optional[str] = None
    is_admin: Optional[bool] = field(default=None, repr=False)

    def to_dict(self) -> dict[str, UserUpdateValue]:
        return {
            k: v for k, v in self.__dict__.items()
            if k != "user_id" and v is not None
        }


@dataclass
class EmailVerificationResendDTO(BaseRequestDTO):
    email: str


@dataclass
class EmailVerifyConfirmDTO(BaseRequestDTO):
    uid: str
    token: str

@dataclass
class ProfileResponseDTO:
    id: str
    username: str
    email: str
    first_name: str
    last_name: str
    gender: Optional[GenderEnum]
    phone_number: Optional[str]
    profile_pic_url: Optional[str]
    email_verified: bool
    is_admin: bool
    reward_points: int
    last_login_at: Optional[str]
    created_at: Optional[str]
    # Security note: failed_login_attempts and last_failed_login intentionally
    # excluded from profile response to avoid leaking account-lockout state.

    @classmethod
    def from_model(cls, obj: "User") -> "ProfileResponseDTO":
        last_login = obj.last_login_at.isoformat() if obj.last_login_at else None
        created = obj.created_at.isoformat() if obj.created_at else None

        return cls(
            id=str(obj.id),
            username=obj.username,
            email=obj.email,
            first_name=obj.first_name,
            last_name=obj.last_name,
            gender=obj.gender,
            phone_number=obj.phone_number,
            profile_pic_url=obj.get_profile_pic_url(),
            email_verified=obj.email_verified,
            is_admin=obj.is_admin,
            reward_points=obj.reward_points,
            last_login_at=last_login,
            created_at=created,
        )

@dataclass
class UpdateProfileRequestDTO:
    first_name: str
    last_name: str
    phone_number: Optional[str] = None
    gender: Optional[GenderEnum] = None

@dataclass
class ChangePasswordRequestDTO:
    current_password: str
    new_password: str

@dataclass
class UserRewardPointsUpdateDTO:
    reward_points: int