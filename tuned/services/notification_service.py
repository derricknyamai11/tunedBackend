from tuned.models.communication import Notification
from tuned.models.enums import NotificationType
from tuned.models.user import User
from typing import Optional, cast
from tuned.dtos.notification import NotificationCreateDTO, NotificationResponseDTO
from tuned.utils.dependencies import get_services
import logging
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

def should_send_notification(user_id: str, notification_category: str = 'general') -> bool:
    from tuned.repository.user.get import GetUserByID
    from tuned.extensions import db

    try:
        user = GetUserByID(cast(Session, db.session)).execute(user_id)
    except Exception:
        logger.debug(f"User {user_id} not found, defaulting to send notification")
        return True
    
    if not user.notification_preferences:
        logger.debug(f"No preferences found for user {user_id}, defaulting to send notification")
        return True
    
    prefs = user.notification_preferences
    
    category_mapping = {
        'order_updates': prefs.order_updates,
        'payment': prefs.payment_notifications,
        'delivery': prefs.delivery_notifications,
        'revision': prefs.revision_updates,
        'extension': prefs.extension_updates,
        'comment': prefs.comment_notifications,
        'support': prefs.support_ticket_updates,
        'marketing': prefs.marketing_emails,
        'general': True
    }
    
    if not prefs.push_notifications:
        logger.debug(f"Push notifications disabled for user {user_id}")
        return False
    
    should_send = category_mapping.get(notification_category, True)
    
    if not should_send:
        logger.debug(f"Notification category '{notification_category}' disabled for user {user_id}")
    
    return should_send


def create_notification(
    user_id: str,
    title: str,
    message: str,
    type: NotificationType = NotificationType.INFO,
    link: Optional[str] = None,
    category: str = 'general'
) -> Optional[NotificationResponseDTO]:
    if not should_send_notification(user_id, category):
        logger.info(f"Skipping notification for user {user_id} (category: {category} disabled)")
        return None
    
    from tuned.tasks.notifications import create_in_app_notification
    try:
        create_in_app_notification.apply_async(
            retry=False,
            kwargs=dict(
                user_id=str(user_id),
                title=title,
                message=message,
                notification_type=type,
                action_url=link,
                category=category,
            ),
        )
        logger.info(f"Notification dispatched for user {user_id}: {title}")
    except Exception:
        pass  # Broker unavailable — skip notification
    return None

def create_welcome_notification(user: User) -> None:
    create_notification(
        user_id=str(user.id),
        title='Welcome to Tuned Essays!',
        message='Thank you for joining us. Please verify your email to get started.',
        type=NotificationType.INFO,
        link='/profile'
    )

def create_email_verified_notification(user: User) -> None:
    create_notification(
        user_id=str(user.id),
        title='Email Verified!',
        message='Your email has been successfully verified. You can now access all features.',
        type=NotificationType.SUCCESS,
        link='/dashboard'
    )

def create_password_changed_notification(user: User) -> None:
    create_notification(
        user_id=str(user.id),
        title='Password Changed',
        message="Your password has been successfully updated. If this wasn't you, please contact support immediately.",
        type=NotificationType.WARNING,
        link='/profile/security'
    )

def emit_notification_via_socket(user_id: int, notification: Notification) -> None:
    pass

def mark_notification_as_read(user_id: str, notification_id: str) -> NotificationResponseDTO:
    services = get_services()
    return services.notification.mark_read(notification_id, user_id)

def mark_all_as_read(user_id: str) -> int:
    services = get_services()
    return services.notification.mark_all_read(user_id)

def get_unread_count(user_id: str) -> int:
    services = get_services()
    return services.notification.get_unread_count(user_id)
