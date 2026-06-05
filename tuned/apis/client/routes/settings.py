from dataclasses import asdict
from flask import request
from tuned.utils.auth.decorators import combined_auth_check
from flask import g
from flask.views import MethodView
from tuned.utils.dependencies import get_services
from tuned.utils.responses import error_response, success_response, validation_error_response
from tuned.utils.auth import get_user_ip, get_user_agent
from tuned.dtos.base import BaseRequestDTO
from tuned.dtos import build_preference_update_dto
from marshmallow import ValidationError
from tuned.apis.client.schemas.settings import (
    LocalizationUpdateSchema, NotificationUpdateSchema, EmailPreferenceUpdateSchema,
    PrivacyUpdateSchema, AccessibilityUpdateSchema, BillingPreferenceUpdateSchema
)
import logging
from typing import Any

logger: logging.Logger = logging.getLogger(__name__)


def _normalize_validation_errors(errors: Any) -> dict[str, list[str]]:
    if not isinstance(errors, dict):
        return {"non_field_errors": [str(errors)]}

    normalized: dict[str, list[str]] = {}
    for field, messages in errors.items():
        if isinstance(messages, list):
            normalized[field] = [str(message) for message in messages]
        else:
            normalized[field] = [str(messages)]
    return normalized

class SettingsView(MethodView):
    decorators = [combined_auth_check(require_admin=False)]

    def get(self) -> tuple[Any, int]:
        try:
            settings_data = get_services().preferences.get_user_preferences(g.current_user.id)
            return success_response(settings_data.to_dict())
        except Exception as e:
            logger.error(f"Get settings error: {str(e)}")
            return error_response("Failed to fetch settings", status=500)

class SettingsCategoryView(MethodView):
    decorators = [combined_auth_check(require_admin=False)]

    def patch(self, category: str) -> tuple[Any, int]:
        schema_map = {
            "localization": LocalizationUpdateSchema(),
            "notification": NotificationUpdateSchema(),
            "email": EmailPreferenceUpdateSchema(),
            "privacy": PrivacyUpdateSchema(),
            "accessibility": AccessibilityUpdateSchema(),
            "billing": BillingPreferenceUpdateSchema()
        }

        schema = schema_map.get(category)
        if not schema:
            return error_response("Invalid settings category", status=400)

        try:
            data = schema.load(request.get_json())
        except ValidationError as err:
            return validation_error_response(_normalize_validation_errors(err.messages))

        try:
            locale = BaseRequestDTO(ip_address=get_user_ip(), user_agent=get_user_agent())
            dto = build_preference_update_dto(category, data)
            updated_preferences = get_services().preferences.update_category(category, g.current_user.id, dto, locale)
            return success_response({"preferences": asdict(updated_preferences)})
        except ValueError as e:
            logger.error(f"Invalid settings update for {category}: {str(e)}")
            return error_response("Invalid settings payload", status=400)
        except Exception as e:
            logger.error(f"Update settings error for {category}: {str(e)}")
            return error_response("Failed to update settings", status=500)
