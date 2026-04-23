# satnogs-mcp

A Model Context Protocol (MCP) server that gives Claude (and other MCP clients) full access to the SatNOGS open satellite observation network — both the **SatNOGS DB** (satellite catalogue, TLEs, transmitters, telemetry) and the **SatNOGS Network** (ground stations, observations, scheduled jobs).

Modelled after [spacetrack-mcp](https://github.com/harris-mohamed/spacetrack-mcp) in structure, style, and packaging conventions.

---

## Goals

- Expose every meaningful read endpoint from both SatNOGS APIs as MCP tools
- Ship as a PyPI-publishable package (`satnogs-mcp`)
- Optional API key support for SatNOGS DB (reads are public, key enables writes and may unlock higher rate limits)
- Intelligent caching (Redis if available, otherwise in-memory) with TTLs appropriate to each data type
- Proactive rate limiting so the server never gets throttled
- stdio transport for Claude Desktop compatibility

---

## Technical Stack

- **Language**: Python 3.11+
- **MCP framework**: FastMCP 2.0+
- **HTTP client**: `requests`
- **Caching**: Redis (optional, via `REDIS_URL`) with in-memory fallback
- **Config**: `python-dotenv`
- **Transport**: stdio

---

## Project Structure

```
satnogs-mcp/
├── src/
│   └── satnogs_mcp/
│       ├── __init__.py        # package metadata & version
│       ├── __main__.py        # CLI entry point
│       ├── server.py          # FastMCP server & all tool definitions
│       ├── client.py          # HTTP clients for both APIs + rate limiting
│       └── cache.py           # Redis + in-memory dual-tier cache
├── tests/
│   └── test_server.py         # basic smoke tests (mock HTTP)
├── pyproject.toml             # PEP 517/518 build config (hatchling or flit)
├── README.md
├── .env.example
└── .gitignore
```

---

## Environment Variables

```
# Optional — enables write operations and may raise rate limits on SatNOGS DB
SATNOGS_DB_API_KEY=

# Optional — Redis URL for caching (falls back to in-memory if unset)
REDIS_URL=redis://localhost:6379
```

No credentials are required for read-only access to either API.

---

## API Endpoints to Wrap

### SatNOGS DB API (https://db.satnogs.org/api/)

| Tool | Endpoint | Description |
|------|----------|-------------|
| `search_satellites` | `GET /satellites/` | Search by name, NORAD ID, status, country, operator |
| `get_satellite` | `GET /satellites/{sat_id}/` | Full detail for one satellite |
| `get_transmitters` | `GET /transmitters/` | Filter by satellite, status, type, mode |
| `get_transmitter` | `GET /transmitters/{uuid}/` | Detail for one transmitter |
| `get_tle` | `GET /tle/` | Current TLE(s) — filter by NORAD ID or sat_id |
| `get_telemetry` | `GET /telemetry/` | Telemetry frames — filter by sat_id, date range |
| `get_modes` | `GET /modes/` | All communication modes in the DB |
| `get_artifacts` | `GET /artifacts/` | Reference artifacts — filter by observation ID |

### SatNOGS Network API (https://network.satnogs.org/api/)

| Tool | Endpoint | Description |
|------|----------|-------------|
| `list_stations` | `GET /stations/` | All ground stations with location, antenna, status |
| `get_station` | `GET /stations/{id}/` | Detail for one station |
| `find_nearby_stations` | `GET /stations/` | Client-side filter by lat/lon + radius (km) |
| `list_observations` | `GET /observations/` | Filter by satellite, station, date range, vetted status |
| `get_observation` | `GET /observations/{id}/` | Full detail including waterfall/audio/demodulated data URLs |
| `list_jobs` | `GET /jobs/` | Scheduled observation jobs |

---

## Tool Design Guidelines

- Every tool returns clean, structured data (dicts/lists) — FastMCP serialises to JSON automatically
- Include sensible defaults and clear parameter descriptions for every argument
- For list endpoints, always support pagination parameters (`page`, `page_size` / `limit`, `offset`) so Claude can fetch large result sets
- For `find_nearby_stations`, accept `lat`, `lon`, `radius_km` and compute distance using the Haversine formula client-side (no external lib needed)
- Observation tools should expose waterfall image URLs, audio URLs, and demodulated payload URLs as metadata fields when present in the API response
- Never silently drop fields — pass through the full API response structure

---

## Caching TTLs

| Data type | TTL |
|-----------|-----|
| Satellite catalogue (`/satellites/`) | 6 hours |
| Transmitters | 6 hours |
| Modes | 24 hours |
| TLE data | 1 hour |
| Telemetry frames | 15 minutes |
| Ground stations | 1 hour |
| Observations | 5 minutes |
| Jobs | 2 minutes |
| Artifacts | 24 hours |

---

## Rate Limiting

Both APIs are publicly hosted community infrastructure — be conservative:
- Max **20 requests/minute**, **200 requests/hour** for DB API
- Max **20 requests/minute**, **200 requests/hour** for Network API
- Use a sliding-window rate limiter (same pattern as spacetrack-mcp)
- On HTTP 429, back off exponentially: 4s, 8s, 16s

---

## pyproject.toml Requirements

```toml
[project]
name = "satnogs-mcp"
version = "0.1.0"
description = "MCP server for the SatNOGS open satellite observation network"
readme = "README.md"
license = { text = "MIT" }
requires-python = ">=3.11"
dependencies = [
    "fastmcp>=2.0",
    "requests>=2.31.0",
    "python-dotenv>=1.1.0",
    "redis>=5.0.1",
]

[project.scripts]
satnogs-mcp = "satnogs_mcp.__main__:main"

[project.urls]
Homepage = "https://github.com/YOUR_USERNAME/satnogs-mcp"
```

---

## README Requirements

The README must include:
1. Project description and what SatNOGS is (1–2 sentences)
2. Complete list of all MCP tools with descriptions
3. Installation: `pip install satnogs-mcp` and `uvx satnogs-mcp`
4. Claude Desktop configuration example (JSON snippet)
5. Environment variables table
6. Example prompts a user can try with Claude
7. License (MIT)

---

## Tests

Write tests in `tests/test_server.py` using `pytest` and `unittest.mock` to patch HTTP calls:
- Test that each tool returns expected structure when the API returns mock data
- Test that the cache is used on second call (no second HTTP request)
- Test that missing/optional parameters use correct defaults
- Test `find_nearby_stations` Haversine filtering

---

## Implementation Notes

1. Use a module-level singleton for the HTTP clients (one for DB, one for Network) to share the session and rate limiter
2. The DB client should attach `Authorization: Token {SATNOGS_DB_API_KEY}` header when the key is set, and omit it otherwise — all read endpoints work without it
3. Follow the exact same `cache.py` dual-tier pattern as spacetrack-mcp
4. The `__main__.py` entry point should just call `mcp.run()` with stdio transport
5. Use `@mcp.tool()` decorators with full docstrings — FastMCP uses these as the tool descriptions sent to Claude
