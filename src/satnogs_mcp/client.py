"""HTTP clients for the SatNOGS DB and Network APIs.

Both clients share the same sliding-window rate-limiter pattern:
  - Max 20 requests/minute, 200 requests/hour per API
  - On HTTP 429, exponential back-off: 4 s → 8 s → 16 s

Module-level singletons (``db_client`` and ``network_client``) are created at
import time so tools share a single session and rate-limiter state.
"""

from __future__ import annotations

import logging
import os
import time
from collections import deque
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Rate limiter
# ---------------------------------------------------------------------------

_BACKOFF_SEQUENCE = (4, 8, 16)  # seconds


class RateLimiter:
    """Sliding-window rate limiter.

    Tracks timestamps of recent requests and blocks (sleep) when either the
    per-minute or per-hour window is full.
    """

    def __init__(self, per_minute: int = 20, per_hour: int = 200) -> None:
        self._per_minute = per_minute
        self._per_hour = per_hour
        self._minute_window: deque[float] = deque()
        self._hour_window: deque[float] = deque()

    def _evict_old(self) -> None:
        now = time.monotonic()
        minute_cutoff = now - 60
        hour_cutoff = now - 3600
        while self._minute_window and self._minute_window[0] < minute_cutoff:
            self._minute_window.popleft()
        while self._hour_window and self._hour_window[0] < hour_cutoff:
            self._hour_window.popleft()

    def acquire(self) -> None:
        """Block until a request slot is available."""
        while True:
            self._evict_old()
            now = time.monotonic()
            if (
                len(self._minute_window) < self._per_minute
                and len(self._hour_window) < self._per_hour
            ):
                self._minute_window.append(now)
                self._hour_window.append(now)
                return
            # Determine how long to wait
            wait = 1.0
            if len(self._minute_window) >= self._per_minute:
                wait = max(wait, self._minute_window[0] + 60 - now + 0.05)
            if len(self._hour_window) >= self._per_hour:
                wait = max(wait, self._hour_window[0] + 3600 - now + 0.05)
            logger.debug("Rate limit reached; sleeping %.2f s", wait)
            time.sleep(wait)


# ---------------------------------------------------------------------------
# Base API client
# ---------------------------------------------------------------------------


class _BaseClient:
    """Shared request logic with rate limiting and 429 back-off."""

    def __init__(self, base_url: str, rate_limiter: RateLimiter) -> None:
        self._base_url = base_url.rstrip("/")
        self._rate_limiter = rate_limiter
        self._session = requests.Session()
        self._session.headers.update(
            {
                "Accept": "application/json",
                "User-Agent": "satnogs-mcp/0.1.0 (+https://github.com/atlas/satnogs-mcp)",
            }
        )

    def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        """Perform a rate-limited GET, retrying on 429."""
        url = f"{self._base_url}/{path.lstrip('/')}"
        for attempt, backoff in enumerate([0] + list(_BACKOFF_SEQUENCE)):
            if backoff:
                logger.warning("HTTP 429 — backing off %d s (attempt %d)", backoff, attempt)
                time.sleep(backoff)
            self._rate_limiter.acquire()
            resp = self._session.get(url, params=params, timeout=30)
            if resp.status_code == 429:
                continue
            resp.raise_for_status()
            return resp.json()
        # Final attempt after max back-off
        self._rate_limiter.acquire()
        resp = self._session.get(url, params=params, timeout=30)
        resp.raise_for_status()
        return resp.json()


# ---------------------------------------------------------------------------
# SatNOGS DB client
# ---------------------------------------------------------------------------

_DB_BASE_URL = "https://db.satnogs.org/api"


class SatNOGSDbClient(_BaseClient):
    """Client for the SatNOGS DB API (db.satnogs.org)."""

    def __init__(self) -> None:
        super().__init__(_DB_BASE_URL, RateLimiter(per_minute=20, per_hour=200))
        api_key = os.getenv("SATNOGS_DB_API_KEY")
        if api_key:
            self._session.headers["Authorization"] = f"Token {api_key}"
            logger.info("SatNOGS DB: authenticated with API key")
        else:
            logger.info("SatNOGS DB: unauthenticated (read-only public access)")

    # ---- satellites -------------------------------------------------------

    def get_satellites(self, params: dict[str, Any] | None = None) -> Any:
        return self._get("/satellites/", params)

    def get_satellite(self, sat_id: str) -> Any:
        return self._get(f"/satellites/{sat_id}/")

    # ---- transmitters -----------------------------------------------------

    def get_transmitters(self, params: dict[str, Any] | None = None) -> Any:
        return self._get("/transmitters/", params)

    def get_transmitter(self, uuid: str) -> Any:
        return self._get(f"/transmitters/{uuid}/")

    # ---- TLEs -------------------------------------------------------------

    def get_tle(self, params: dict[str, Any] | None = None) -> Any:
        return self._get("/tle/", params)

    # ---- telemetry --------------------------------------------------------

    def get_telemetry(self, params: dict[str, Any] | None = None) -> Any:
        return self._get("/telemetry/", params)

    # ---- modes ------------------------------------------------------------

    def get_modes(self, params: dict[str, Any] | None = None) -> Any:
        return self._get("/modes/", params)

    # ---- artifacts --------------------------------------------------------

    def get_artifacts(self, params: dict[str, Any] | None = None) -> Any:
        return self._get("/artifacts/", params)


# ---------------------------------------------------------------------------
# SatNOGS Network client
# ---------------------------------------------------------------------------

_NETWORK_BASE_URL = "https://network.satnogs.org/api"


class SatNOGSNetworkClient(_BaseClient):
    """Client for the SatNOGS Network API (network.satnogs.org)."""

    def __init__(self) -> None:
        super().__init__(_NETWORK_BASE_URL, RateLimiter(per_minute=20, per_hour=200))
        logger.info("SatNOGS Network: public access")

    # ---- stations ---------------------------------------------------------

    def get_stations(self, params: dict[str, Any] | None = None) -> Any:
        return self._get("/stations/", params)

    def get_station(self, station_id: int) -> Any:
        return self._get(f"/stations/{station_id}/")

    # ---- observations -----------------------------------------------------

    def get_observations(self, params: dict[str, Any] | None = None) -> Any:
        return self._get("/observations/", params)

    def get_observation(self, obs_id: int) -> Any:
        return self._get(f"/observations/{obs_id}/")

    # ---- jobs -------------------------------------------------------------

    def get_jobs(self, params: dict[str, Any] | None = None) -> Any:
        return self._get("/jobs/", params)


# ---------------------------------------------------------------------------
# Module-level singletons
# ---------------------------------------------------------------------------

db_client = SatNOGSDbClient()
network_client = SatNOGSNetworkClient()
