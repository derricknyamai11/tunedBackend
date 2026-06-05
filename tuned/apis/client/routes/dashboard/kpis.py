from tuned.utils.dependencies import get_services
import logging
from tuned.core.logging import get_logger
from tuned.utils.responses import success_response, error_response
from tuned.utils.auth.decorators import combined_auth_check
from flask import g
from flask.views import MethodView
from dataclasses import asdict
from typing import Any

logger: logging.Logger = get_logger(__name__)

class DashboardKPIs(MethodView):
    decorators = [combined_auth_check(require_admin=False)]

    def get(self) -> tuple[Any, int]:
        try:
            dto = get_services().analytics.get_kpis(str(g.current_user.id))
            return success_response(data=asdict(dto), message="Successfully loaded", status=200)
        except Exception as e:
            logger.error("Failed to load KPIs: %s", e)
            return error_response(message="Failed to load KPIs", status=500)
