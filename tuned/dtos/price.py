from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING
from tuned.dtos.content import DeadlineResponseDTO
from datetime import datetime

if TYPE_CHECKING:
    from tuned.models.price import PricingCategory, PriceRate


@dataclass
class PricingCategoryDTO:
    name: str
    description: str = ""
    display_order: int = 0

@dataclass
class PricingCategoryUpdateDTO:
    name: Optional[str] = None
    description: Optional[str] = None
    display_order: Optional[int] = None


@dataclass
class PriceRateDTO:
    pricing_category_id: str
    academic_level_id: str
    deadline_id: str
    price_per_page: float
    is_active: Optional[bool] = True

@dataclass
class PriceRateUpdateDTO:
    pricing_category_id: Optional[str] = None
    academic_level_id: Optional[str] = None
    deadline_id: Optional[str] = None
    price_per_page: Optional[float] = None
    is_active: Optional[bool] = None

@dataclass
class PricingCategoryResponseDTO:
    id: str
    name: str
    description: str
    display_order: int

    @classmethod
    def from_model(cls, obj: "PricingCategory") -> "PricingCategoryResponseDTO":
        return cls(
            id=obj.id,
            name=obj.name,
            description=obj.description or "",
            display_order=obj.display_order,
        )


@dataclass
class PriceRateResponseDTO:
    id: str
    pricing_category_id: str
    academic_level_id: str
    deadline_id: str
    price_per_page: float
    is_active: bool

    @classmethod
    def from_model(cls, obj: "PriceRate") -> "PriceRateResponseDTO":
        return cls(
            id=obj.id,
            pricing_category_id=obj.pricing_category_id,
            academic_level_id=obj.academic_level_id,
            deadline_id=obj.deadline_id,
            price_per_page=obj.price_per_page,
            is_active=obj.is_active,
        )


@dataclass
class PriceRateLookupDTO:
    pricing_category_id: str
    academic_level_id: str
    deadline_id: str


@dataclass
class CalculatePriceRequestDTO:
    deadline: datetime
    pricing_category_id: str
    academic_level_id: str
    word_count: int
    report_type: Optional[str] = None

@dataclass
class CalculatePriceResponseDTO:
    price_per_page: float
    page_count: float
    pages_price: float
    total_price: float
    deadline_hours: float
    selected_deadline: DeadlineResponseDTO

