from functools import wraps
from flask import request, g
from typing import Callable, Any, Optional
import logging

logger = logging.getLogger(__name__)


def _get_redis():
    """Lazy import so test mocks applied to tuned.redis_client are respected."""
    from tuned.redis_client import redis_client  # noqa: PLC0415
    return redis_client

def rate_limit(
    max_requests: int = 5,
    window: int = 60,
    key_prefix: str = 'rate_limit',
    fail_open: bool = False,   # True = allow through on Redis error; False = block
) -> Callable[..., Any]:
    """Rate-limit a view.

    When Redis is unavailable the decorator defaults to BLOCKING (fail_open=False)
    for security-sensitive endpoints such as login/register.  Pass fail_open=True
    only for non-security-critical endpoints where availability matters more.
    """
    def decorator(f: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(f)
        def wrapped(*args: Any, **kwargs: Any) -> Any:
            if hasattr(g, 'current_user') and g.current_user:
                client_id = f"user:{g.current_user.id}"
            else:
                client_id = f"ip:{request.remote_addr}"

            key = f"{key_prefix}:{f.__name__}:{client_id}"

            try:
                current: Optional[Any] = _get_redis().get(key)
                if current is None:
                    _get_redis().setex(key, window, 1)
                else:
                    current_val: int = int(current)
                    if current_val >= max_requests:
                        from tuned.utils.responses import error_response
                        return error_response(
                            'Rate limit exceeded. Please try again later.', status=429
                        )
                    _get_redis().incr(key)
            except Exception:
                # In production, fail_open=False blocks to prevent brute force.
                # In development/testing, always allow through (Redis may not be running).
                from flask import current_app
                is_production = current_app.config.get('FLASK_ENV') == 'production'
                effective_fail_open = (not fail_open and is_production) is False

                if not effective_fail_open:
                    from tuned.utils.responses import error_response
                    logger.warning(
                        'Rate limiter Redis unavailable for key=%s — blocking (production)',
                        key,
                    )
                    return error_response(
                        'Service temporarily unavailable. Please try again shortly.',
                        status=503,
                    )
                logger.warning(
                    'Rate limiter Redis unavailable for key=%s — allowing (non-production)',
                    key,
                )

            return f(*args, **kwargs)
        return wrapped
    return decorator