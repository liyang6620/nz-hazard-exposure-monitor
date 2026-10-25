from __future__ import annotations

import argparse
import asyncio
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from nzhem.adapters.local.briefing_tools import DuckDbBriefingTools

server = FastMCP("NZ Hazard Exposure Monitor")
_tools: DuckDbBriefingTools | None = None
_data_paths: tuple[Path, Path] | None = None
_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="nzhem-mcp-duckdb")


def _active_tools() -> DuckDbBriefingTools:
    global _tools
    if _tools is None:
        if _data_paths is None:
            raise RuntimeError("MCP data paths have not been configured")
        _tools = DuckDbBriefingTools(*_data_paths)
    return _tools


def _sync_query(method: str, *args: Any) -> Any:
    return getattr(_active_tools(), method)(*args)


async def _query(method: str, *args: Any) -> Any:
    return await asyncio.get_running_loop().run_in_executor(
        _executor, partial(_sync_query, method, *args)
    )


@server.tool()
async def get_event(event_id: str) -> dict[str, Any]:
    """Return the authoritative event metadata and shaking-source details."""
    return await _query("get_event", event_id)


@server.tool()
async def get_exposure_summary(event_id: str, mmi_threshold: float) -> list[dict[str, Any]]:
    """Return building, footprint and population exposure grouped by region."""
    return await _query("get_exposure_summary", event_id, mmi_threshold)


@server.tool()
async def compare_then_now(event_id: str, mmi_threshold: float) -> list[dict[str, Any]]:
    """Compare supported event-time building exposure with current exposure."""
    return await _query("compare_then_now", event_id, mmi_threshold)


@server.tool()
async def get_region_context(region_code: str) -> dict[str, Any]:
    """Return current exposure and strong-event context for one region."""
    return await _query("get_region_context", region_code)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the local NZHEM stdio MCP server")
    parser.add_argument("--event-root", type=Path, required=True)
    parser.add_argument("--reference-root", type=Path, required=True)
    arguments = parser.parse_args()
    global _data_paths
    _data_paths = (arguments.event_root, arguments.reference_root)
    try:
        server.run(transport="stdio")
    finally:
        if _tools is not None:
            _executor.submit(_tools.close).result()
        _executor.shutdown()


if __name__ == "__main__":
    main()
