from tuned.extensions import db
from tuned.models.base import BaseModel
from datetime import datetime, timezone
from tuned.models.enums import OrderStatus, SupportTicketStatus, Currency
from sqlalchemy import event
from sqlalchemy.orm import validates, Mapped, mapped_column, relationship, Session
from tuned.utils.orders import generate_public_order_number
from typing import TYPE_CHECKING, Optional, Any

if TYPE_CHECKING:
    from tuned.models.user import User
    from tuned.models.service import Service, AcademicLevel, Deadline
    from tuned.models.payment import Payment, Invoice, Discount
    from tuned.models.order_delivery import OrderDelivery
    from tuned.models.content import Testimonial
    from tuned.models.revision_request import OrderRevisionRequest
    from tuned.models.deadline_extension import OrderDeadlineExtensionRequest
    from tuned.models.audit import OrderStatusHistory, EmailLog
    from tuned.models.communication import Chat

class Order(BaseModel):
    __tablename__ = 'order'
    order_number: Mapped[str] = mapped_column(db.String(20), unique=True, nullable=False, index=True)
    client_id: Mapped[str] = mapped_column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    writer_id: Mapped[Optional[str]] = mapped_column(db.String(36), db.ForeignKey('users.id'), nullable=True)
    service_id: Mapped[str] = mapped_column(db.String(36), db.ForeignKey('service.id'), nullable=False)
    academic_level_id: Mapped[str] = mapped_column(db.String(36), db.ForeignKey('academic_level.id'), nullable=False)
    deadline_id: Mapped[str] = mapped_column(db.String(36), db.ForeignKey('deadline.id'), nullable=False)
    title: Mapped[str] = mapped_column(db.String(255), nullable=False)
    description: Mapped[str] = mapped_column(db.Text, nullable=False)
    word_count: Mapped[int] = mapped_column(db.Integer, nullable=False)
    page_count: Mapped[float] = mapped_column(db.Float, nullable=False)
    format_style: Mapped[Optional[str]] = mapped_column(db.String(50), nullable=True, default=None)
    report_type: Mapped[Optional[str]] = mapped_column(db.String(50), nullable=True, default=None)
    total_price: Mapped[float] = mapped_column(db.Float, nullable=False)
    status: Mapped[OrderStatus] = mapped_column(db.Enum(OrderStatus), default=OrderStatus.PENDING, nullable=False)
    paid: Mapped[bool] = mapped_column(db.Boolean, default=False, nullable=False)
    delivered_at: Mapped[Optional[datetime]] = mapped_column(db.DateTime, nullable=True, default=None)
    extension_requested: Mapped[bool] = mapped_column(db.Boolean, default=False, nullable=False)
    extension_requested_at: Mapped[Optional[datetime]] = mapped_column(db.DateTime, nullable=True, default=None)
    due_date: Mapped[Optional[datetime]] = mapped_column(db.DateTime, nullable=True, default=None)
    price_per_page: Mapped[float] = mapped_column(db.Float, nullable=False)
    subtotal: Mapped[float] = mapped_column(db.Float, nullable=False)
    discount_amount: Mapped[Optional[float]] = mapped_column(db.Float, nullable=True, default=0.0)
    currency: Mapped[Currency] = mapped_column(db.Enum(Currency), default=Currency.USD, nullable=False)
    additional_materials: Mapped[Optional[str]] = mapped_column(db.Text, nullable=True, default=None)
    
    # Relationships
    client: Mapped["User"] = relationship('User', foreign_keys=[client_id], back_populates='orders')
    writer: Mapped[Optional["User"]] = relationship('User', foreign_keys=[writer_id], backref='assigned_orders', lazy=True)
    service: Mapped["Service"] = relationship('Service', foreign_keys=[service_id], back_populates='orders')
    academic_level: Mapped["AcademicLevel"] = relationship('AcademicLevel', foreign_keys=[academic_level_id], back_populates='orders')
    deadline: Mapped["Deadline"] = relationship('Deadline', foreign_keys=[deadline_id], back_populates='orders')
    testimonials: Mapped[list["Testimonial"]] = relationship('Testimonial', foreign_keys='Testimonial.order_id', back_populates='order', lazy=True, cascade='all, delete-orphan')
    files: Mapped[list["OrderFile"]] = relationship('OrderFile', foreign_keys='OrderFile.order_id', back_populates='order', lazy=True, cascade='all, delete-orphan')
    payments: Mapped[list["Payment"]] = relationship('Payment', foreign_keys='Payment.order_id', back_populates='order', lazy=True, cascade='all, delete-orphan')
    invoice: Mapped[Optional["Invoice"]] = relationship('Invoice', foreign_keys='Invoice.order_id', back_populates='order', uselist=False, cascade='all, delete-orphan')
    comments: Mapped[list["OrderComment"]] = relationship('OrderComment', foreign_keys='OrderComment.order_id', back_populates='order', lazy=True, cascade="all, delete-orphan")
    deliveries: Mapped[list["OrderDelivery"]] = relationship('OrderDelivery', foreign_keys='OrderDelivery.order_id', back_populates='order', lazy=True, cascade="all, delete-orphan")
    discounts: Mapped[list["Discount"]] = relationship('Discount', secondary='order_discount', back_populates='orders')
    chats: Mapped[list["Chat"]] = relationship('Chat', back_populates='order')
    revision_requests: Mapped[list["OrderRevisionRequest"]] = relationship('OrderRevisionRequest', back_populates='order', lazy='dynamic', cascade='all, delete-orphan')
    deadline_extension_requests: Mapped[list["OrderDeadlineExtensionRequest"]] = relationship('OrderDeadlineExtensionRequest', back_populates='order', lazy='dynamic', cascade='all, delete-orphan')
    support_tickets: Mapped[list["SupportTicket"]] = relationship('SupportTicket', back_populates='order')
    status_history: Mapped[list["OrderStatusHistory"]] = relationship('OrderStatusHistory', back_populates='order')
    email_logs: Mapped[list["EmailLog"]] = relationship('EmailLog', back_populates='order')

    __table_args__ = (
        db.Index('ix_order_client_status_created', 'client_id', 'status', 'created_at'),
        db.CheckConstraint('word_count > 0', name='valid_word_count'),
        db.CheckConstraint('page_count > 0', name='valid_page_count'),
        db.CheckConstraint('total_price > 0', name='valid_total_price'),
    )
    
    VALID_STATUS_TRANSITIONS = {
        OrderStatus.PENDING: [OrderStatus.ACTIVE, OrderStatus.CANCELED],
        OrderStatus.ACTIVE: [OrderStatus.COMPLETED_PENDING_REVIEW, OrderStatus.OVERDUE, OrderStatus.CANCELED],
        OrderStatus.COMPLETED_PENDING_REVIEW: [OrderStatus.COMPLETED, OrderStatus.REVISION],
        OrderStatus.REVISION: [OrderStatus.ACTIVE, OrderStatus.COMPLETED_PENDING_REVIEW],
        OrderStatus.OVERDUE: [OrderStatus.ACTIVE, OrderStatus.CANCELED],
        OrderStatus.COMPLETED: [OrderStatus.REVISION], 
        OrderStatus.CANCELED: [], 
    }
    
    @validates('status')
    def validate_status_transition(self, key: str, new_status: OrderStatus) -> OrderStatus:
        if not self.id or not hasattr(self, '_sa_instance_state') or self._sa_instance_state.key is None:
            return new_status
        
        current_status = self.status
        if current_status == new_status:
            return new_status
        
        valid_transitions = self.VALID_STATUS_TRANSITIONS.get(current_status, [])
        if new_status not in valid_transitions:
            raise ValueError(
                f'Invalid status transition from {current_status.value} to {new_status.value}. '
                f'Valid transitions: {[s.value for s in valid_transitions]}'
            )
        return new_status
    
    @property
    def status_color(self: "Order") -> str:
        colors = {
            OrderStatus.PENDING: 'secondary',
            OrderStatus.ACTIVE: 'primary',
            OrderStatus.COMPLETED_PENDING_REVIEW: 'success',
            OrderStatus.COMPLETED: 'success',
            OrderStatus.OVERDUE: 'danger',
            OrderStatus.CANCELED: 'dark',
            OrderStatus.REVISION: 'info',
        }
        return colors.get(self.status, 'warning')
    
    @property
    def latest_delivery(self: "Order") -> Optional["OrderDelivery"]:
        return max(
            (item for item in self.deliveries if item.delivered_at is not None),
            key=lambda x: x.delivered_at,
            default=None
        )

    @property
    def is_delivered(self: "Order") -> bool:
        return self.latest_delivery is not None
        
    def __init__(self: "Order", **kwargs: Any) -> None:
        super().__init__(**kwargs)
        if not self.order_number:
            self.order_number = generate_public_order_number(db.session())
       
    def __repr__(self: "Order") -> str:
        return f'<Order {self.order_number}>'

class OrderSequence(BaseModel):
    __tablename__ = "order_sequences"

    year: Mapped[int] = mapped_column(db.Integer, primary_key=True)
    month: Mapped[int] = mapped_column(db.Integer, primary_key=True)
    value: Mapped[int] = mapped_column(db.Integer, nullable=False, default=0)
    
class OrderFile(BaseModel):
    __tablename__ = 'order_file'
    order_id: Mapped[str] = mapped_column(db.String(36), db.ForeignKey('order.id'), nullable=False)
    filename: Mapped[str] = mapped_column(db.String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(db.String(255), nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    is_from_client: Mapped[bool] = mapped_column(db.Boolean, default=True, nullable=False)
    
    order: Mapped["Order"] = relationship('Order', back_populates='files')

    @property
    def file_size(self) -> int:
        import os
        try:
            return os.path.getsize(self.file_path)
        except (OSError, TypeError):
            return 0
    
    def __repr__(self) -> str:
        return f'<OrderFile {self.filename}>'

class OrderComment(BaseModel):
    __tablename__ = 'order_comment'
    order_id: Mapped[Optional[str]] = mapped_column(db.String(36), db.ForeignKey('order.id'), nullable=True)
    user_id: Mapped[Optional[str]] = mapped_column(db.String(36), db.ForeignKey('users.id'), nullable=True)
    message: Mapped[Optional[str]] = mapped_column(db.Text, nullable=True)
    is_admin: Mapped[bool] = mapped_column(db.Boolean, default=False, nullable=False)
    is_read: Mapped[bool] = mapped_column(db.Boolean, default=False, nullable=False)
    
    user: Mapped[Optional["User"]] = relationship('User', foreign_keys=[user_id], back_populates='order_comments')
    order: Mapped[Optional["Order"]] = relationship('Order', foreign_keys=[order_id], back_populates='comments')
    
    def __repr__(self) -> str:
        return f'<OrderComment {self.id}>'


class SupportTicket(BaseModel):
    __tablename__ = 'support_ticket'
    order_id: Mapped[str] = mapped_column(db.String(36), db.ForeignKey('order.id'), nullable=False)
    user_id: Mapped[str] = mapped_column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    subject: Mapped[str] = mapped_column(db.String(255), nullable=False)
    message: Mapped[str] = mapped_column(db.Text, nullable=False)
    status: Mapped[SupportTicketStatus] = mapped_column(db.Enum(SupportTicketStatus), default=SupportTicketStatus.OPEN, nullable=False)
    
    order: Mapped["Order"] = relationship('Order', foreign_keys=[order_id], back_populates='support_tickets')
    user: Mapped["User"] = relationship('User', foreign_keys=[user_id], back_populates='support_tickets')
    
    def __repr__(self) -> str:
        return f'<SupportTicket {self.id} for Order {self.order_id}>'


@event.listens_for(Order, "before_insert")
def set_public_order_number(connection: Session, target: Order) -> None:
    if target.order_number:
        return
    target.order_number = generate_public_order_number(connection)