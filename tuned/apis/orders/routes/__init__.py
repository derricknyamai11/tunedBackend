from __future__ import annotations

from datetime import timedelta, datetime, timezone
from typing import Any

from flask import request
from flask.views import MethodView
from tuned.utils.auth.decorators import combined_auth_check
from flask import g
from marshmallow import Schema, fields, validate, ValidationError

from tuned.extensions import db
from tuned.models.order import Order
from tuned.models.service import Service, AcademicLevel, Deadline
from tuned.models.enums import OrderStatus, Currency
from tuned.utils.responses import success_response, error_response, validation_error_response
from tuned.utils.orders import generate_public_order_number
from tuned.core.logging import get_logger

logger = get_logger(__name__)


class CreateOrderSchema(Schema):
    service_id = fields.Str(required=True)
    academic_level_id = fields.Str(required=True)
    deadline_id = fields.Str(required=True)
    title = fields.Str(required=True, validate=validate.Length(min=3, max=255))
    description = fields.Str(required=True, validate=validate.Length(min=10))
    word_count = fields.Int(required=True, validate=validate.Range(min=1))
    format_style = fields.Str(load_default=None, allow_none=True)
    report_type = fields.Str(load_default=None, allow_none=True)
    additional_materials = fields.Str(load_default=None, allow_none=True)
    currency = fields.Str(load_default="USD", validate=validate.OneOf([c.value for c in Currency]))


class OrderListView(MethodView):
    decorators = [combined_auth_check(require_admin=False)]

    def get(self) -> tuple[Any, int]:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 10, type=int), 50)
        status_filter = request.args.get('status', '').strip()

        query = Order.query.filter_by(client_id=g.current_user.id)
        if status_filter:
            try:
                query = query.filter_by(status=OrderStatus(status_filter))
            except ValueError:
                return error_response(f'Invalid status: {status_filter}', status=400)

        pagination = query.order_by(Order.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )

        return success_response({
            'orders': [
                {
                    'id': str(o.id),
                    'order_number': o.order_number,
                    'title': o.title,
                    'status': o.status.value,
                    'paid': o.paid,
                    'total_price': float(o.total_price),
                    'currency': o.currency.value,
                    'word_count': o.word_count,
                    'due_date': o.due_date.isoformat() if o.due_date else None,
                    'created_at': o.created_at.isoformat(),
                    'is_delivered': o.is_delivered,
                }
                for o in pagination.items
            ],
            'total': pagination.total,
            'pages': pagination.pages,
            'current_page': page,
        })

    def post(self) -> tuple[Any, int]:
        try:
            data = CreateOrderSchema().load(request.get_json(silent=True) or {})
        except ValidationError as e:
            return validation_error_response(e.messages)

        service = Service.query.get(data['service_id'])
        if not service or service.is_deleted:
            return error_response('Service not found', status=404)

        academic_level = AcademicLevel.query.get(data['academic_level_id'])
        if not academic_level:
            return error_response('Academic level not found', status=404)

        deadline = Deadline.query.get(data['deadline_id'])
        if not deadline:
            return error_response('Deadline not found', status=404)

        words_per_page = 275
        page_count = round(data['word_count'] / words_per_page, 2)

        from tuned.models.price import PriceRate
        price_rate = PriceRate.query.filter_by(
            pricing_category_id=service.pricing_category_id,
            academic_level_id=data['academic_level_id'],
            deadline_id=data['deadline_id'],
            is_active=True,
        ).first()

        if price_rate:
            price_per_page = float(price_rate.price_per_page)
        else:
            price_per_page = 10.0

        subtotal = round(page_count * price_per_page, 2)
        total_price = subtotal

        due_date = datetime.now(timezone.utc) + timedelta(hours=deadline.hours)

        order = Order(
            client_id=g.current_user.id,
            service_id=data['service_id'],
            academic_level_id=data['academic_level_id'],
            deadline_id=data['deadline_id'],
            title=data['title'],
            description=data['description'],
            word_count=data['word_count'],
            page_count=page_count,
            format_style=data.get('format_style'),
            report_type=data.get('report_type'),
            additional_materials=data.get('additional_materials'),
            total_price=total_price,
            subtotal=subtotal,
            price_per_page=price_per_page,
            currency=Currency(data.get('currency', 'USD')),
            due_date=due_date,
        )

        db.session.add(order)
        db.session.flush()
        order.order_number = generate_public_order_number(db.session)
        db.session.commit()

        logger.info(f'Order {order.order_number} created by user {g.current_user.id}')

        return success_response(
            {
                'id': str(order.id),
                'order_number': order.order_number,
                'title': order.title,
                'status': order.status.value,
                'total_price': float(order.total_price),
                'currency': order.currency.value,
                'due_date': order.due_date.isoformat() if order.due_date else None,
                'created_at': order.created_at.isoformat(),
            },
            status=201,
        )


class OrderDetailView(MethodView):
    decorators = [combined_auth_check(require_admin=False)]

    def get(self, order_id: str) -> tuple[Any, int]:
        order = Order.query.filter_by(id=order_id, client_id=g.current_user.id).first()
        if not order:
            return error_response('Order not found', status=404)

        return success_response({
            'id': str(order.id),
            'order_number': order.order_number,
            'title': order.title,
            'description': order.description,
            'status': order.status.value,
            'paid': order.paid,
            'total_price': float(order.total_price),
            'subtotal': float(order.subtotal),
            'discount_amount': float(order.discount_amount or 0),
            'currency': order.currency.value,
            'word_count': order.word_count,
            'page_count': float(order.page_count),
            'format_style': order.format_style,
            'report_type': order.report_type,
            'additional_materials': order.additional_materials,
            'due_date': order.due_date.isoformat() if order.due_date else None,
            'delivered_at': order.delivered_at.isoformat() if order.delivered_at else None,
            'is_delivered': order.is_delivered,
            'extension_requested': order.extension_requested,
            'created_at': order.created_at.isoformat(),
            'updated_at': order.updated_at.isoformat(),
            'service': {
                'id': str(order.service.id),
                'name': order.service.name,
            } if order.service else None,
            'academic_level': {
                'id': str(order.academic_level.id),
                'name': order.academic_level.name,
            } if order.academic_level else None,
            'deadline': {
                'id': str(order.deadline.id),
                'name': order.deadline.name,
                'hours': order.deadline.hours,
            } if order.deadline else None,
        })


class OrderCancelView(MethodView):
    decorators = [combined_auth_check(require_admin=False)]

    def post(self, order_id: str) -> tuple[Any, int]:
        order = Order.query.filter_by(id=order_id, client_id=g.current_user.id).first()
        if not order:
            return error_response('Order not found', status=404)

        cancelable = (OrderStatus.PENDING, OrderStatus.ACTIVE)
        if order.status not in cancelable:
            return error_response(
                f'Cannot cancel order with status "{order.status.value}".',
                status=422,
            )

        try:
            order.status = OrderStatus.CANCELED
            db.session.commit()
        except ValueError as e:
            db.session.rollback()
            return error_response("Invalid status transition.", status=422)

        return success_response({'message': f'Order {order.order_number} cancelled'})


class OrderSubmitView(MethodView):
    """Mark a pending order as active (submitted for processing)."""
    decorators = [combined_auth_check(require_admin=False)]

    def post(self, order_id: str) -> tuple[Any, int]:
        order = Order.query.filter_by(id=order_id, client_id=g.current_user.id).first()
        if not order:
            return error_response('Order not found', status=404)

        if order.status != OrderStatus.PENDING:
            return error_response(
                f'Only pending orders can be submitted. Current status: "{order.status.value}".',
                status=422,
            )

        try:
            order.status = OrderStatus.ACTIVE
            db.session.commit()
        except ValueError as e:
            db.session.rollback()
            return error_response("Invalid status transition.", status=422)

        logger.info(f'Order {order.order_number} submitted by user {g.current_user.id}')
        return success_response({
            'message': f'Order {order.order_number} submitted successfully',
            'order_number': order.order_number,
            'status': order.status.value,
        })


ORDER_ROUTES: list[dict] = [
    {
        'url_rule': '/orders',
        'view_func': OrderListView.as_view('order_list'),
        'methods': ['GET', 'POST'],
    },
    {
        'url_rule': '/orders/<string:order_id>',
        'view_func': OrderDetailView.as_view('order_detail'),
        'methods': ['GET'],
    },
    {
        'url_rule': '/orders/<string:order_id>/submit',
        'view_func': OrderSubmitView.as_view('order_submit'),
        'methods': ['POST'],
    },
    {
        'url_rule': '/orders/<string:order_id>/cancel',
        'view_func': OrderCancelView.as_view('order_cancel'),
        'methods': ['POST'],
    },
]
