from __future__ import annotations

from dataclasses import dataclass, asdict
from enum import Enum
from typing import Mapping, Optional, Dict, TYPE_CHECKING, TypeAlias, TypeVar, cast
# from datetime import datetime

from tuned.models.enums import (
    DateFormat,
    EmailFrequency,
    InvoiceDeliveryMethod,
    NumberFormat,
    ProfileVisibility,
    TimeFormat,
    WeekStart,
)

if TYPE_CHECKING:
    from tuned.models.preferences import (
        UserLocalizationSettings, UserNotificationPreferences,
        UserEmailPreferences, UserPrivacySettings,
        UserAccessibilityPreferences, UserBillingPreferences
    )


@dataclass
class LocalizationDTO:
    language: str
    country_code: Optional[str]
    timezone: str
    date_format: str
    time_format: str
    currency: str
    number_format: str
    week_start: str

    @classmethod
    def from_model(cls, obj: "UserLocalizationSettings") -> "LocalizationDTO":
        return cls(
            language=obj.language,
            country_code=obj.country_code,
            timezone=obj.timezone,
            date_format=obj.date_format.value if hasattr(obj.date_format, 'value') else obj.date_format,
            time_format=obj.time_format.value if hasattr(obj.time_format, 'value') else obj.time_format,
            currency=obj.currency,
            number_format=obj.number_format.value if hasattr(obj.number_format, 'value') else obj.number_format,
            week_start=obj.week_start.value if hasattr(obj.week_start, 'value') else obj.week_start
        )

@dataclass
class NotificationDTO:
    email_notifications: bool
    sms_notifications: bool
    push_notifications: bool
    order_updates: bool
    payment_notifications: bool
    delivery_notifications: bool
    revision_updates: bool
    extension_updates: bool
    comment_notifications: bool
    support_ticket_updates: bool
    marketing_emails: bool
    weekly_summary: bool

    @classmethod
    def from_model(cls, obj: "UserNotificationPreferences") -> "NotificationDTO":
        return cls(
            email_notifications=obj.email_notifications,
            sms_notifications=obj.sms_notifications,
            push_notifications=obj.push_notifications,
            order_updates=obj.order_updates,
            payment_notifications=obj.payment_notifications,
            delivery_notifications=obj.delivery_notifications,
            revision_updates=obj.revision_updates,
            extension_updates=obj.extension_updates,
            comment_notifications=obj.comment_notifications,
            support_ticket_updates=obj.support_ticket_updates,
            marketing_emails=obj.marketing_emails,
            weekly_summary=obj.weekly_summary
        )

@dataclass
class EmailPreferenceDTO:
    newsletter: bool
    promotional_emails: bool
    product_updates: bool
    order_confirmations: bool
    payment_receipts: bool
    account_security: bool
    frequency: str
    daily_digest_hour: Optional[int]

    @classmethod
    def from_model(cls, obj: "UserEmailPreferences") -> "EmailPreferenceDTO":
        return cls(
            newsletter=obj.newsletter,
            promotional_emails=obj.promotional_emails,
            product_updates=obj.product_updates,
            order_confirmations=obj.order_confirmations,
            payment_receipts=obj.payment_receipts,
            account_security=obj.account_security,
            frequency=obj.frequency.value if hasattr(obj.frequency, 'value') else obj.frequency,
            daily_digest_hour=obj.daily_digest_hour
        )

@dataclass
class PrivacyDTO:
    profile_visibility: str
    show_email: bool
    show_phone: bool
    show_name: bool
    allow_messages: bool
    allow_comments: bool
    data_sharing: bool
    analytics_tracking: bool
    third_party_cookies: bool
    allow_search_engine_indexing: bool

    @classmethod
    def from_model(cls, obj: "UserPrivacySettings") -> "PrivacyDTO":
        return cls(
            profile_visibility=obj.profile_visibility.value if hasattr(obj.profile_visibility, 'value') else obj.profile_visibility,
            show_email=obj.show_email,
            show_phone=obj.show_phone,
            show_name=obj.show_name,
            allow_messages=obj.allow_messages,
            allow_comments=obj.allow_comments,
            data_sharing=obj.data_sharing,
            analytics_tracking=obj.analytics_tracking,
            third_party_cookies=obj.third_party_cookies,
            allow_search_engine_indexing=obj.allow_search_engine_indexing
        )

@dataclass
class AccessibilityDTO:
    font_size_multiplier: float
    text_spacing_increased: bool
    high_contrast_mode: bool
    color_blind_mode: bool
    reduced_motion: bool
    screen_reader_optimized: bool
    keyboard_navigation_enhanced: bool
    focus_indicators_enhanced: bool

    @classmethod
    def from_model(cls, obj: "UserAccessibilityPreferences") -> "AccessibilityDTO":
        return cls(
            font_size_multiplier=float(obj.font_size_multiplier),
            text_spacing_increased=obj.text_spacing_increased,
            high_contrast_mode=obj.high_contrast_mode,
            color_blind_mode=obj.color_blind_mode,
            reduced_motion=obj.reduced_motion,
            screen_reader_optimized=obj.screen_reader_optimized,
            keyboard_navigation_enhanced=obj.keyboard_navigation_enhanced,
            focus_indicators_enhanced=obj.focus_indicators_enhanced
        )

@dataclass
class BillingPreferenceDTO:
    invoice_email: Optional[str]
    invoice_delivery: str
    payment_reminders: bool
    reminder_days_before: int
    auto_reload_enabled: Optional[bool]
    auto_reload_threshold: Optional[float]

    @classmethod
    def from_model(cls, obj: "UserBillingPreferences") -> "BillingPreferenceDTO":
        return cls(
            invoice_email=obj.invoice_email,
            invoice_delivery=obj.invoice_delivery.value if hasattr(obj.invoice_delivery, 'value') else obj.invoice_delivery,
            payment_reminders=obj.payment_reminders,
            reminder_days_before=obj.reminder_days_before,
            auto_reload_enabled=obj.auto_reload_enabled,
            auto_reload_threshold=float(obj.auto_reload_threshold) if obj.auto_reload_threshold else None
        )

@dataclass
class AllPreferencesResponseDTO:
    localization: LocalizationDTO
    notification: NotificationDTO
    email: EmailPreferenceDTO
    privacy: PrivacyDTO
    accessibility: AccessibilityDTO
    billing: BillingPreferenceDTO

    def to_dict(self) -> Dict[str, Dict[str, str | int | float | bool | None]]:
        return {
            "localization": asdict(self.localization),
            "notification": asdict(self.notification),
            "email": asdict(self.email),
            "privacy": asdict(self.privacy),
            "accessibility": asdict(self.accessibility),
            "billing": asdict(self.billing)
        }


PreferenceCategory: TypeAlias = str


@dataclass(kw_only=True)
class PreferenceUpdateDTOBase:
    def to_update_dict(self) -> dict[str, object]:
        return {
            key: value
            for key, value in self.__dict__.items()
            if value is not None
        }


@dataclass(kw_only=True)
class LocalizationUpdateDTO(PreferenceUpdateDTOBase):
    language: Optional[str] = None
    country_code: Optional[str] = None
    timezone: Optional[str] = None
    date_format: Optional[DateFormat] = None
    time_format: Optional[TimeFormat] = None
    currency: Optional[str] = None
    number_format: Optional[NumberFormat] = None
    week_start: Optional[WeekStart] = None


@dataclass(kw_only=True)
class NotificationPreferenceUpdateDTO(PreferenceUpdateDTOBase):
    email_notifications: Optional[bool] = None
    sms_notifications: Optional[bool] = None
    push_notifications: Optional[bool] = None
    order_updates: Optional[bool] = None
    payment_notifications: Optional[bool] = None
    delivery_notifications: Optional[bool] = None
    revision_updates: Optional[bool] = None
    extension_updates: Optional[bool] = None
    comment_notifications: Optional[bool] = None
    support_ticket_updates: Optional[bool] = None
    marketing_emails: Optional[bool] = None
    weekly_summary: Optional[bool] = None


@dataclass(kw_only=True)
class EmailPreferenceUpdateDTO(PreferenceUpdateDTOBase):
    newsletter: Optional[bool] = None
    promotional_emails: Optional[bool] = None
    product_updates: Optional[bool] = None
    frequency: Optional[EmailFrequency] = None
    daily_digest_hour: Optional[int] = None


@dataclass(kw_only=True)
class PrivacyUpdateDTO(PreferenceUpdateDTOBase):
    profile_visibility: Optional[ProfileVisibility] = None
    show_email: Optional[bool] = None
    show_phone: Optional[bool] = None
    show_name: Optional[bool] = None
    allow_messages: Optional[bool] = None
    allow_comments: Optional[bool] = None
    data_sharing: Optional[bool] = None
    analytics_tracking: Optional[bool] = None
    third_party_cookies: Optional[bool] = None
    allow_search_engine_indexing: Optional[bool] = None


@dataclass(kw_only=True)
class AccessibilityUpdateDTO(PreferenceUpdateDTOBase):
    font_size_multiplier: Optional[float] = None
    text_spacing_increased: Optional[bool] = None
    high_contrast_mode: Optional[bool] = None
    color_blind_mode: Optional[bool] = None
    reduced_motion: Optional[bool] = None
    screen_reader_optimized: Optional[bool] = None
    keyboard_navigation_enhanced: Optional[bool] = None
    focus_indicators_enhanced: Optional[bool] = None


@dataclass(kw_only=True)
class BillingPreferenceUpdateDTO(PreferenceUpdateDTOBase):
    invoice_email: Optional[str] = None
    invoice_delivery: Optional[InvoiceDeliveryMethod] = None
    payment_reminders: Optional[bool] = None
    reminder_days_before: Optional[int] = None
    auto_reload_enabled: Optional[bool] = None
    auto_reload_threshold: Optional[float] = None


PreferenceUpdateDTO: TypeAlias = (
    LocalizationUpdateDTO
    | NotificationPreferenceUpdateDTO
    | EmailPreferenceUpdateDTO
    | PrivacyUpdateDTO
    | AccessibilityUpdateDTO
    | BillingPreferenceUpdateDTO
)

PreferenceResponseDTO: TypeAlias = (
    LocalizationDTO
    | NotificationDTO
    | EmailPreferenceDTO
    | PrivacyDTO
    | AccessibilityDTO
    | BillingPreferenceDTO
)

EnumT = TypeVar("EnumT", bound=Enum)


def _optional_enum(value: object, enum_cls: type[EnumT]) -> EnumT | None:
    if value is None:
        return None
    if isinstance(value, enum_cls):
        return value
    return enum_cls(value)


def _optional_str(value: object) -> str | None:
    return cast(str | None, value)


def _optional_bool(value: object) -> bool | None:
    return cast(bool | None, value)


def _optional_int(value: object) -> int | None:
    return cast(int | None, value)


def _optional_float(value: object) -> float | None:
    return cast(float | None, value)


def build_preference_update_dto(
    category: str,
    data: Mapping[str, object],
) -> PreferenceUpdateDTO:
    if category == "localization":
        return LocalizationUpdateDTO(
            language=_optional_str(data.get("language")),
            country_code=_optional_str(data.get("country_code")),
            timezone=_optional_str(data.get("timezone")),
            date_format=_optional_enum(data.get("date_format"), DateFormat),
            time_format=_optional_enum(data.get("time_format"), TimeFormat),
            currency=_optional_str(data.get("currency")),
            number_format=_optional_enum(data.get("number_format"), NumberFormat),
            week_start=_optional_enum(data.get("week_start"), WeekStart),
        )
    if category == "notification":
        return NotificationPreferenceUpdateDTO(
            email_notifications=_optional_bool(data.get("email_notifications")),
            sms_notifications=_optional_bool(data.get("sms_notifications")),
            push_notifications=_optional_bool(data.get("push_notifications")),
            order_updates=_optional_bool(data.get("order_updates")),
            payment_notifications=_optional_bool(data.get("payment_notifications")),
            delivery_notifications=_optional_bool(data.get("delivery_notifications")),
            revision_updates=_optional_bool(data.get("revision_updates")),
            extension_updates=_optional_bool(data.get("extension_updates")),
            comment_notifications=_optional_bool(data.get("comment_notifications")),
            support_ticket_updates=_optional_bool(data.get("support_ticket_updates")),
            marketing_emails=_optional_bool(data.get("marketing_emails")),
            weekly_summary=_optional_bool(data.get("weekly_summary")),
        )
    if category == "email":
        return EmailPreferenceUpdateDTO(
            newsletter=_optional_bool(data.get("newsletter")),
            promotional_emails=_optional_bool(data.get("promotional_emails")),
            product_updates=_optional_bool(data.get("product_updates")),
            frequency=_optional_enum(data.get("frequency"), EmailFrequency),
            daily_digest_hour=_optional_int(data.get("daily_digest_hour")),
        )
    if category == "privacy":
        return PrivacyUpdateDTO(
            profile_visibility=_optional_enum(data.get("profile_visibility"), ProfileVisibility),
            show_email=_optional_bool(data.get("show_email")),
            show_phone=_optional_bool(data.get("show_phone")),
            show_name=_optional_bool(data.get("show_name")),
            allow_messages=_optional_bool(data.get("allow_messages")),
            allow_comments=_optional_bool(data.get("allow_comments")),
            data_sharing=_optional_bool(data.get("data_sharing")),
            analytics_tracking=_optional_bool(data.get("analytics_tracking")),
            third_party_cookies=_optional_bool(data.get("third_party_cookies")),
            allow_search_engine_indexing=_optional_bool(data.get("allow_search_engine_indexing")),
        )
    if category == "accessibility":
        return AccessibilityUpdateDTO(
            font_size_multiplier=_optional_float(data.get("font_size_multiplier")),
            text_spacing_increased=_optional_bool(data.get("text_spacing_increased")),
            high_contrast_mode=_optional_bool(data.get("high_contrast_mode")),
            color_blind_mode=_optional_bool(data.get("color_blind_mode")),
            reduced_motion=_optional_bool(data.get("reduced_motion")),
            screen_reader_optimized=_optional_bool(data.get("screen_reader_optimized")),
            keyboard_navigation_enhanced=_optional_bool(data.get("keyboard_navigation_enhanced")),
            focus_indicators_enhanced=_optional_bool(data.get("focus_indicators_enhanced")),
        )
    if category == "billing":
        return BillingPreferenceUpdateDTO(
            invoice_email=_optional_str(data.get("invoice_email")),
            invoice_delivery=_optional_enum(data.get("invoice_delivery"), InvoiceDeliveryMethod),
            payment_reminders=_optional_bool(data.get("payment_reminders")),
            reminder_days_before=_optional_int(data.get("reminder_days_before")),
            auto_reload_enabled=_optional_bool(data.get("auto_reload_enabled")),
            auto_reload_threshold=_optional_float(data.get("auto_reload_threshold")),
        )
    raise ValueError(f"Invalid preference category: {category}")
