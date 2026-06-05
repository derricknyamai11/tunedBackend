from flask.views import MethodView
from tuned.utils.dependencies import get_services
from tuned.utils.responses import success_response, error_response
from tuned.utils.cache import cache_get, cache_set
from tuned.core.logging import get_logger

from dataclasses import asdict
import json
import logging
from typing import Any

logger: logging.Logger = get_logger(__name__)

CACHE_KEY = 'homepage:featured'
CACHE_TTL = 300


class GetFeaturedContent(MethodView):
    def get(self) -> tuple[Any, int]:
        try:
            raw = cache_get(CACHE_KEY)
            if raw is not None and isinstance(raw, (str, bytes, bytearray)):
                logger.debug('Returning featured content from cache')
                return success_response(json.loads(raw))

            featured_services = get_services().service_category.list_categories()
            featured_samples = get_services().sample.list_featured_samples()
            featured_blogs = get_services().blogs.post.list_featured()

            data = {
                'services': [asdict(s) for s in featured_services],
                'samples': [asdict(s) for s in featured_samples],
                'blogs': [asdict(b) for b in featured_blogs],
            }

            cache_set(CACHE_KEY, CACHE_TTL, json.dumps(data, default=str))

            return success_response(data)
        except Exception as e:
            logger.error(f'Error fetching featured content: {str(e)}')
            return error_response('Failed to fetch featured content', status=500)
