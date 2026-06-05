from datetime import datetime
from flask import url_for 
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from tuned.extensions import db
from tuned.models.base import BaseModel
from tuned.models.communication import ChatMessage, Chat
from tuned.models.enums import GenderEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional, TYPE_CHECKING, Any
import secrets
import string

if TYPE_CHECKING:
    from tuned.models.order import Order
    from tuned.models.referral import Referral
    from tuned.models.communication import Notification
    from tuned.models.content import Testimonial
    from tuned.models.audit import ActivityLog, EmailLog
    from tuned.models.payment import Payment, Invoice, Refund
    from tuned.models.blog import BlogComment, CommentReaction
    from tuned.models.order import OrderComment, SupportTicket
    from tuned.models.preferences.privacy import UserPrivacySettings
    from tuned.models.preferences.notification import UserNotificationPreferences
    from tuned.models.preferences.localization import UserLocalizationSettings
    from tuned.models.preferences.email import UserEmailPreferences
    from tuned.models.preferences.billing import UserBillingPreferences
    from tuned.models.preferences.accessibility import UserAccessibilityPreferences

class User(UserMixin, BaseModel):  # type: ignore[misc]
    __tablename__ = 'users'

    username: Mapped[str] = mapped_column(db.String(64), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(db.String(120), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(db.String(256), nullable=False)

    failed_login_attempts: Mapped[int] = mapped_column(db.Integer, default=0, nullable=False)
    last_failed_login: Mapped[Optional[datetime]] = mapped_column(db.DateTime, nullable=True)

    email_verified: Mapped[bool] = mapped_column(db.Boolean, default=False, nullable=False)
    email_verification_token: Mapped[Optional[str]] = mapped_column(db.String(128), nullable=True, index=True)
    email_verification_token_expires_at: Mapped[Optional[datetime]] = mapped_column(db.DateTime(timezone=True), nullable=True)
    
    first_name: Mapped[str] = mapped_column(db.String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(db.String(100), nullable=False)
    gender: Mapped[Optional[GenderEnum]] = mapped_column(db.Enum(GenderEnum), nullable=True)
    phone_number: Mapped[Optional[str]] = mapped_column(db.String(20), nullable=True)
    profile_pic: Mapped[Optional[str]] = mapped_column(db.String(120), nullable=True, default='default.png')

    is_admin: Mapped[bool] = mapped_column(db.Boolean, default=False, server_default='false', nullable=False)
    is_writer: Mapped[bool] = mapped_column(db.Boolean, default=False, server_default='false', nullable=False)
    wallet_balance: Mapped[float] = mapped_column(db.Float, default=0.0, server_default='0.0', nullable=False)
    is_active: Mapped[bool] = mapped_column(db.Boolean, default=True, server_default='true', nullable=False)

    referral_code: Mapped[Optional[str]] = mapped_column(db.String(10), unique=True, nullable=True) 
    reward_points: Mapped[int] = mapped_column(db.Integer, default=0, nullable=False)

    braintree_customer_id: Mapped[Optional[str]] = mapped_column(db.String(50), nullable=True)

    last_login_at: Mapped[Optional[datetime]] = mapped_column(db.DateTime, nullable=True)
    
    language: Mapped[Optional[str]] = mapped_column(db.String(10), default='en', nullable=True)  # ISO 639-1
    timezone: Mapped[Optional[str]] = mapped_column(db.String(50), default='UTC', nullable=True)  # IANA timezone
    
    # Relationships
    orders: Mapped[list["Order"]] = relationship('Order', foreign_keys='Order.client_id', back_populates='client', lazy=True)
    referrals: Mapped[list["Referral"]] = relationship('Referral', foreign_keys='Referral.referrer_id', back_populates='referrer', lazy=True)
    referred_by: Mapped[list["Referral"]] = relationship('Referral', foreign_keys='Referral.referred_id', back_populates='referred', lazy=True)
    notifications: Mapped[list["Notification"]] = relationship('Notification', foreign_keys="Notification.user_id", back_populates='user', lazy=True)
    testimonials: Mapped[list["Testimonial"]] = relationship('Testimonial', foreign_keys="Testimonial.user_id", back_populates='author', lazy=True, cascade='all, delete-orphan')
    
    activity_logs: Mapped[list["ActivityLog"]] = relationship("ActivityLog", foreign_keys="ActivityLog.user_id", back_populates="user", cascade="all, delete-orphan")
    email_logs: Mapped[list["EmailLog"]] = relationship("EmailLog", foreign_keys="EmailLog.user_id", back_populates="user", cascade="all, delete-orphan")
    
    user_chats: Mapped[list["Chat"]] = relationship('Chat', foreign_keys="Chat.user_id", back_populates='user', lazy=True)
    admin_chats: Mapped[list["Chat"]] = relationship('Chat', foreign_keys="Chat.admin_id", back_populates='admin', lazy=True)
    chat_messages: Mapped[list["ChatMessage"]] = relationship('ChatMessage', foreign_keys="ChatMessage.user_id", back_populates='user', lazy=True)
    
    payments: Mapped[list["Payment"]] = relationship('Payment', foreign_keys="Payment.user_id", back_populates='user', lazy=True)
    invoices: Mapped[list["Invoice"]] = relationship('Invoice', foreign_keys="Invoice.user_id", back_populates='user', lazy=True)
    processed_refunds: Mapped[list["Refund"]] = relationship('Refund', foreign_keys="Refund.processed_by", back_populates='admin', lazy=True)
    
    blog_comments: Mapped[list["BlogComment"]] = relationship('BlogComment', foreign_keys="BlogComment.user_id", back_populates='user', lazy=True)
    comment_reactions: Mapped[list["CommentReaction"]] = relationship('CommentReaction', foreign_keys="CommentReaction.user_id", back_populates='user', lazy=True)
    
    order_comments: Mapped[list["OrderComment"]] = relationship('OrderComment', foreign_keys="OrderComment.user_id", back_populates='user', lazy=True)
    support_tickets: Mapped[list["SupportTicket"]] = relationship('SupportTicket', foreign_keys="SupportTicket.user_id", back_populates='user', lazy=True)

    privacy_settings: Mapped["UserPrivacySettings"] = relationship("UserPrivacySettings", foreign_keys="UserPrivacySettings.user_id", back_populates="user", uselist=False, cascade="all, delete-orphan")
    notification_preferences: Mapped["UserNotificationPreferences"] = relationship("UserNotificationPreferences", foreign_keys="UserNotificationPreferences.user_id", back_populates="user", uselist=False, cascade="all, delete-orphan")
    localization_settings: Mapped["UserLocalizationSettings"] = relationship("UserLocalizationSettings", foreign_keys="UserLocalizationSettings.user_id", back_populates="user", uselist=False, cascade="all, delete-orphan")
    email_preferences: Mapped["UserEmailPreferences"] = relationship("UserEmailPreferences", foreign_keys="UserEmailPreferences.user_id", back_populates="user", uselist=False, cascade="all, delete-orphan")
    billing_preferences: Mapped["UserBillingPreferences"] = relationship("UserBillingPreferences", foreign_keys="UserBillingPreferences.user_id", back_populates="user", uselist=False, cascade="all, delete-orphan")
    accessibility_preferences: Mapped["UserAccessibilityPreferences"] = relationship("UserAccessibilityPreferences", foreign_keys="UserAccessibilityPreferences.user_id", back_populates="user", uselist=False, cascade="all, delete-orphan")

    def __init__(self: 'User', **kwargs: Any) -> None:
        super(User, self).__init__(**kwargs)
        if not self.referral_code:
            self.referral_code = self.generate_referral_code()

    def generate_referral_code(self: 'User') -> str:
        return ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(10))
    
    def set_password(self: 'User', password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self: 'User', password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def get_name(self: 'User') -> str:
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.username
    
    def get_unread_notification_count(self: 'User') -> int:
        count = 0
        if self.notifications:
            for n in self.notifications:
                if n.is_read == False:
                    count += 1
        return count 
    
    def get_unread_message_count(self: 'User') -> int:
        from sqlalchemy import and_, or_
        return db.session.query(ChatMessage).join(Chat).filter(
            and_(
                or_(Chat.user_id == self.id, Chat.admin_id == self.id),
                ChatMessage.user_id != self.id,
                ChatMessage.is_read == False
            )
        ).count()
    
    def get_profile_pic_url(self: 'User') -> str:
        if self.profile_pic and self.profile_pic != 'default.png':
            return url_for('static', filename=f'client/assets/profile_pics/{self.profile_pic}', _external=True)
            
        if self.gender == GenderEnum.FEMALE:
            return url_for('static', filename='ladyDefault.png', _external=True)
        return url_for('static', filename='manDefault.png', _external=True)
    
    def __repr__(self: 'User') -> str:
        return f'<User {self.username}>'
