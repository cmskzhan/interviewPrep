import json
import os
from typing import Any

import redis

DEFAULT_TTL_SECONDS = 300


class TTLCache:
    """
    Redis-backed TTL cache with the same interface as cache.py.

    Each entry is stored as a JSON-serialised string with Redis SETEX,
    so the TTL is managed by Redis itself (no manual expiry checks needed).

    Namespace prefixes isolate each service's keyspace:
        market-data-service  →  TTLCache(namespace="mds")  →  mds:<key>
        strategy-service     →  TTLCache(namespace="stg")  →  stg:<key>

    Requires the REDIS_URL environment variable, injected via Kubernetes Secret.
    Example value: rediss://:<auth-token>@<elasticache-endpoint>:6379
    """

    def __init__(self, namespace: str = "", ttl_seconds: int = DEFAULT_TTL_SECONDS):
        self.ttl_seconds = ttl_seconds
        self._prefix = f"{namespace}:" if namespace else ""
        self._client = redis.Redis.from_url(
            os.environ["REDIS_URL"],
            decode_responses=True,
        )

    def build_key(self, *parts: Any) -> str:
        """Build a namespaced cache key, e.g. build_key('investigate', 'MSFT', '1D', 30)."""
        return self._prefix + ":".join(str(p) for p in parts)

    def get(self, key: str) -> Any | None:
        """Return the cached value if present and not expired, else None."""
        raw = self._client.get(key)
        if raw is None:
            return None
        return json.loads(raw)

    def set(self, key: str, value: Any) -> None:
        """Store a value; Redis handles expiry after ttl_seconds."""
        self._client.setex(key, self.ttl_seconds, json.dumps(value))

    def clear(self) -> None:
        """Delete all keys under this namespace. Use with care in production."""
        if not self._prefix:
            return
        for key in self._client.scan_iter(f"{self._prefix}*"):
            self._client.delete(key)
