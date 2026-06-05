from flask.views import MethodView
from tuned.utils.dependencies import get_services
from tuned.utils.responses import success_response, error_response
from tuned.core.logging import get_logger
from tuned.utils.cache import cache_get, cache_set, cache_delete, cache_exists
from dataclasses import asdict
import json
import logging
from typing import Any

logger: logging.Logger = get_logger(__name__)

CACHE_TTL = 300
CACHE_KEY_TAGS = 'tags:list'

class GetTagsList(MethodView):
    def get(self) -> tuple[Any, int]:
        try:
            raw = cache_get(CACHE_KEY_TAGS)
            if raw is not None and isinstance(raw, (str, bytes, bytearray)):
                return success_response(
                    json.loads(raw),
                    "Tags fetched successfully"
                )
            
            tag_dtos = get_services().tag.list_tags(limit=20)
            tag_data = [asdict(tag) for tag in tag_dtos]
            
            cache_set(
                CACHE_KEY_TAGS, CACHE_TTL,
                json.dumps(tag_data)
            )

            return success_response(
                tag_data,
                "Tags fetched successfully"
            )

        except Exception as e:
            logger.error(f"Error fetching tags: {str(e)}")
            return error_response("Failed to fetch tags", status=500)
