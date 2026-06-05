from __future__ import annotations

from typing import TYPE_CHECKING
from flask import current_app

if TYPE_CHECKING:
    from tuned.interface import Services


def get_services() -> Services:
    services = current_app.extensions.get('services')
    if services is None:
        raise RuntimeError("Services not initialized. Was create_app() called?")
    return services  # type: ignore[return-value]
