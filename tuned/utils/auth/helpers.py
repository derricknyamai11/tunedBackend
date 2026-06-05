import re
from flask import request

# IPv4 / IPv6 pattern — only log IP addresses, not arbitrary header values
_IPV4_RE = re.compile(r'^(\d{1,3}\.){3}\d{1,3}$')
_IPV6_RE = re.compile(r'^[0-9a-fA-F:]{2,39}$')


def _sanitize_ip(raw: str) -> str:
    """Return IP only if it looks like a valid address; otherwise 'unknown'."""
    cleaned = raw.strip()
    if _IPV4_RE.match(cleaned) or _IPV6_RE.match(cleaned):
        return cleaned
    return 'unknown'


def _sanitize_user_agent(raw: str) -> str:
    """Strip control characters and limit length to prevent log injection."""
    sanitized = re.sub(r'[\r\n\t\x00-\x1f\x7f]', ' ', raw)
    return sanitized[:256]


def get_user_ip() -> str:
    forwarded = request.headers.get('X-Forwarded-For')
    if forwarded:
        raw = forwarded.split(',')[0].strip()
        return _sanitize_ip(raw)

    real_ip = request.headers.get('X-Real-IP')
    if real_ip:
        return _sanitize_ip(real_ip.strip())

    return _sanitize_ip(request.remote_addr or 'unknown')


def get_user_agent() -> str:
    raw = request.headers.get('User-Agent', 'unknown')
    return _sanitize_user_agent(raw)


def is_email_verified_required() -> bool:
    from flask import current_app
    return bool(current_app.config.get('REQUIRE_EMAIL_VERIFICATION', True))
