"""Abuse and cost guards for POST /generate.

Both are in-memory and per process: with N workers or instances the effective limits are
N times the settings. Fine for the single-instance deployment (Cloud Run max-instances=1).
"""

from collections.abc import Callable
from datetime import UTC, date, datetime

from slowapi import Limiter
from slowapi.util import get_remote_address

# Keyed by client IP. Behind a proxy, uvicorn's --proxy-headers + FORWARDED_ALLOW_IPS make
# request.client the real client instead of the proxy.
limiter = Limiter(key_func=get_remote_address, storage_uri="memory://")

_rate_limit = "10/minute"


def configure_rate_limit(value: str) -> None:
    global _rate_limit
    _rate_limit = value


def current_rate_limit() -> str:
    """Evaluated by slowapi on every request, so the limit follows Settings.rate_limit."""
    return _rate_limit


def _utc_today() -> date:
    return datetime.now(UTC).date()


class DailyCap:
    """Counts /generate calls per UTC day and refuses once `cap` is reached."""

    def __init__(self, cap: int, today: Callable[[], date] = _utc_today) -> None:
        self.cap = cap
        self._today = today
        self._day = today()
        self._count = 0

    def try_acquire(self) -> bool:
        # No await between check and increment, so this is safe on the event loop.
        today = self._today()
        if today != self._day:
            self._day = today
            self._count = 0
        if self._count >= self.cap:
            return False
        self._count += 1
        return True
