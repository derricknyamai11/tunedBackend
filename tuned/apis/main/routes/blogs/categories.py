from flask import request
from flask.views import MethodView
from tuned.utils.dependencies import get_services
from tuned.utils.responses import error_response, success_response
from tuned.utils.cache import cache_get, cache_set, cache_delete, cache_exists
from tuned.core.logging import get_logger

from dataclasses import asdict
import json
import logging
from typing import Any

logger: logging.Logger = get_logger(__name__)

CACHE_KEY: str = "blog:categories"
CACHE_TTL: int = 60 * 60 * 24

class ListBlogCategories(MethodView):
    def get(self) -> tuple[Any, int]:
        try:
            raw = cache_get(CACHE_KEY)
            if raw is not None and isinstance(raw, (str, bytes, bytearray)):
                logger.debug('Returning blog categories from cache')
                return success_response(json.loads(raw))
            
            categories = get_services().blogs.category.list_categories()
            categories_dict = [asdict(category) for category in categories]
            
            cache_set(
                CACHE_KEY, CACHE_TTL
                , json.dumps(categories_dict))
            
            return success_response(categories_dict)
        except Exception as e:
            logger.error(f'Error fetching blog categories: {str(e)}')
            return error_response('Failed to fetch blog categories', status=500)
            
            
            
                    
            
        
    