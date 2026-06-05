from __future__ import annotations
from flask import request, g
from flask.views import MethodView
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from tuned.extensions import db
from tuned.utils.responses import success_response, error_response
from tuned.models.user import User
from tuned.models.order import Order
from typing import Any


def writer_required(f):
    from functools import wraps
    @wraps(f)
    def wrapped(*args, **kwargs):
        try:
            verify_jwt_in_request()
            user_id = get_jwt_identity()
            user = User.query.get(str(user_id))
            if not user or not user.is_writer:
                return error_response('Writer access required', status=403)
            g.current_user = user
            return f(*args, **kwargs)
        except Exception:
            return error_response('Authentication required', status=401)
    return wrapped


class WriterOrders(MethodView):
    decorators = [writer_required]
    def get(self) -> tuple[Any, int]:
        user = g.current_user
        status_filter = request.args.get('status', '').strip()
        query = Order.query.filter_by(writer_id=str(user.id))
        if status_filter:
            try:
                from tuned.models.enums import OrderStatus
                query = query.filter_by(status=OrderStatus(status_filter))
            except ValueError:
                pass
        orders = query.order_by(Order.created_at.desc()).all()
        return success_response([{
            'id': str(o.id),
            'order_number': o.order_number,
            'title': o.title,
            'status': o.status.value,
            'due_date': o.due_date.isoformat() if o.due_date else None,
            'total_price': float(o.total_price),
            'word_count': o.word_count,
            'description': o.description,
            'client': {'name': f'{o.client.first_name} {o.client.last_name}'.strip() if o.client else 'Client'},
        } for o in orders])


class WriterProfile(MethodView):
    decorators = [writer_required]
    def get(self) -> tuple[Any, int]:
        user = g.current_user
        from sqlalchemy import func
        order_count = db.session.query(func.count(Order.id)).filter_by(writer_id=str(user.id)).scalar() or 0
        return success_response({
            'id': str(user.id),
            'name': f'{user.first_name} {user.last_name}'.strip(),
            'email': user.email,
            'is_writer': user.is_writer,
            'orders_assigned': order_count,
        })


class WriterOrderDetail(MethodView):
    decorators = [writer_required]
    def get(self, order_id: str) -> tuple[Any, int]:
        user = g.current_user
        order = Order.query.filter_by(id=order_id, writer_id=str(user.id)).first()
        if not order:
            return error_response('Order not found or not assigned to you', status=404)
        return success_response({
            'id': str(order.id),
            'order_number': order.order_number,
            'title': order.title,
            'description': order.description,
            'status': order.status.value,
            'due_date': order.due_date.isoformat() if order.due_date else None,
            'word_count': order.word_count,
            'page_count': float(order.page_count),
            'format_style': order.format_style,
            'additional_materials': order.additional_materials,
        })


WRITER_ROUTES = [
    {'rule': '/profile', 'view_func': WriterProfile.as_view('writer_profile'), 'methods': ['GET']},
    {'rule': '/orders', 'view_func': WriterOrders.as_view('writer_orders'), 'methods': ['GET']},
    {'rule': '/orders/<string:order_id>', 'view_func': WriterOrderDetail.as_view('writer_order_detail'), 'methods': ['GET']},
]
