from flask import Blueprint

admin_bp = Blueprint('admin', __name__)

from tuned.apis.admin.routes import ADMIN_ROUTES  # noqa: E402

for route in ADMIN_ROUTES:
    admin_bp.add_url_rule(
        rule=route['url_rule'],
        view_func=route['view_func'],
        methods=route['methods'],
    )

__all__ = ['admin_bp']
