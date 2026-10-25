from mcp_server.server import server


def test_mcp_server_registers_only_the_four_read_only_tools() -> None:
    tools = server._tool_manager.list_tools()

    assert {tool.name for tool in tools} == {
        "get_event",
        "get_exposure_summary",
        "compare_then_now",
        "get_region_context",
    }
