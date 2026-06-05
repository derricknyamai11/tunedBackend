from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING
from datetime import datetime

if TYPE_CHECKING:
    from tuned.models.referral import Referral

from tuned.dtos.base import BaseDTO
from tuned.models.enums import ReferralStatus

@dataclass(kw_only=True)
class ReferralCreateDTO:
    referrer_id: str
    referred_id: str
    code: str
    status: Optional[str] = ReferralStatus.PENDING
    points_earned: Optional[int] = 0

@dataclass(kw_only=True)
class ReferralUpdateDTO:
    status: Optional[str] = None
    points_earned: Optional[int] = None
    points_used: Optional[int] = None
    completed_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None

@dataclass(kw_only=True)
class ReferralResponseDTO(BaseDTO):
    id: str
    referrer_id: str
    referred_id: str
    code: str
    status: str
    points_earned: int
    points_used: int
    completed_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None

    @classmethod
    def from_model(cls, model: "Referral") -> 'ReferralResponseDTO':
        if model.referrer_id is None or model.referred_id is None:
            raise ValueError("Referral model is missing required user identifiers")
        return cls(
            id=str(model.id),
            referrer_id=model.referrer_id,
            referred_id=model.referred_id,
            code=model.code,
            status=model.status.value if hasattr(model.status, 'value') else model.status,
            points_earned=model.points_earned,
            points_used=getattr(model, 'points_used', 0),
            completed_at=getattr(model, 'completed_at', None),
            expires_at=getattr(model, 'expires_at', None),
            created_at=model.created_at,
            updated_at=model.updated_at,
            is_deleted=getattr(model, 'is_deleted', False)
        )

@dataclass(kw_only=True)
class RewardCalculationResultDTO:
    referral_id: str
    referrer_id: str
    referred_id: str
    points_earned: int
    new_status: str


@dataclass(kw_only=True)
class ReferralRedemptionResultDTO:
    redeemed_points: int
    discount_amount: float
    new_balance: int
    order_id: str
    updated_total_price: float
