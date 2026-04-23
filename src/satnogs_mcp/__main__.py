"""CLI entry point for satnogs-mcp.

Run with:
    python -m satnogs_mcp
or:
    satnogs-mcp
"""

from .server import mcp


def main() -> None:
    """Start the satnogs-mcp FastMCP server using stdio transport."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
