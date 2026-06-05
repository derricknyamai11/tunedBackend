from flask import request
from flask.views import MethodView
from marshmallow import ValidationError
from dataclasses import asdict
import json
import logging
from typing import Any, Optional, cast
from datetime import datetime

from tuned.utils.dependencies import get_services
from tuned.apis.main.schemas import CalculatePriceSchema
from tuned.utils.responses import success_response, error_response, validation_error_response
from tuned.utils.cache import cache_get, cache_set, cache_delete, cache_exists
from tuned.dtos import CalculatePriceRequestDTO, ServiceWithPricingCategory
from tuned.utils.enums import PricingCategoryEnum
from tuned.core.logging import get_logger
from tuned.repository.exceptions import DatabaseError, NotFound

logger: logging.Logger = get_logger(__name__)

CACHE_KEY = 'quote:options'
CACHE_TTL = 600

class GetQuoteFormOptions(MethodView):    
    def _build_services_response(self) -> list[ServiceWithPricingCategory]:
        services = get_services().service.list_services()
        services_response: list[ServiceWithPricingCategory] = []
        
        for service in services:
            category_name = service.category.name if service.category else "General"
            pricing_name = (
                (service.pricing_category.name).lower() 
                if service.pricing_category else None
            )

            pricing_enum = PricingCategoryEnum.from_string(pricing_name)
            
            services_response.append(
                ServiceWithPricingCategory(
                    id = service.id,
                    name = service.name,
                    category = category_name,
                    pricing_category = pricing_enum
                )
            )

        return services_response

    def get(self) -> tuple[Any, int]:
        try:
            raw = cache_get(CACHE_KEY)
            if raw is not None and isinstance(raw, (str, bytes, bytearray)):
                logger.debug('Returning quote form options from cache')
                return success_response(json.loads(raw))
            
            services = self._build_services_response()
            academic_levels = get_services().academic_level.list_academic_levels()
            deadlines = get_services().deadline.list_deadlines()

            data = {
                'services': [asdict(s) for s in services],
                'levels': [asdict(a) for a in academic_levels],
                'deadlines': [asdict(d) for d in deadlines],
            }
            
            cache_set(
                CACHE_KEY,
                CACHE_TTL,
                json.dumps(data)
            )
            
            logger.info('Quote form options fetched and cached successfully')
            return success_response(data)
            
        except Exception as e:
            logger.error(f'Error fetching quote form options: {str(e)}')
            return error_response('Failed to fetch form options', status=500)

class CalculatePrice(MethodView):
    def __init__(self) -> None:
        self._schema = CalculatePriceSchema()
    
    def _convert_schema_to_dto(self, data: dict[str, Any]) -> CalculatePriceRequestDTO:
        return CalculatePriceRequestDTO(
            deadline=cast(datetime, data.get('deadline')),
            pricing_category_id=cast(str, data.get('pricing_category_id')),
            academic_level_id=cast(str, data.get('level_id')),
            word_count=cast(int, data.get('word_count')),
            report_type=cast(Optional[str], data.get('report_type'))
        )

    def _get_service_pricing_category(self, service_id: str) -> str:
        try:
            service = get_services().service.get_service(service_id)
            return service.pricing_category_id
        except NotFound:
            raise
        except DatabaseError:
            raise
        except Exception as e:
            logger.error(f"Error while fetching service pricing category: {str(e)}")
            raise RuntimeError("Internal error while fetching service details")
        

    def post(self) -> tuple[Any, int]:
        try:
            data = request.get_json()
            validated_data = self._schema.load(data or {})

            service_pricing_category_id = self._get_service_pricing_category(validated_data['service_id'])
            validated_data['pricing_category_id'] = service_pricing_category_id

            dto = self._convert_schema_to_dto(validated_data)
            price_dto = get_services().price_rate.calculate_price(dto)

            return success_response(asdict(price_dto))

        except ValidationError as err:
            logger.error(f'Validation error in calculate price: {str(err)}')
            return validation_error_response(err.messages)
        except NotFound as e:
            logger.error(f'Resource not found in calculate price: {str(e)}')
            return error_response('Failed to calculate price', status=404)
        except Exception as e:
            logger.error(f'Error calculating price: {str(e)}')
            return error_response('Failed to calculate price', status=500)
