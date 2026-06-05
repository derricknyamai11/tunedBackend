from flask.views import MethodView
from tuned.utils.dependencies import get_services
from tuned.utils.responses import success_response, error_response
from tuned.utils.cache import cache_get, cache_set, cache_delete, cache_exists
from tuned.core.logging import get_logger
from dataclasses import asdict
import json
import logging
from typing import Any

logger: logging.Logger = get_logger(__name__)

CACHE_KEY = 'blogs:comments'
CACHE_TTL = 300

class GetBlogComments(MethodView):
    def get(self, slug: str) -> tuple[Any, int]:
        try:
            raw = cache_get(f'{CACHE_KEY}:{slug}')
            if raw is not None and isinstance(raw, (str, bytes, bytearray)):
                logger.debug('Returning comments from cache')
                return success_response(json.loads(raw))

            # Look up post by slug first
            from tuned.models.blog import BlogPost
            from tuned.extensions import db
            post = db.session.query(BlogPost).filter_by(slug=slug).first()
            if not post:
                return error_response('Blog post not found', status=404)

            all_comments = get_services().blogs.comment.get_blog_comments(str(post.id))
            # Only expose approved comments to the public
            approved = [c for c in all_comments if getattr(c, 'approved', True)]
            data = {
                'comments': [asdict(c) for c in approved]
            }

            cache_set(f'{CACHE_KEY}:{slug}', CACHE_TTL, json.dumps(data, default=str))

            return success_response(data)
        except Exception as e:
            logger.error(f'Error fetching comments: {str(e)}')
            return error_response('Failed to fetch comments', status=500)
