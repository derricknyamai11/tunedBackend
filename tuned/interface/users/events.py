from __future__ import annotations

from tuned.core.events import EventBus, EventPayload
from tuned.core.logging import get_logger
import logging
from typing import cast, Any

logger: logging.Logger = get_logger(__name__)


class UserEventHandlers:
    def __init__(self, event_bus: EventBus) -> None:
        self._bus = event_bus

    def register(self) -> None:
        self._bus.on("user.registered",                self._on_registered)
        self._bus.on("user.resend_verification_email", self._on_resend_verification)
        self._bus.on("user.email_verified",            self._on_email_verified)
        self._bus.on("user.password_changed",          self._on_password_changed)
        logger.info("[UserEventHandlers] registered")

    @staticmethod
    def _safe_async(task: Any, *args: Any, **kwargs: Any) -> None:
        """Call a Celery task without blocking if the broker is unavailable."""
        try:
            task.apply_async(*args, **kwargs)
        except Exception:
            pass  # Broker (Redis) not running — skip background task

    def _on_registered(self, payload: EventPayload) -> None:
        from tuned.services.email_service import send_verification_email
        from tuned.tasks.email import send_welcome_task
        from tuned.repository.user.get import GetUserByID
        from tuned.extensions import db

        user_id   = payload.get("user_id")
        raw_token = payload.get("raw_token")

        try:
            user = GetUserByID(cast(Any, db.session)).execute(str(user_id))
            send_verification_email(user, str(raw_token or ""))
            self._safe_async(send_welcome_task, args=[user_id], countdown=1800, queue="email")
        except Exception as exc:
            logger.error("[UserEventHandlers._on_registered] Error: %r", exc)

    def _on_resend_verification(self, payload: EventPayload) -> None:
        from tuned.services.email_service import send_verification_email
        from tuned.repository.user.get import GetUserByID
        from tuned.extensions import db

        user_id   = payload.get("user_id")
        raw_token = payload.get("raw_token")

        try:
            user = GetUserByID(cast(Any, db.session)).execute(str(user_id))
            send_verification_email(user, str(raw_token or ""))
        except Exception as exc:
            logger.error(
                "[UserEventHandlers._on_resend_verification] Error: %r", exc
            )

    def _on_email_verified(self, payload: EventPayload) -> None:
        from tuned.tasks.notifications import create_in_app_notification
        from tuned.models.enums import NotificationType

        user_id = payload.get("user_id")
        self._safe_async(
            create_in_app_notification,
            kwargs=dict(
                user_id=str(user_id),
                title="Email Verified",
                message="Your email has been verified. Welcome to TunedEssays!",
                notification_type=NotificationType.SUCCESS,
            ),
        )

    def _on_password_changed(self, payload: EventPayload) -> None:
        from tuned.tasks.notifications import create_in_app_notification
        from tuned.models.enums import NotificationType

        user_id = payload.get("user_id")
        self._safe_async(
            create_in_app_notification,
            kwargs=dict(
                user_id=str(user_id),
                title="Password Changed",
                message=(
                    "Your password has been successfully updated. "
                    "If this wasn't you, please contact support immediately."
                ),
                notification_type=NotificationType.WARNING,
            ),
        )
