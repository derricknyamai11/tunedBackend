import logging
from tuned.utils.dependencies import get_services
from tuned.core.logging import get_logger
from tuned.utils.responses import success_response, error_response
from tuned.utils.auth.decorators import combined_auth_check
from flask import g
from flask.views import MethodView
from dataclasses import asdict
from typing import Any

logger: logging.Logger = get_logger(__name__)

class ReorderOrder(MethodView):
    decorators = [combined_auth_check(require_admin=False)]

    def post(self, order_id: str) -> tuple[Any, int]:
        try:
            dto = get_services().order.reorder(order_id, str(g.current_user.id))
            return success_response(data=asdict(dto), message="Successfully created", status=201)
        except Exception as e:
            logger.error("Failed to create reorder: %s", e)
            return error_response(message="Failed to create reorder", status=500)
