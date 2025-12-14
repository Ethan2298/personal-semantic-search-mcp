"""Quick test to verify MCP server functionality before configuring Claude Code."""

import asyncio
from mcp_server import list_tools, call_tool

async def test_mcp():
    print("=" * 50)
    print("Testing MCP Server Tools")
    print("=" * 50)

    # Test 1: List tools
    print("\n1. Testing list_tools()...")
    tools = await list_tools()
    print(f"   Found {len(tools)} tools:")
    for t in tools:
        print(f"   - {t.name}: {t.description[:50]}...")

    # Test 2: Get stats
    print("\n2. Testing get_index_stats...")
    result = await call_tool("get_index_stats", {})
    print("   " + result[0].text.replace("\n", "\n   "))

    # Test 3: Search
    print("\n3. Testing search_notes...")
    result = await call_tool("search_notes", {"query": "calendar scheduling", "limit": 2})
    output = result[0].text
    # Just show first 500 chars
    print("   " + output[:500].replace("\n", "\n   ") + "...")

    print("\n" + "=" * 50)
    print("All tests passed! MCP server is ready.")
    print("=" * 50)

if __name__ == "__main__":
    asyncio.run(test_mcp())
