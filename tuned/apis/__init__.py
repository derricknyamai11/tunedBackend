from tuned.apis.main import main_bp
from tuned.apis.auth import auth_bp
from tuned.apis.notifications import notification_bp
from tuned.apis.client import client_bp
from tuned.apis.admin import admin_bp
from tuned.apis.orders import orders_bp
from tuned.apis.writer import writer_bp

__all__ = [
    'main_bp',
    'auth_bp',
    'notification_bp',
    'client_bp',
    'admin_bp',
    'orders_bp',
    'writer_bp',
]