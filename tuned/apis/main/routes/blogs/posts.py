# from tuned.apis.main.schemas.blogs import PostByCategorySchema
from flask import request
from flask.views import MethodView
from tuned.utils.dependencies import get_services
from tuned.utils.responses import paginated_response, error_response, validation_error_response, success_response
from tuned.utils.cache import cache_get, cache_set, cache_delete, cache_exists
from tuned.apis.main.schemas import BlogFilterSchema
from tuned.dtos import BlogPostListRequestDTO #, PostByCategoryRequestDTO
from tuned.core.logging import get_logger
from marshmallow import ValidationError

from dataclasses import asdict
import json
import logging
from typing import Any

logger: logging.Logger = get_logger(__name__)

CACHE_KEY = 'blogs:all'
CACHE_TTL = 300

class ListBlogPosts(MethodView):
    def __init__(self) -> None:
        self._schema = BlogFilterSchema()

    def get(self) -> tuple[Any, int]:
        try:
            params = {}
            if request.args:
                params = self._schema.load(request.args)
            
        except ValidationError as err:
            logger.error(f'Validation error: {str(err)}')
            return validation_error_response(err.messages)

        try:
            cache_key = f'{CACHE_KEY}:{json.dumps(params)}'
            raw = cache_get(cache_key)
            if raw is not None and isinstance(raw, (str, bytes, bytearray)):
                logger.debug(f'Returning blogs from cache')
                data = json.loads(raw)
                return paginated_response(
                    items=data.get("blogs", []),
                    page=data.get("page", 1),
                    per_page=data.get("per_page", 12),
                    total=data.get("total", 0)
                    )
            
            blog_req = BlogPostListRequestDTO(**params)
            blogs_dto = get_services().blogs.post.list_published(blog_req)
            data = asdict(blogs_dto)

            cache_set(
                cache_key,
                CACHE_TTL,
                json.dumps(data)
            )
            
            return paginated_response(
                items=data.get("blogs", []),
                page=data.get("page", 1),
                per_page=data.get("per_page", 12),
                total=data.get("total", 0)
                )
        except Exception as e:
            logger.error(f'Error fetching blogs: {str(e)}')
            return error_response('Failed to fetch blogs', status=500)

class GetBlogPost(MethodView):

    def get(self, slug: str) -> tuple[Any, int]:
        try:
            raw = cache_get(f'blog:{slug}')
            if raw is not None and isinstance(raw, (str, bytes, bytearray)):
                logger.debug('Returning blog from cache')
                return success_response(json.loads(raw))
            
            blog_dto = get_services().blogs.post.get_by_slug(slug)
            data = asdict(blog_dto)

            cache_set(
                f'blog:{slug}',
                CACHE_TTL,
                json.dumps(data)
            )
            
            return success_response(data)
        except Exception as e:
            logger.error(f'Error fetching blog: {str(e)}')
            return error_response('Failed to fetch blog post details', status=500)

class GetRelatedBlogPosts(MethodView):

    def get(self, slug: str) -> tuple[Any, int]:
        try:
            raw = cache_get(f'blog:{slug}:related')
            if raw is not None and isinstance(raw, (str, bytes, bytearray)):
                logger.debug('Returning blogs from cache')
                return success_response(json.loads(raw))

            related_blogs = get_services().blogs.post.get_related(slug)
            data = [asdict(b) for b in related_blogs]

            cache_set(
                f'blog:{slug}:related',
                CACHE_TTL,
                json.dumps(data)
            )
            
            return success_response(data)
        except Exception as e:
            logger.error(f'Error fetching related blogs: {str(e)}')
            return error_response('Failed to fetch related blogs', status=500)