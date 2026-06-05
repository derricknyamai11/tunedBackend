"""
Simple Redis cache helpers with fast-fail when Redis is unavailable.
Probes Redis on first call; if unavailable, all subsequent calls are no-ops.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

_redis_available: Optional[bool] = None  # None = not yet checked


def _get_rc() -> Any:
    """Return redis_client or None if unavailable, with a 50ms probe."""
    global _redis_available
    try:
        from tuned.redis_client import redis_client
        if _redis_available is False:
            return None
        if _redis_available is None:
            # Probe with a 50ms timeout
            redis_client.ping()
            _redis_available = True
            logger.debug("[cache] Redis is available")
        return redis_client
    except Exception:
        _redis_available = False
        return None


def cache_get(key: str) -> Any:
    rc = _get_rc()
    if rc is None:
        return None
    try:
        return rc.get(key)
    except Exception:
        return None


def cache_set(key: str, ttl: int, value: str) -> None:
    rc = _get_rc()
    if rc is None:
        return
    try:
        rc.setex(key, ttl, value)
    except Exception:
        pass


def cache_delete(key: str) -> None:
    rc = _get_rc()
    if rc is None:
        return
    try:
        rc.delete(key)
    except Exception:
        pass


def cache_exists(key: str) -> bool:
    rc = _get_rc()
    if rc is None:
        return False
    try:
        return bool(rc.exists(key))
    except Exception:
        return False


def reset_cache_probe() -> None:
    """Call this if Redis becomes available after startup."""
    global _redis_available
    _redis_available = None
