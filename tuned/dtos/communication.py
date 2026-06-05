from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING
from tuned.dtos.base import BaseDTO

if TYPE_CHECKING:
    from tuned.models.communication import NewsletterSubscriber

@dataclass
class NewsletterSubscribeDTO(BaseDTO):
    email: str
    name: Optional[str] = None

@dataclass(kw_only=True)
class NewsletterSubscriberResponseDTO(BaseDTO):
    id: str
    email: str
    name: str
    is_active: bool

    @classmethod
    def from_model(cls, obj: "NewsletterSubscriber") -> "NewsletterSubscriberResponseDTO":
        return cls(
            id=str(obj.id),
            email=obj.email,
            name=obj.name or "",
            is_active=obj.is_active,
            created_at=obj.created_at
        )
