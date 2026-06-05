from __future__ import annotations

import logging
from tuned.core.events import EventBus, EventPayload
from tuned.core.logging import get_logger

logger: logging.Logger = get_logger(__name__)


def _safe_delay(task: object, *args: object, **kwargs: object) -> None:
    """Call a Celery task's .delay() without blocking if the broker is down."""
    try:
        getattr(task, 'delay')(*args, **kwargs)
    except Exception:
        pass


class OrderEventHandlers:
    def __init__(self, event_bus: EventBus) -> None:
        self._bus = event_bus

    def register(self) -> None:
        self._bus.on("order.status_changed", self._on_status_changed)
        self._bus.on("order.created",        self._on_created)
        logger.info("[OrderEventHandlers] registered")

    def _on_status_changed(self, payload: EventPayload) -> None:
        order_id    = payload.get("order_id")
        client_id   = payload.get("client_id")
        new_status  = payload.get("new_status", "")
        progress    = payload.get("progress", 0)
        delivered_at = payload.get("delivered_at")
        order_number = payload.get("order_number", "")
        try:
            from tuned.extensions import socketio
            socketio.emit(
                "order.updated",
                {
                    "id":           str(order_id),
                    "order_number": order_number,
                    "status":       new_status,
                    "progress":     progress,
                    "delivered_at": delivered_at,
                },
                room=f"user_{client_id}",
            )
        except Exception as exc:
            logger.error(
                "[OrderEventHandlers._on_status_changed] Socket emit failed: %r", exc
            )
        try:
            from tuned.tasks.notifications import create_in_app_notification
            from tuned.models.enums import NotificationType
            
            _safe_delay(create_in_app_notification,
                user_id=str(client_id),
                title="Order Updated",
                message=f"Order {order_number} status changed to {new_status}.",
                notification_type=NotificationType.INFO.value.upper(),
            )
        except Exception as exc:
            logger.error(
                "[OrderEventHandlers._on_status_changed] Notification task failed: %r",
                exc,
            )

        try:
            from tuned.utils.dependencies import get_services
            from tuned.dtos.audit import OrderStatusHistoryCreateDTO
            services = get_services()
            services.audit.order_status_history.log_status_change(OrderStatusHistoryCreateDTO(
                order_id=str(order_id),
                user_id=str(client_id),
                old_status=payload.get("old_status"),
                new_status=new_status,
            ))
        except Exception as exc:
            logger.error(
                "[OrderEventHandlers._on_status_changed] Audit failed: %r", exc
            )

    def _on_created(self, payload: EventPayload) -> None:
        client_id    = payload.get("client_id")
        order_number = payload.get("order_number", "")

        try:
            from tuned.tasks.notifications import create_in_app_notification
            from tuned.models.enums import NotificationType
            
            _safe_delay(create_in_app_notification,
                user_id=str(client_id),
                title="New Order Placed",
                message=f"Order {order_number} has been created successfully.",
                notification_type=NotificationType.SUCCESS.value.upper(),
            )
        except Exception as exc:
            logger.error(
                "[OrderEventHandlers._on_created] Notification task failed: %r", exc
            )
