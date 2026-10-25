# Local NZHEM MCP server

The local-only stdio MCP server exposes four read-only tools over the same M3
Parquet data used by the application:

- `get_event`
- `get_exposure_summary`
- `compare_then_now`
- `get_region_context`

Run it from the repository root with the ignored local data paths:

```text
python -m mcp_server.server --event-root .local/data/curated/events/m3 --reference-root .local/data/curated/reference-export/dee5b263952e
```

An MCP client's command configuration should use the repository virtual
environment's Python executable, set the repository as its working directory,
pass **absolute** data paths, and set `PYTHONPATH=src;.` on Windows. The server
does not accept or require an OpenAI, ArcGIS or Azure credential and performs
no network calls.

Run the reproducible stdio client demonstration with:

```text
python scripts/demo_mcp.py --event-root .local/data/curated/events/m3 --reference-root .local/data/curated/reference-export/dee5b263952e --output evidence/m6/mcp-demo.json
```

The server initializes DuckDB on one dedicated worker thread and then serves
the small M3 event/exposure cache from memory. This avoids blocking the MCP
event loop while retaining DuckDB's 512 MB limit and single-thread query
contract during startup.
