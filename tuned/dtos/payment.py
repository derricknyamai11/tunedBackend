from __future__ import annotations

from tuned.models import (
    RefundStatus, PaymentStatus, MethodCategory, TransactionType,
    TransactionStatus, DiscountType, Currency
)
from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING
from datetime import datetime
from tuned.dtos.base import BaseDTO

if TYPE_CHECKING:
    from tuned.models.payment import AcceptedPaymentMethod, Payment, Invoice, Transaction, Discount, Refund


@dataclass(kw_only=True)
class AcceptedMethodCreateDTO:
    name: str
    category: MethodCategory
    details: Optional[str] = None
    is_active: Optional[bool] = True

@dataclass(kw_only=True)
class AcceptedMethodUpdateDTO:
    name: Optional[str] = None
    category: Optional[MethodCategory] = None
    details: Optional[str] = None
    is_active: Optional[bool] = None

@dataclass(kw_only=True)
class AcceptedMethodResponseDTO(BaseDTO):
    id: str
    name: str
    category: MethodCategory
    details: Optional[str]
    is_active: bool

    @classmethod
    def from_model(cls, model: "AcceptedPaymentMethod") -> 'AcceptedMethodResponseDTO':
        return cls(
            id=str(model.id),
            name=model.name,
            category=model.category,
            details=model.details,
            is_active=model.is_active,
            created_at=model.created_at,
            updated_at=model.updated_at,
            is_deleted=getattr(model, 'is_deleted', False)
        )

@dataclass(kw_only=True)
class PaymentCreateDTO:
    order_id: str
    user_id: str
    amount: float
    accepted_method_id: int
    status: PaymentStatus = PaymentStatus.PENDING

@dataclass(kw_only=True)
class PaymentClientMarkDTO:
    client_proof_reference: str

@dataclass(kw_only=True)
class PaymentAdminVerifyDTO:
    admin_notes: Optional[str] = None

@dataclass(kw_only=True)
class PaymentUpdateDTO:
    status: Optional[PaymentStatus] = None
    client_proof_reference: Optional[str] = None
    client_marked_paid_at: Optional[datetime] = None
    admin_verified_at: Optional[datetime] = None

@dataclass(kw_only=True)
class PaymentResponseDTO(BaseDTO):
    id: str
    payment_id: str
    order_id: str
    user_id: str
    amount: float
    status: PaymentStatus
    accepted_method_id: int
    currency: Currency
    client_proof_reference: Optional[str]
    client_marked_paid_at: Optional[datetime]
    admin_verified_at: Optional[datetime]
    
    @classmethod
    def from_model(cls, model: "Payment") -> 'PaymentResponseDTO':
        return cls(
            id=str(model.id),
            payment_id=model.payment_id,
            order_id=model.order_id,
            user_id=model.user_id,
            amount=model.amount,
            status=model.status,
            accepted_method_id=model.accepted_method_id,
            currency=model.currency,
            client_proof_reference=model.client_proof_reference,
            client_marked_paid_at=model.client_marked_paid_at,
            admin_verified_at=model.admin_verified_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
            is_deleted=getattr(model, 'is_deleted', False)
        )

@dataclass(kw_only=True)
class InvoiceCreateDTO:
    order_id: str
    user_id: str
    subtotal: float
    total: float
    due_date: datetime
    payment_id: Optional[str] = None
    discount: Optional[float] = 0.0
    tax: Optional[float] = 0.0
    paid: Optional[bool] = False

@dataclass(kw_only=True)
class InvoiceUpdateDTO:
    paid: Optional[bool] = None
    payment_id: Optional[str] = None

@dataclass(kw_only=True)
class InvoiceResponseDTO(BaseDTO):
    id: str
    invoice_number: str
    order_id: str
    user_id: str
    payment_id: Optional[str]
    subtotal: float
    discount: float
    tax: float
    total: float
    due_date: datetime
    paid: bool
    
    @classmethod
    def from_model(cls, model: "Invoice") -> 'InvoiceResponseDTO':
        return cls(
            id=str(model.id),
            invoice_number=model.invoice_number,
            order_id=model.order_id,
            user_id=model.user_id,
            payment_id=model.payment_id,
            subtotal=model.subtotal,
            discount=model.discount,
            tax=model.tax,
            total=model.total,
            due_date=model.due_date,
            paid=model.paid,
            created_at=model.created_at,
            updated_at=model.updated_at,
            is_deleted=getattr(model, 'is_deleted', False)
        )

@dataclass(kw_only=True)
class TransactionCreateDTO:
    payment_id: str
    transaction_id: str
    type: TransactionType
    amount: float
    status: TransactionStatus

@dataclass(kw_only=True)
class TransactionResponseDTO(BaseDTO):
    id: str
    payment_id: str
    transaction_id: str
    type: TransactionType
    amount: float
    status: TransactionStatus
    
    @classmethod
    def from_model(cls, model: "Transaction") -> 'TransactionResponseDTO':
        return cls(
            id=str(model.id),
            payment_id=model.payment_id,
            transaction_id=model.transaction_id,
            type=model.type,
            amount=model.amount,
            status=model.status,
            created_at=model.created_at,
            updated_at=model.updated_at,
            is_deleted=getattr(model, 'is_deleted', False)
        )

@dataclass(kw_only=True)
class DiscountCreateDTO:
    code: str
    amount: float
    discount_type: DiscountType = DiscountType.PERCENTAGE
    description: Optional[str] = None
    min_order_value: Optional[float] = 0.0
    max_discount_value: Optional[float] = None
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None
    usage_limit: Optional[int] = None
    is_active: Optional[bool] = True

@dataclass(kw_only=True)
class DiscountUpdateDTO:
    description: Optional[str] = None
    is_active: Optional[bool] = None
    valid_to: Optional[datetime] = None

@dataclass(kw_only=True)
class DiscountResponseDTO(BaseDTO):
    id: str
    code: str
    description: Optional[str]
    discount_type: DiscountType
    amount: float
    min_order_value: float
    max_discount_value: Optional[float]
    valid_from: Optional[datetime]
    valid_to: Optional[datetime]
    usage_limit: Optional[int]
    times_used: int
    is_active: bool
    
    @classmethod
    def from_model(cls, model: "Discount") -> 'DiscountResponseDTO':
        return cls(
            id=str(model.id),
            code=model.code,
            description=model.description,
            discount_type=model.discount_type,
            amount=model.amount,
            min_order_value=model.min_order_value,
            max_discount_value=model.max_discount_value,
            valid_from=model.valid_from,
            valid_to=model.valid_to,
            usage_limit=model.usage_limit,
            times_used=model.times_used,
            is_active=model.is_active,
            created_at=model.created_at,
            updated_at=model.updated_at,
            is_deleted=getattr(model, 'is_deleted', False)
        )

@dataclass(kw_only=True)
class RefundCreateDTO:
    payment_id: str
    amount: float
    status: RefundStatus = RefundStatus.PENDING
    reason: Optional[str] = None
    processed_by: Optional[str] = None
    admin_reference_id: Optional[str] = None
    refund_date: Optional[datetime] = None

@dataclass(kw_only=True)
class RefundUpdateDTO:
    status: Optional[RefundStatus] = None

@dataclass(kw_only=True)
class RefundResponseDTO(BaseDTO):
    id: str
    payment_id: Optional[str]
    amount: float
    reason: Optional[str]
    status: RefundStatus
    processed_by: Optional[str]
    admin_reference_id: Optional[str]
    refund_date: Optional[datetime]
    
    @classmethod
    def from_model(cls, model: "Refund") -> 'RefundResponseDTO':
        return cls(
            id=str(model.id),
            payment_id=model.payment_id,
            amount=model.amount,
            reason=model.reason,
            status=model.status,
            processed_by=model.processed_by,
            admin_reference_id=model.admin_reference_id,
            refund_date=model.refund_date,
            created_at=model.created_at,
            updated_at=model.updated_at,
            is_deleted=getattr(model, 'is_deleted', False)
        )
