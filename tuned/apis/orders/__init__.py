from flask import Blueprint

orders_bp = Blueprint('orders', __name__)

from tuned.apis.orders.routes import ORDER_ROUTES  # noqa: E402

for route in ORDER_ROUTES:
    orders_bp.add_url_rule(
        rule=route['url_rule'],
        view_func=route['view_func'],
        methods=route['methods'],
    )

__all__ = ['orders_bp']
