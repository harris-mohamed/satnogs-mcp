"""FastMCP server exposing SatNOGS DB and Network APIs as MCP tools.

Start with:
    python -m satnogs_mcp
or:
    satnogs-mcp
"""

from __future__ import annotations

import math
import os
from typing import Any

from fastmcp import FastMCP

from .cache import Cache
from .client import db_client, network_client

mcp = FastMCP("satnogs-mcp")

# Module-level cache singleton
_cache = Cache()

# ---------------------------------------------------------------------------
# TTL constants (seconds)
# ---------------------------------------------------------------------------
TTL_SATELLITES = 6 * 3600       # 6 hours
TTL_TRANSMITTERS = 6 * 3600     # 6 hours
TTL_MODES = 24 * 3600           # 24 hours
TTL_TLE = 3600                  # 1 hour
TTL_TELEMETRY = 15 * 60         # 15 minutes
TTL_STATIONS = 3600             # 1 hour
TTL_OBSERVATIONS = 5 * 60       # 5 minutes
TTL_JOBS = 2 * 60               # 2 minutes
TTL_ARTIFACTS = 24 * 3600       # 24 hours


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_params(**kwargs: Any) -> dict[str, Any]:
    """Build a query-param dict, omitting None values."""
    return {k: v for k, v in kwargs.items() if v is not None}


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return great-circle distance in kilometres between two lat/lon points."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ===========================================================================
# SatNOGS DB tools
# ===========================================================================


@mcp.tool()
def search_satellites(
    name: str | None = None,
    norad_cat_id: int | None = None,
    status: str | None = None,
    country: str | None = None,
    operator: str | None = None,
    page: int | None = None,
    page_size: int | None = None,
) -> Any:
    """Search the SatNOGS DB satellite catalogue.

    Args:
        name: Filter by satellite name (partial match supported).
        norad_cat_id: Filter by NORAD catalogue number.
        status: Filter by operational status (e.g. 'alive', 'dead', 're-entered').
        country: Filter by country of origin (ISO 3166-1 alpha-2, e.g. 'US').
        operator: Filter by operator name.
        page: Page number for pagination (default 1).
        page_size: Results per page (default 25, max 100).

    Returns:
        List of satellite objects from the SatNOGS DB catalogue.
    """
    params = _build_params(
        name=name,
        norad_cat_id=norad_cat_id,
        status=status,
        country=country,
        operator=operator,
        page=page,
        page_size=page_size,
    )
    cache_key = f"db:satellites:{sorted(params.items())}"
    return _cache.get_or_fetch(cache_key, lambda: db_client.get_satellites(params), TTL_SATELLITES)


@mcp.tool()
def get_satellite(sat_id: str) -> Any:
    """Get full details for a single satellite by its SatNOGS DB identifier.

    Args:
        sat_id: The SatNOGS DB satellite ID (e.g. 'FUNCUBE-1' or integer ID).

    Returns:
        Satellite detail object including name, NORAD ID, launch date, status,
        country, operator, links, and more.
    """
    cache_key = f"db:satellite:{sat_id}"
    return _cache.get_or_fetch(cache_key, lambda: db_client.get_satellite(sat_id), TTL_SATELLITES)


@mcp.tool()
def get_transmitters(
    satellite_norad_cat_id: int | None = None,
    sat_id: str | None = None,
    status: str | None = None,
    type: str | None = None,
    mode: str | None = None,
    page: int | None = None,
    page_size: int | None = None,
) -> Any:
    """Retrieve transmitter records from SatNOGS DB.

    Args:
        satellite_norad_cat_id: Filter by NORAD catalogue number.
        sat_id: Filter by SatNOGS DB satellite ID.
        status: Filter by transmitter status ('active', 'inactive', 'invalid').
        type: Filter by type ('Transmitter', 'Transceiver', 'Transponder').
        mode: Filter by modulation mode name (e.g. 'FM', 'AFSK').
        page: Page number for pagination.
        page_size: Results per page.

    Returns:
        List of transmitter objects with frequency, mode, polarisation, and status.
    """
    params = _build_params(
        satellite_norad_cat_id=satellite_norad_cat_id,
        sat_id=sat_id,
        status=status,
        type=type,
        mode=mode,
        page=page,
        page_size=page_size,
    )
    cache_key = f"db:transmitters:{sorted(params.items())}"
    return _cache.get_or_fetch(
        cache_key, lambda: db_client.get_transmitters(params), TTL_TRANSMITTERS
    )


@mcp.tool()
def get_transmitter(uuid: str) -> Any:
    """Get full details for a single transmitter by its UUID.

    Args:
        uuid: The UUID of the transmitter (e.g. 'abc12345-...').

    Returns:
        Transmitter detail object including frequency, mode, status, and links.
    """
    cache_key = f"db:transmitter:{uuid}"
    return _cache.get_or_fetch(
        cache_key, lambda: db_client.get_transmitter(uuid), TTL_TRANSMITTERS
    )


@mcp.tool()
def get_tle(
    norad_cat_id: int | None = None,
    sat_id: str | None = None,
    page: int | None = None,
    page_size: int | None = None,
) -> Any:
    """Retrieve current Two-Line Element (TLE) sets from SatNOGS DB.

    Args:
        norad_cat_id: Filter by NORAD catalogue number.
        sat_id: Filter by SatNOGS DB satellite ID.
        page: Page number for pagination.
        page_size: Results per page.

    Returns:
        List of TLE objects each containing tle0 (name line), tle1, tle2,
        and associated satellite identifiers.
    """
    params = _build_params(
        norad_cat_id=norad_cat_id,
        sat_id=sat_id,
        page=page,
        page_size=page_size,
    )
    cache_key = f"db:tle:{sorted(params.items())}"
    return _cache.get_or_fetch(cache_key, lambda: db_client.get_tle(params), TTL_TLE)


@mcp.tool()
def get_telemetry(
    sat_id: str | None = None,
    satellite_norad_cat_id: int | None = None,
    start: str | None = None,
    end: str | None = None,
    page: int | None = None,
    page_size: int | None = None,
) -> Any:
    """Retrieve decoded telemetry frames from SatNOGS DB.

    Args:
        sat_id: Filter by SatNOGS DB satellite ID.
        satellite_norad_cat_id: Filter by NORAD catalogue number.
        start: ISO 8601 start datetime (e.g. '2024-01-01T00:00:00Z').
        end: ISO 8601 end datetime (e.g. '2024-01-02T00:00:00Z').
        page: Page number for pagination.
        page_size: Results per page.

    Returns:
        List of telemetry frame objects containing decoded data and observation links.
    """
    params = _build_params(
        sat_id=sat_id,
        satellite_norad_cat_id=satellite_norad_cat_id,
        start=start,
        end=end,
        page=page,
        page_size=page_size,
    )
    cache_key = f"db:telemetry:{sorted(params.items())}"
    return _cache.get_or_fetch(cache_key, lambda: db_client.get_telemetry(params), TTL_TELEMETRY)


@mcp.tool()
def get_modes(
    page: int | None = None,
    page_size: int | None = None,
) -> Any:
    """List all communication modes defined in SatNOGS DB.

    Args:
        page: Page number for pagination.
        page_size: Results per page.

    Returns:
        List of mode objects with id and name (e.g. 'FM', 'CW', 'BPSK').
    """
    params = _build_params(page=page, page_size=page_size)
    cache_key = f"db:modes:{sorted(params.items())}"
    return _cache.get_or_fetch(cache_key, lambda: db_client.get_modes(params), TTL_MODES)


@mcp.tool()
def get_artifacts(
    observation: int | None = None,
    page: int | None = None,
    page_size: int | None = None,
) -> Any:
    """Retrieve reference artifacts from SatNOGS DB, optionally filtered by observation.

    Args:
        observation: Filter by SatNOGS Network observation ID.
        page: Page number for pagination.
        page_size: Results per page.

    Returns:
        List of artifact objects with download URLs and metadata.
    """
    params = _build_params(observation=observation, page=page, page_size=page_size)
    cache_key = f"db:artifacts:{sorted(params.items())}"
    return _cache.get_or_fetch(cache_key, lambda: db_client.get_artifacts(params), TTL_ARTIFACTS)


# ===========================================================================
# SatNOGS Network tools
# ===========================================================================


@mcp.tool()
def list_stations(
    status: str | None = None,
    min_horizon: float | None = None,
    page: int | None = None,
    page_size: int | None = None,
) -> Any:
    """List SatNOGS ground stations with location and antenna details.

    Args:
        status: Filter by station status ('Online', 'Testing', 'Offline').
        min_horizon: Minimum elevation angle (degrees) for antenna horizon filter.
        page: Page number for pagination.
        page_size: Results per page.

    Returns:
        List of ground station objects including id, name, lat, lng, altitude,
        antenna types, status, and contact info.
    """
    params = _build_params(status=status, min_horizon=min_horizon, page=page, page_size=page_size)
    cache_key = f"network:stations:{sorted(params.items())}"
    return _cache.get_or_fetch(
        cache_key, lambda: network_client.get_stations(params), TTL_STATIONS
    )


@mcp.tool()
def get_station(station_id: int) -> Any:
    """Get full details for a single SatNOGS ground station.

    Args:
        station_id: Numeric station ID (e.g. 1 for the first registered station).

    Returns:
        Ground station detail object including location, antenna inventory,
        observation statistics, and contact information.
    """
    cache_key = f"network:station:{station_id}"
    return _cache.get_or_fetch(
        cache_key, lambda: network_client.get_station(station_id), TTL_STATIONS
    )


@mcp.tool()
def find_nearby_stations(
    lat: float,
    lon: float,
    radius_km: float = 500.0,
    status: str | None = None,
) -> list[dict[str, Any]]:
    """Find SatNOGS ground stations within a given radius of a coordinate.

    Distance is computed using the Haversine formula (no external library needed).

    Args:
        lat: Latitude of the centre point in decimal degrees (-90 to 90).
        lon: Longitude of the centre point in decimal degrees (-180 to 180).
        radius_km: Search radius in kilometres (default 500 km).
        status: Optionally filter by station status ('Online', 'Testing', 'Offline').

    Returns:
        List of station objects sorted by ascending distance, each augmented with
        a 'distance_km' field showing how far the station is from the query point.
    """
    # Fetch all stations (leverages cache)
    params = _build_params(status=status)
    cache_key = f"network:stations:{sorted(params.items())}"
    all_stations = _cache.get_or_fetch(
        cache_key, lambda: network_client.get_stations(params), TTL_STATIONS
    )

    # The API may return a paginated dict or a plain list
    if isinstance(all_stations, dict):
        stations_list = all_stations.get("results", [])
    else:
        stations_list = list(all_stations)

    results = []
    for station in stations_list:
        slat = station.get("lat") or station.get("latitude")
        slng = station.get("lng") or station.get("longitude")
        if slat is None or slng is None:
            continue
        dist = _haversine_km(lat, lon, float(slat), float(slng))
        if dist <= radius_km:
            results.append({**station, "distance_km": round(dist, 2)})

    results.sort(key=lambda s: s["distance_km"])
    return results


@mcp.tool()
def list_observations(
    satellite__norad_cat_id: int | None = None,
    ground_station: int | None = None,
    start: str | None = None,
    end: str | None = None,
    status: str | None = None,
    vetted_status: str | None = None,
    page: int | None = None,
    page_size: int | None = None,
) -> Any:
    """List SatNOGS Network observations with optional filters.

    Args:
        satellite__norad_cat_id: Filter by NORAD catalogue number.
        ground_station: Filter by ground station ID.
        start: ISO 8601 start of observation window (e.g. '2024-01-01T00:00:00Z').
        end: ISO 8601 end of observation window.
        status: Filter by observation status ('future', 'good', 'bad', 'failed', 'unknown').
        vetted_status: Filter by vetting status ('unvetted', 'good', 'bad').
        page: Page number for pagination.
        page_size: Results per page.

    Returns:
        List of observation objects including waterfall image URLs, audio URLs,
        demodulated payload URLs, and observation metadata.
    """
    params = _build_params(
        satellite__norad_cat_id=satellite__norad_cat_id,
        ground_station=ground_station,
        start=start,
        end=end,
        status=status,
        vetted_status=vetted_status,
        page=page,
        page_size=page_size,
    )
    cache_key = f"network:observations:{sorted(params.items())}"
    return _cache.get_or_fetch(
        cache_key, lambda: network_client.get_observations(params), TTL_OBSERVATIONS
    )


@mcp.tool()
def get_observation(obs_id: int) -> Any:
    """Get full details for a single SatNOGS Network observation.

    Includes waterfall image URL, audio URL, demodulated data URL, and all
    metadata collected during the pass.

    Args:
        obs_id: Numeric observation ID.

    Returns:
        Observation detail object with all data URLs and pass metadata.
    """
    cache_key = f"network:observation:{obs_id}"
    return _cache.get_or_fetch(
        cache_key, lambda: network_client.get_observation(obs_id), TTL_OBSERVATIONS
    )


@mcp.tool()
def list_jobs(
    ground_station: int | None = None,
    page: int | None = None,
    page_size: int | None = None,
) -> Any:
    """List scheduled observation jobs in the SatNOGS Network.

    Args:
        ground_station: Filter by ground station ID.
        page: Page number for pagination.
        page_size: Results per page.

    Returns:
        List of scheduled job objects with start/end times, satellite, and station info.
    """
    params = _build_params(ground_station=ground_station, page=page, page_size=page_size)
    cache_key = f"network:jobs:{sorted(params.items())}"
    return _cache.get_or_fetch(cache_key, lambda: network_client.get_jobs(params), TTL_JOBS)
