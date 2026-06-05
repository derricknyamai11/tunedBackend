from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, List, TYPE_CHECKING
from tuned.models import Service
from tuned.dtos.base import BaseDTO

if TYPE_CHECKING:
    from tuned.models.service import ServiceCategory
from tuned.utils.enums import PricingCategoryEnum
from tuned.dtos.price import PricingCategoryResponseDTO
from tuned.dtos.content import TagResponseDTO

@dataclass
class ServiceDTO:
    name: str
    description: str
    category_id: str
    featured: bool
    pricing_category_id: str
    slug: Optional[str] = None
    is_active: Optional[bool] = True

@dataclass
class ServiceUpdateDTO:
    name: Optional[str] = None
    description: Optional[str] = None
    category_id: Optional[str] = None
    featured: Optional[bool] = None
    pricing_category_id: Optional[str] = None
    slug: Optional[str] = None
    is_active: Optional[bool] = None


@dataclass
class ServiceCategoryDTO:
    name: str
    description: str = ""
    order: int = 0

@dataclass
class ServiceCategoryUpdateDTO:
    name: Optional[str] = None
    description: Optional[str] = None
    order: Optional[int] = None


@dataclass
class ServiceWithPricingCategory:
  id: str
  name: str
  category: str
  pricing_category: PricingCategoryEnum


@dataclass
class ServiceResponseDTO(BaseDTO):
    id: str
    name: str
    description: Optional[str]
    category_id: str
    featured: bool
    pricing_category_id: str
    slug: str
    is_active: bool
    tags: List[TagResponseDTO]
    category: Optional[ServiceCategoryResponseDTO] = None
    pricing_category: Optional[PricingCategoryResponseDTO] = None

    @classmethod
    def from_model(cls, model: "Service") -> "ServiceResponseDTO":
        return cls(
            id=model.id,
            name=model.name,
            description=model.description,
            category_id=model.category_id,
            featured=model.featured,
            pricing_category_id=model.pricing_category_id,
            slug=model.slug,
            is_active=model.is_active,

            category=ServiceCategoryResponseDTO.from_model(model.category) if model.category else None,
            pricing_category=PricingCategoryResponseDTO.from_model(model.pricing_category) if model.pricing_category else None,
            tags=[TagResponseDTO.from_model(tag) for tag in model.tag_list],
        )
@dataclass
class ServiceCategoryResponseDTO(BaseDTO):
    id: str
    name: str
    description: Optional[str]
    order: int

    @classmethod
    def from_model(cls, model: "ServiceCategory") -> "ServiceCategoryResponseDTO":
        return cls(
            id=model.id,
            name=model.name,
            description=model.description,
            order=model.order,
        )
