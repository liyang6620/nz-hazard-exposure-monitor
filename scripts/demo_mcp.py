from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[1]


async def run_demo(event_root: Path, reference_root: Path, event_id: str) -> dict:
    event_root = event_root.resolve()
    reference_root = reference_root.resolve()
    environment = dict(os.environ)
    environment["PYTHONPATH"] = os.pathsep.join([str(ROOT / "src"), str(ROOT)])
    parameters = StdioServerParameters(
        command=sys.executable,
        args=[
            "-m",
            "mcp_server.server",
            "--event-root",
            str(event_root),
            "--reference-root",
            str(reference_root),
        ],
        env=environment,
        cwd=ROOT,
    )
    async with (
        stdio_client(parameters) as streams,
        ClientSession(*streams) as session,
    ):
        await session.initialize()
        tools = await session.list_tools()
        event = await session.call_tool("get_event", {"event_id": event_id})
        exposure = await session.call_tool(
            "get_exposure_summary", {"event_id": event_id, "mmi_threshold": 6.0}
        )
    return {
        "transport": "stdio",
        "tools": sorted(tool.name for tool in tools.tools),
        "event_call_error": event.isError,
        "event_result_blocks": len(event.content),
        "exposure_call_error": exposure.isError,
        "exposure_result_blocks": len(exposure.content),
        "network_required": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Exercise the local NZHEM MCP server")
    parser.add_argument("--event-root", type=Path, required=True)
    parser.add_argument("--reference-root", type=Path, required=True)
    parser.add_argument("--event-id", default="2016p858000")
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    result = asyncio.run(
        run_demo(arguments.event_root, arguments.reference_root, arguments.event_id)
    )
    encoded = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if arguments.output:
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")


if __name__ == "__main__":
    main()
