from tuned.core.logging import get_logger
from flask.views import MethodView
from tuned.utils.dependencies import get_services
from tuned.utils.responses import success_response, error_response

from dataclasses import asdict
import json
import logging
from typing import Any
from tuned.utils.cache import cache_get, cache_set, cache_delete, cache_exists

logger: logging.Logger = get_logger(__name__)

CACHE_TTL = 300
CACHE_KEY_ACADEMIC_LEVELS = 'academic_levels:list'

class GetAcademicLevels(MethodView):
    def get(self) -> tuple[Any, int]:
        try:
            raw = cache_get(CACHE_KEY_ACADEMIC_LEVELS)
            if raw is not None and isinstance(raw, (str, bytes, bytearray)):
                return success_response(
                    json.loads(raw),
                    "Academic levels fetched successfully"
                )
            
            academic_levels = get_services().academic_level.list_academic_levels()
            academic_levels_data = [asdict(academic_level) for academic_level in academic_levels]
            
            cache_set(
                CACHE_KEY_ACADEMIC_LEVELS, CACHE_TTL,
                json.dumps(academic_levels_data)
            )

            return success_response(
                academic_levels_data,
                "Academic levels fetched successfully"
            )

        except Exception as e:
            logger.error(f"Error fetching academic levels: {str(e)}")
            return error_response("Failed to fetch academic levels", status=500)
