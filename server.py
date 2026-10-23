"""MCP server for Cursor or any MCP client. Read-only: it connects as sow_reader."""
import json

from mcp.server.fastmcp import FastMCP          # requires mcp<2 (renamed MCPServer in 2.x)

import search
from assemble import draft_sow as _draft

mcp = FastMCP("sow-intelligence")


def _j(x):
    return json.dumps(x, default=str, indent=2)


@mcp.tool()
def search_sows(query: str, clause_type: str | None = None, k: int = 8) -> str:
    """Find passages in past SOWs. Returns text with filename and page for citation."""
    return _j(search.search_text(query, k=min(k, 20), clause_type=clause_type))


@mcp.tool()
def clause_coverage(clause_type: str, present: bool = False) -> str:
    """List every SOW missing a clause type (or having it, if present=true). Complete, not a sample."""
    return _j(search.clause_coverage(clause_type, present))


@mcp.tool()
def contract_details(sow_id: int | None = None, expiring_within_days: int | None = None,
                     product: str | None = None) -> str:
    """Metadata and clause register for SOWs, filtered by id, expiry window or product."""
    return _j(search.contract_details(sow_id, expiring_within_days, product))


@mcp.tool()
def find_components(query: str, section: str | None = None, product: str | None = None,
                    size_band: str | None = None, pricing_model: str | None = None) -> str:
    """Reusable SOW building blocks from proven engagements, with effort data and source."""
    return _j(search.find_components(query, section, product, size_band, pricing_model))


@mcp.tool()
def draft_sow(client_alias: str, objective: str, products: list[str],
              size_band: str | None = None, pricing_model: str | None = None) -> str:
    """Draft a new SOW from proven components. Returns markdown marked DRAFT, gaps and sources."""
    return _j(_draft({"client_alias": client_alias, "objective": objective, "products": products,
                      "size_band": size_band, "pricing_model": pricing_model}))


if __name__ == "__main__":
    mcp.run()
