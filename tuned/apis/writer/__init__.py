from flask import Blueprint
writer_bp = Blueprint('writer', __name__)
from tuned.apis.writer.routes import WRITER_ROUTES
for route in WRITER_ROUTES:
    writer_bp.add_url_rule(rule=route['rule'], view_func=route['view_func'], methods=route['methods'])
__all__ = ['writer_bp']
