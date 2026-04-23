# satnogs-mcp

An [MCP](https://modelcontextprotocol.io/) server that gives Claude (and other MCP clients) full access to the [SatNOGS](https://satnogs.org/) open satellite observation network — the world's largest open-source ground-station network for amateur satellites.

---

## MCP Tools

### SatNOGS DB (satellite catalogue)

| Tool | Description |
|------|-------------|
| `search_satellites` | Search the satellite catalogue by name, NORAD ID, status, country, or operator |
| `get_satellite` | Full details for one satellite |
| `get_transmitters` | Transmitters filtered by satellite, status, type, or mode |
| `get_transmitter` | Detail for one transmitter by UUID |
| `get_tle` | Current TLE sets, filtered by NORAD ID or satellite ID |
| `get_telemetry` | Decoded telemetry frames, filtered by satellite and date range |
| `get_modes` | All communication modes in the DB |
| `get_artifacts` | Reference artifacts, optionally filtered by observation ID |

### SatNOGS Network (ground stations & observations)

| Tool | Description |
|------|-------------|
| `list_stations` | All ground stations with location, antenna, and status |
| `get_station` | Full detail for one station |
| `find_nearby_stations` | Find stations within a radius (km) of a lat/lon point |
| `list_observations` | Observations filtered by satellite, station, date range, and vetting status |
| `get_observation` | Full observation detail including waterfall, audio, and demodulated data URLs |
| `list_jobs` | Scheduled observation jobs |

---

## Installation

```bash
pip install satnogs-mcp
```

Or run without installing via `uvx`:

```bash
uvx satnogs-mcp
```

---

## Claude Desktop Configuration

Add the following to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "satnogs": {
      "command": "uvx",
      "args": ["satnogs-mcp"],
      "env": {
        "SATNOGS_DB_API_KEY": "optional-key-here",
        "REDIS_URL": "redis://localhost:6379"
      }
    }
  }
}
```

Config file location:
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `SATNOGS_DB_API_KEY` | No | API key for SatNOGS DB (read access works without it; key may enable higher rate limits and write access) |
| `REDIS_URL` | No | Redis connection URL for caching (e.g. `redis://localhost:6379`). Falls back to in-memory cache if unset. |

Copy `.env.example` to `.env` and fill in any values you need:

```bash
cp .env.example .env
```

---

## Example Prompts

Try these prompts in Claude once the server is running:

- "Search for active cubesats launched by universities."
- "What are the current TLEs for ISS (NORAD 25544)?"
- "Show me all FM transmitters for the FUNcube-1 satellite."
- "Find SatNOGS ground stations within 200 km of London."
- "List recent good observations of NORAD 39444."
- "What ground stations are online in Europe?"
- "Show me the waterfall image from observation 12345."
- "What telemetry has been collected for FUNCUBE-1 this week?"

---

## Development

```bash
git clone https://github.com/atlas/satnogs-mcp
cd satnogs-mcp
pip install -e ".[dev]"
pytest tests/ -v
```

---

## Architecture

- **`cache.py`** — Dual-tier cache: Redis primary (when `REDIS_URL` is set), in-memory TTL dict fallback
- **`client.py`** — HTTP clients for DB and Network APIs with sliding-window rate limiter (20 req/min, 200 req/hour) and exponential back-off on HTTP 429
- **`server.py`** — FastMCP server with `@mcp.tool()` decorated tools; module-level singleton clients share sessions and rate-limiter state

---

## License

MIT
