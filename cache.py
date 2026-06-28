import time
from typing import Any

DEFAULT_TTL_SECONDS = 300


class TTLCache:
    """
    Minimal in-memory cache with per-entry time-to-live.

    Each entry stores the cached value together with an absolute expiry
    timestamp: {key: (value, expires_at)}. Expired entries are evicted
    lazily on access.
    """

    def __init__(self, ttl_seconds: int = DEFAULT_TTL_SECONDS):
        self.ttl_seconds = ttl_seconds
        self._store: dict[str, tuple[Any, float]] = {}

    @staticmethod
    def build_key(*parts: Any) -> str:
        """Build a namespaced cache key, e.g. build_key('investigate', 'MSFT', '1D', 30)."""
        return ":".join(str(p) for p in parts)

    def get(self, key: str) -> Any | None:
        """Return the cached value if present and not expired, else None."""
        entry = self._store.get(key)
        if entry is None:
            return None

        value, expires_at = entry
        if time.monotonic() >= expires_at:
            del self._store[key]
            return None
        return value

    def set(self, key: str, value: Any) -> None:
        """Store a value with an expiry of now + ttl_seconds."""
        self._store[key] = (value, time.monotonic() + self.ttl_seconds)

    def clear(self) -> None:
        self._store.clear()
