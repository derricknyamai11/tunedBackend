from enum import Enum

class PricingCategoryEnum(str, Enum):
    WRITING = "writing"
    TECHNICAL = "technical"
    PROOFREADING = "proofreading"
    
    @classmethod
    def from_string(cls, value: str | None) -> "PricingCategoryEnum":
        if not value:
            raise RuntimeError("Pricing category is None")

        value = value.lower()

        for enum_member in cls:
            if value.startswith(enum_member.value):
                return enum_member

        return cls.TECHNICAL 
