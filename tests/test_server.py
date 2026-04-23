"""Smoke tests for satnogs-mcp tools using mocked HTTP responses."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Fixtures — patch the singleton clients and cache at import time
# ---------------------------------------------------------------------------

MOCK_SATELLITES = [
    {
        "sat_id": "FUNCUBE-1",
        "name": "FUNcube-1",
        "norad_cat_id": 39444,
        "status": "alive",
        "country": "GB",
        "operator": "AMSAT-UK",
    }
]

MOCK_SATELLITE = {
    "sat_id": "FUNCUBE-1",
    "name": "FUNcube-1",
    "norad_cat_id": 39444,
    "status": "alive",
    "country": "GB",
}

MOCK_TRANSMITTERS = [
    {
        "uuid": "abc-123",
        "description": "FUNcube-1 Downlink",
        "alive": True,
        "type": "Transmitter",
        "downlink_low": 145935000,
        "mode": "FM",
        "sat_id": "FUNCUBE-1",
    }
]

MOCK_TRANSMITTER = MOCK_TRANSMITTERS[0]

MOCK_TLE = [
    {
        "tle0": "FUNCUBE-1",
        "tle1": "1 39444U 13066AE  24001.00000000  .00000000  00000-0  00000-0 0  9990",
        "tle2": "2 39444  97.9000 100.0000 0010000 100.0000 260.0000 14.80000000000000",
        "norad_cat_id": 39444,
        "sat_id": "FUNCUBE-1",
    }
]

MOCK_TELEMETRY = [
    {
        "id": 1,
        "sat_id": "FUNCUBE-1",
        "timestamp": "2024-01-01T12:00:00Z",
        "frame": "DEADBEEF",
        "decoded": {"beacon": True},
    }
]

MOCK_MODES = [
    {"id": 1, "name": "FM"},
    {"id": 2, "name": "CW"},
    {"id": 3, "name": "BPSK"},
]

MOCK_ARTIFACTS = [
    {"id": 1, "observation": 12345, "artifact_file": "https://example.com/artifact.h5"}
]

MOCK_STATIONS = [
    {
        "id": 1,
        "name": "Alpha Station",
        "lat": 51.5,
        "lng": -0.1,
        "status": "Online",
        "altitude": 10,
    },
    {
        "id": 2,
        "name": "Far Station",
        "lat": -33.9,
        "lng": 151.2,
        "status": "Online",
        "altitude": 50,
    },
]

MOCK_STATION = MOCK_STATIONS[0]

MOCK_OBSERVATIONS = [
    {
        "id": 12345,
        "start": "2024-01-01T12:00:00Z",
        "end": "2024-01-01T12:15:00Z",
        "ground_station": 1,
        "satellite__norad_cat_id": 39444,
        "waterfall": "https://example.com/waterfall.png",
        "payload": "https://example.com/payload.txt",
        "demoddata": [{"payload_demod": "https://example.com/demod.ogg"}],
        "vetted_status": "good",
        "status": "good",
    }
]

MOCK_OBSERVATION = MOCK_OBSERVATIONS[0]

MOCK_JOBS = [
    {
        "id": 1,
        "start": "2024-01-02T00:00:00Z",
        "end": "2024-01-02T00:15:00Z",
        "ground_station": 1,
        "tle0": "FUNCUBE-1",
    }
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fresh_cache():
    """Return a fresh in-memory Cache instance with no data."""
    from satnogs_mcp.cache import Cache

    c = Cache(redis_url=None)  # force in-memory
    c.clear()
    return c


# ---------------------------------------------------------------------------
# SatNOGS DB tool tests
# ---------------------------------------------------------------------------


class TestSearchSatellites:
    def test_returns_satellite_list(self):
        from satnogs_mcp import server

        cache = _fresh_cache()
        with (
            patch.object(server, "_cache", cache),
            patch.object(server.db_client, "get_satellites", return_value=MOCK_SATELLITES) as mock,
        ):
            result = server.search_satellites(name="FUNcube")
            assert isinstance(result, list)
            assert result[0]["name"] == "FUNcube-1"
            mock.assert_called_once()

    def test_cache_prevents_second_http_call(self):
        from satnogs_mcp import server

        cache = _fresh_cache()
        with (
            patch.object(server, "_cache", cache),
            patch.object(server.db_client, "get_satellites", return_value=MOCK_SATELLITES) as mock,
        ):
            server.search_satellites()
            server.search_satellites()
            assert mock.call_count == 1, "Second call should be served from cache"

    def test_default_params(self):
        from satnogs_mcp import server

        cache = _fresh_cache()
        with (
            patch.object(server, "_cache", cache),
            patch.object(server.db_client, "get_satellites", return_value=[]) as mock,
        ):
            server.search_satellites()
            # Should be called with an empty dict (all params are None)
            mock.assert_called_once_with({})


class TestGetSatellite:
    def test_returns_satellite_detail(self):
        from satnogs_mcp import server

        cache = _fresh_cache()
        with (
            patch.object(server, "_cache", cache),
            patch.object(server.db_client, "get_satellite", return_value=MOCK_SATELLITE) as mock,
        ):
            result = server.get_satellite("FUNCUBE-1")
            assert result["sat_id"] == "FUNCUBE-1"
            mock.assert_called_once_with("FUNCUBE-1")


class TestGetTransmitters:
    def test_returns_transmitter_list(self):
        from satnogs_mcp import server

        cache = _fresh_cache()
        with (
            patch.object(server, "_cache", cache),
            patch.object(
                server.db_client, "get_transmitters", return_value=MOCK_TRANSMITTERS
            ) as mock,
        ):
            result = server.get_transmitters(sat_id="FUNCUBE-1")
            assert result[0]["uuid"] == "abc-123"
            mock.assert_called_once()


class TestGetTransmitter:
    def test_returns_transmitter_detail(self):
        from satnogs_mcp import server

        cache = _fresh_cache()
        with (
            patch.object(server, "_cache", cache),
            patch.object(
                server.db_client, "get_transmitter", return_value=MOCK_TRANSMITTER
            ) as mock,
        ):
            result = server.get_transmitter("abc-123")
            assert result["uuid"] == "abc-123"
            mock.assert_called_once_with("abc-123")


class TestGetTle:
    def test_returns_tle_list(self):
        from satnogs_mcp import server

        cache = _fresh_cache()
        with (
            patch.object(server, "_cache", cache),
            patch.object(server.db_client, "get_tle", return_value=MOCK_TLE) as mock,
        ):
            result = server.get_tle(norad_cat_id=39444)
            assert result[0]["tle0"] == "FUNCUBE-1"
            mock.assert_called_once()


class TestGetTelemetry:
    def test_returns_telemetry_list(self):
        from satnogs_mcp import server

        cache = _fresh_cache()
        with (
            patch.object(server, "_cache", cache),
            patch.object(server.db_client, "get_telemetry", return_value=MOCK_TELEMETRY) as mock,
        ):
            result = server.get_telemetry(sat_id="FUNCUBE-1")
            assert result[0]["sat_id"] == "FUNCUBE-1"
            mock.assert_called_once()


class TestGetModes:
    def test_returns_mode_list(self):
        from satnogs_mcp import server

        cache = _fresh_cache()
        with (
            patch.object(server, "_cache", cache),
            patch.object(server.db_client, "get_modes", return_value=MOCK_MODES) as mock,
        ):
            result = server.get_modes()
            assert any(m["name"] == "FM" for m in result)
            mock.assert_called_once()

    def test_cache_used_on_second_call(self):
        from satnogs_mcp import server

        cache = _fresh_cache()
        with (
            patch.object(server, "_cache", cache),
            patch.object(server.db_client, "get_modes", return_value=MOCK_MODES) as mock,
        ):
            server.get_modes()
            server.get_modes()
            assert mock.call_count == 1


class TestGetArtifacts:
    def test_returns_artifact_list(self):
        from satnogs_mcp import server

        cache = _fresh_cache()
        with (
            patch.object(server, "_cache", cache),
            patch.object(server.db_client, "get_artifacts", return_value=MOCK_ARTIFACTS) as mock,
        ):
            result = server.get_artifacts(observation=12345)
            assert result[0]["observation"] == 12345
            mock.assert_called_once()


# ---------------------------------------------------------------------------
# SatNOGS Network tool tests
# ---------------------------------------------------------------------------


class TestListStations:
    def test_returns_station_list(self):
        from satnogs_mcp import server

        cache = _fresh_cache()
        with (
            patch.object(server, "_cache", cache),
            patch.object(
                server.network_client, "get_stations", return_value=MOCK_STATIONS
            ) as mock,
        ):
            result = server.list_stations()
            assert isinstance(result, list)
            assert result[0]["id"] == 1
            mock.assert_called_once()

    def test_cache_used_on_second_call(self):
        from satnogs_mcp import server

        cache = _fresh_cache()
        with (
            patch.object(server, "_cache", cache),
            patch.object(
                server.network_client, "get_stations", return_value=MOCK_STATIONS
            ) as mock,
        ):
            server.list_stations()
            server.list_stations()
            assert mock.call_count == 1


class TestGetStation:
    def test_returns_station_detail(self):
        from satnogs_mcp import server

        cache = _fresh_cache()
        with (
            patch.object(server, "_cache", cache),
            patch.object(
                server.network_client, "get_station", return_value=MOCK_STATION
            ) as mock,
        ):
            result = server.get_station(1)
            assert result["id"] == 1
            mock.assert_called_once_with(1)


class TestFindNearbyStations:
    def test_filters_by_radius(self):
        from satnogs_mcp import server

        cache = _fresh_cache()
        # London (51.5, -0.1) — station 1 is in London, station 2 is in Sydney
        with (
            patch.object(server, "_cache", cache),
            patch.object(
                server.network_client, "get_stations", return_value=MOCK_STATIONS
            ),
        ):
            result = server.find_nearby_stations(lat=51.5, lon=-0.1, radius_km=100.0)
            ids = [s["id"] for s in result]
            assert 1 in ids, "London station should be within 100 km"
            assert 2 not in ids, "Sydney station should be excluded"

    def test_results_sorted_by_distance(self):
        from satnogs_mcp import server

        cache = _fresh_cache()
        with (
            patch.object(server, "_cache", cache),
            patch.object(
                server.network_client, "get_stations", return_value=MOCK_STATIONS
            ),
        ):
            result = server.find_nearby_stations(lat=51.5, lon=-0.1, radius_km=20000.0)
            distances = [s["distance_km"] for s in result]
            assert distances == sorted(distances)

    def test_distance_km_field_present(self):
        from satnogs_mcp import server

        cache = _fresh_cache()
        with (
            patch.object(server, "_cache", cache),
            patch.object(
                server.network_client, "get_stations", return_value=MOCK_STATIONS
            ),
        ):
            result = server.find_nearby_stations(lat=51.5, lon=-0.1, radius_km=20000.0)
            assert all("distance_km" in s for s in result)

    def test_paginated_response_structure(self):
        """If the API returns a paginated dict, results should still be extracted."""
        from satnogs_mcp import server

        cache = _fresh_cache()
        paginated = {"count": 2, "next": None, "previous": None, "results": MOCK_STATIONS}
        with (
            patch.object(server, "_cache", cache),
            patch.object(server.network_client, "get_stations", return_value=paginated),
        ):
            result = server.find_nearby_stations(lat=51.5, lon=-0.1, radius_km=100.0)
            assert any(s["id"] == 1 for s in result)

    def test_haversine_accuracy(self):
        """Test the Haversine helper directly."""
        from satnogs_mcp.server import _haversine_km

        # London to Paris ≈ 340 km
        dist = _haversine_km(51.5074, -0.1278, 48.8566, 2.3522)
        assert 330 < dist < 360, f"Expected ~343 km, got {dist:.1f} km"


class TestListObservations:
    def test_returns_observation_list(self):
        from satnogs_mcp import server

        cache = _fresh_cache()
        with (
            patch.object(server, "_cache", cache),
            patch.object(
                server.network_client, "get_observations", return_value=MOCK_OBSERVATIONS
            ) as mock,
        ):
            result = server.list_observations(satellite__norad_cat_id=39444)
            assert result[0]["id"] == 12345
            assert "waterfall" in result[0]
            mock.assert_called_once()


class TestGetObservation:
    def test_returns_observation_detail(self):
        from satnogs_mcp import server

        cache = _fresh_cache()
        with (
            patch.object(server, "_cache", cache),
            patch.object(
                server.network_client, "get_observation", return_value=MOCK_OBSERVATION
            ) as mock,
        ):
            result = server.get_observation(12345)
            assert result["id"] == 12345
            assert "waterfall" in result
            mock.assert_called_once_with(12345)


class TestListJobs:
    def test_returns_job_list(self):
        from satnogs_mcp import server

        cache = _fresh_cache()
        with (
            patch.object(server, "_cache", cache),
            patch.object(server.network_client, "get_jobs", return_value=MOCK_JOBS) as mock,
        ):
            result = server.list_jobs()
            assert result[0]["id"] == 1
            mock.assert_called_once()


# ---------------------------------------------------------------------------
# Cache unit tests
# ---------------------------------------------------------------------------


class TestCache:
    def test_get_returns_none_on_miss(self):
        from satnogs_mcp.cache import Cache

        c = Cache(redis_url=None)
        assert c.get("missing") is None

    def test_set_and_get(self):
        from satnogs_mcp.cache import Cache

        c = Cache(redis_url=None)
        c.set("k", {"hello": "world"}, ttl=60)
        assert c.get("k") == {"hello": "world"}

    def test_ttl_expiry(self):
        import time

        from satnogs_mcp.cache import Cache

        c = Cache(redis_url=None)
        c.set("expiring", 42, ttl=1)
        assert c.get("expiring") == 42
        time.sleep(1.1)
        assert c.get("expiring") is None

    def test_get_or_fetch_calls_fn_on_miss(self):
        from satnogs_mcp.cache import Cache

        c = Cache(redis_url=None)
        fetcher = MagicMock(return_value={"data": 1})
        result = c.get_or_fetch("k2", fetcher, ttl=60)
        assert result == {"data": 1}
        fetcher.assert_called_once()

    def test_get_or_fetch_uses_cache_on_hit(self):
        from satnogs_mcp.cache import Cache

        c = Cache(redis_url=None)
        fetcher = MagicMock(return_value={"data": 1})
        c.get_or_fetch("k3", fetcher, ttl=60)
        c.get_or_fetch("k3", fetcher, ttl=60)
        assert fetcher.call_count == 1
