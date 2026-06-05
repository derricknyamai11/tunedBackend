from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING
from tuned.models import NotificationType

if TYPE_CHECKING:
    from tuned.models.communication import Notification


@dataclass
class NotificationCreateDTO:
    user_id: str
    title: str
    message: str
    notification_type: NotificationType = NotificationType.INFO
    link: Optional[str] = None
    category: str = 'general'

@dataclass
class NotificationResponseDTO:
    id: str
    user_id: str
    title: str
    message: str
    type: str
    link: Optional[str]
    is_read: bool
    created_at: str

    @classmethod
    def from_model(cls, model: "Notification") -> 'NotificationResponseDTO':
        return cls(
            id=str(model.id),
            user_id=str(model.user_id),
            title=model.title,
            message=model.message,
            type=model.type.value if hasattr(model.type, 'value') else str(model.type),
            link=model.link,
            is_read=model.is_read,
            created_at=model.created_at.isoformat() if hasattr(model.created_at, 'isoformat') else str(model.created_at)
        )
