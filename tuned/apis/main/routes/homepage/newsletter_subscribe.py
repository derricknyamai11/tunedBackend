from flask import request
from flask.views import MethodView
from tuned.utils.dependencies import get_services
from tuned.utils.responses import (
    success_response,
    error_response,
    validation_error_response,
    created_response
)
from tuned.utils.decorators import rate_limit
from tuned.dtos.communication import NewsletterSubscribeDTO
from tuned.apis.main.schemas import NewsletterSubscribeSchema
from tuned.core.logging import get_logger
from marshmallow import ValidationError
import logging
from typing import Any

logger: logging.Logger = get_logger(__name__)


class NewsletterSubscribeView(MethodView):
    decorators = [rate_limit(max_requests=3, window=3600, fail_open=True)]

    def post(self) -> tuple[Any, int]:
        try:
            schema = NewsletterSubscribeSchema()
            data = schema.load(request.get_json() or {})
        except ValidationError as err:
            return validation_error_response(err.messages)
        
        try:
            subscribe_dto = NewsletterSubscribeDTO(
                email=data['email'],
                name=data.get('name')
            )
            
            result = get_services().newsletter.subscribe(
                data=subscribe_dto,
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent')
            )
            
            # TODO: Check if it was a re-subscription or new
            # If it already existed and just returned it
            # The service handles reactivation logic
            
            # TODO: The service doesn't currently return if it was "new" or "existing"
            # But can check the result created_at vs current time if needed
            # For simplicity, just return success
            
            return success_response(
                {'subscribed': True},
                message='Successfully processed newsletter subscription'
            )
            
        except Exception as e:
            logger.error(f'Error processing newsletter subscription: {str(e)}')
            return error_response('Failed to process subscription', status=500)
