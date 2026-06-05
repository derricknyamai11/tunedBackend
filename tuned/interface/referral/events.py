from __future__ import annotations
import logging
from typing import Dict, Any
from tuned.core.events import EventBus

logger = logging.getLogger(__name__)


def _safe_delay(task: object, *args: object, **kwargs: object) -> None:
    try:
        getattr(task, 'delay')(*args, **kwargs)
    except Exception:
        pass


class ReferralEventHandlers:
    def __init__(self, bus: EventBus) -> None:
        self.bus = bus

    def register(self) -> None:
        self.bus.on("PaymentCompleted", self.handle_payment_completed)
        self.bus.on("ReferralCommissionEarned", self.handle_commission_earned)
        self.bus.on("user.registered_with_referral", self.handle_user_registered_with_referral)
        logger.info("[ReferralEventHandlers] Registered.")

    def handle_user_registered_with_referral(self, payload: Dict[str, Any]) -> None:
        new_user_id = payload.get("new_user_id")
        referral_code = payload.get("referral_code")
        
        if new_user_id and referral_code:
            logger.info(f"[ReferralEventHandlers] Processing referral for new user {new_user_id} with code {referral_code}")
            try:
                from tuned.utils.dependencies import get_services
                get_services().referral.process_signup(str(new_user_id), str(referral_code))
            except Exception as e:
                logger.error(f"[ReferralEventHandlers] Failed to process referral signup: {e}")

    def handle_payment_completed(self, payload: Dict[str, Any]) -> None:
        payment_id = payload.get("payment_id")
        user_id = payload.get("user_id")
        
        if payment_id and user_id:
            logger.info(f"[ReferralEventHandlers] PaymentCompleted event received for user {user_id}. Enqueueing referral check task.")
            from tuned.tasks.referral_tasks import process_referral_reward_task
            
            _safe_delay(process_referral_reward_task,str(payment_id), str(user_id))

    def handle_commission_earned(self, payload: Dict[str, Any]) -> None:
        referrer_id = payload.get("referrer_id")
        commission = payload.get("commission_earned")
        logger.info(f"[ReferralEventHandlers] ReferralCommissionEarned for {referrer_id}: {commission}")
        
        try:
            from tuned.extensions import socketio
            from tuned.tasks.notifications import create_in_app_notification
            from tuned.models.enums import NotificationType
            room = f"user_{referrer_id}"
            socketio.emit('dashboard:points_updated', payload, room=room)
            
            _safe_delay(create_in_app_notification,
                user_id=str(referrer_id),
                title="Referral Points Earned!",
                message=f"Congratulations! You just earned {payload.get('points_earned')} reward points from a successful referral.",
                notification_type=NotificationType.SUCCESS,
                action_url='/dashboard/referrals'
            )
        except Exception as e:
            logger.error(f"[ReferralEventHandlers] Failed to emit socket event: {e}")
