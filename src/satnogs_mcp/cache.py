"""Dual-tier cache: Redis (when available) with in-memory fallback.

Usage:
    cache = Cache()
    cache.set("key", value, ttl=300)
    value = cache.get("key")  # None on miss
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# In-memory backend
# ---------------------------------------------------------------------------


class _InMemoryBackend:
    """Simple TTL-aware in-memory store."""

    def __init__(self) -> None:
        self._store: dict[str, tuple[Any, float]] = {}  # key -> (value, expires_at)

    def get(self, key: str) -> Any | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        value, expires_at = entry
        if time.monotonic() > expires_at:
            del self._store[key]
            return None
        return value

    def set(self, key: str, value: Any, ttl: int) -> None:
        self._store[key] = (value, time.monotonic() + ttl)

    def delete(self, key: str) -> None:
        self._store.pop(key, None)

    def clear(self) -> None:
        self._store.clear()


# ---------------------------------------------------------------------------
# Redis backend
# ---------------------------------------------------------------------------


class _RedisBackend:
    """Thin wrapper around a Redis connection."""

    def __init__(self, client: Any) -> None:
        self._client = client

    def get(self, key: str) -> Any | None:
        raw = self._client.get(key)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return None

    def set(self, key: str, value: Any, ttl: int) -> None:
        self._client.setex(key, ttl, json.dumps(value))

    def delete(self, key: str) -> None:
        self._client.delete(key)

    def clear(self) -> None:
        self._client.flushdb()


# ---------------------------------------------------------------------------
# Public Cache class (dual-tier: Redis primary, in-memory fallback)
# ---------------------------------------------------------------------------


class Cache:
    """Dual-tier cache.  Redis is used when ``REDIS_URL`` is set and the
    connection succeeds; otherwise falls back to an in-process TTL dict.
    """

    def __init__(self, redis_url: str | None = None) -> None:
        self._backend = self._init_backend(redis_url or os.getenv("REDIS_URL"))

    # ------------------------------------------------------------------
    # Initialisation helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _init_backend(redis_url: str | None) -> _InMemoryBackend | _RedisBackend:
        if redis_url:
            try:
                import redis  # type: ignore[import-untyped]

                client = redis.from_url(redis_url, socket_connect_timeout=2)
                client.ping()
                logger.info("Cache: using Redis at %s", redis_url)
                return _RedisBackend(client)
            except Exception as exc:  # pragma: no cover
                logger.warning(
                    "Cache: Redis unavailable (%s) — falling back to in-memory", exc
                )
        logger.info("Cache: using in-memory store")
        return _InMemoryBackend()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self, key: str) -> Any | None:
        """Return cached value or *None* on miss/expiry."""
        return self._backend.get(key)

    def set(self, key: str, value: Any, ttl: int) -> None:
        """Store *value* under *key* with a time-to-live in seconds."""
        self._backend.set(key, value, ttl)

    def delete(self, key: str) -> None:
        """Remove a key (no-op if absent)."""
        self._backend.delete(key)

    def clear(self) -> None:
        """Flush the entire cache (use with care in production)."""
        self._backend.clear()

    def get_or_fetch(self, key: str, fetch_fn: Any, ttl: int) -> Any:
        """Return cached value; if missing call *fetch_fn()*, cache, and return."""
        cached = self.get(key)
        if cached is not None:
            return cached
        value = fetch_fn()
        self.set(key, value, ttl)
        return value
