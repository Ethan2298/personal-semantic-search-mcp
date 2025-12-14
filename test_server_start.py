"""Test that the MCP server can start without errors."""

import sys
import asyncio

async def test_server_start():
    """Try to import and verify server components work."""
    try:
        from mcp_server import server, list_tools, call_tool, main
        print("[OK] Server module imports successfully")

        # Test list_tools
        tools = await list_tools()
        print(f"[OK] list_tools() returns {len(tools)} tools")

        # Test search (quick)
        result = await call_tool("get_index_stats", {})
        if result and result[0].text:
            print("[OK] get_index_stats() works")

        print("\n" + "="*50)
        print("MCP SERVER IS READY FOR CLAUDE CODE")
        print("="*50)
        print("\nTo activate, restart Claude Code or run:")
        print("  /mcp")
        print("\nThe semantic-search server should appear in the list.")
        return True

    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_server_start())
    sys.exit(0 if success else 1)
