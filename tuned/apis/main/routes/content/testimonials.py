from flask import request
from flask.views import MethodView
from tuned.utils.dependencies import get_services
from tuned.utils.responses import (
    success_response,
    error_response,
    paginated_response
)
from tuned.utils.cache import cache_get, cache_set
from tuned.dtos.content import TestimonialListRequestDTO
from tuned.apis.main.schemas import TestimonialListSchema
from tuned.core.logging import get_logger
from dataclasses import asdict
import json
import logging
from typing import Any

logger: logging.Logger = get_logger(__name__)

CACHE_KEY_PREFIX = 'testimonials'
CACHE_TTL = 900  # 15 minutes


class TestimonialsView(MethodView):
    def get(self) -> tuple[Any, int]:
        try:
            validated_data = TestimonialListSchema().load(request.args)
            service_id = validated_data.get('service_id')
            page = validated_data.get('page')
            per_page = validated_data.get('per_page')

            cache_key = f'{CACHE_KEY_PREFIX}:service_{service_id}:page_{page}:per_{per_page}'

            raw = cache_get(cache_key)
            if raw is not None and isinstance(raw, (str, bytes, bytearray)):
                cached = json.loads(raw)
                return paginated_response(
                    items=cached['items'],
                    page=cached['page'],
                    per_page=cached['per_page'],
                    total=cached['total'],
                )

            req_dto = TestimonialListRequestDTO(
                service_id=service_id,
                page=page,
                per_page=per_page,
            )

            paginated_dto = get_services().testimonial.list_approved_paginated(req_dto)

            items = [asdict(t) for t in paginated_dto.testimonials]
            total = paginated_dto.total

            cache_set(
                cache_key,
                CACHE_TTL,
                json.dumps({'items': items, 'page': page, 'per_page': per_page, 'total': total}),
            )

            return paginated_response(items=items, page=page, per_page=per_page, total=total)

        except Exception as e:
            logger.error(f'Error fetching testimonials: {str(e)}')
            return error_response('Failed to fetch testimonials', status=500)
