# Step 4 - MCP Server Integration

**Status:** Complete ✓
**Verified:** 2025-12-10
**Index:** 909 chunks | 378 files

---

## Verification Results

Tested and confirmed working in Claude Code:

| Tool | Result |
|------|--------|
| `get_index_stats` | ✓ Returns chunk/file counts by type |
| `search_notes` | ✓ Semantic search with relevance scores |
| `index_notes` | ✓ Re-indexes vault on demand |

---

## Goal

Expose the semantic search as an MCP server so Claude can search your vault during conversations. This enables natural language queries like "find my notes about stoicism" without leaving the chat.

---

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| MCP Framework | FastMCP (official SDK) | Official Python SDK, decorator-based, simple |
| Transport | stdio | Simplest for local use with Claude Code |
| Tools | 3 tools | search, index, stats - covers all use cases |
| Default Vault | ~/Desktop/Notes | Your Obsidian vault location |
| Result Format | Markdown | Easy to read, preserves structure |

---

## Input

```python
# From Step 3
from search import search_vault, index_vault
from vector_store import init_db, get_collection_stats
```

---

## Output

An MCP server that exposes:

1. **search_notes** - Semantic search across indexed notes
2. **index_notes** - Re-index the vault (or specific folder)
3. **get_index_stats** - Show what's indexed

---

## Architecture

```
Claude Code
     │
     │ (stdio)
     ▼
┌─────────────────┐
│   MCP Server    │ ◄── mcp_server.py (FastMCP)
│  (stdio transport)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Search Module  │ ◄── search.py (Step 3)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Vector Store   │ ◄── ChromaDB
└─────────────────┘
```

---

## Dependencies

In `requirements.txt`:

```
mcp
```

---

## Implementation

### Files to Create

| File | Purpose |
|------|---------|
| `mcp_server.py` | MCP server with tools using FastMCP |

---

### mcp_server.py

```python
"""
MCP Server for Personal Semantic Search

Exposes semantic search as an MCP server so Claude can search your vault.
Uses FastMCP with stdio transport for local use with Claude Code.
"""

import os
from pathlib import Path
from typing import Optional

from mcp.server.fastmcp import FastMCP

# Import from local modules
from search import search_vault, index_vault
from vector_store import init_db, get_collection_stats

# Default vault path
DEFAULT_VAULT = os.path.expanduser("~/Desktop/Notes")

# Create the FastMCP server
mcp = FastMCP("semantic-search")


@mcp.tool()
def search_notes(query: str, limit: int = 5, file_type: Optional[str] = None) -> str:
    """
    Search your notes using semantic similarity.

    Args:
        query: Natural language search query
        limit: Max results to return (default 5)
        file_type: Filter by file type (e.g., 'md', 'py')

    Returns:
        Formatted markdown with search results
    """
    filters = {"file_type": file_type} if file_type else None
    results = search_vault(query, n_results=limit, filters=filters)

    if not results:
        return "No results found."

    # Format results as markdown
    output = f"## Search Results for '{query}'\n\n"
    for i, r in enumerate(results, 1):
        filename = Path(r.chunk.source_path).name
        headers = " > ".join(r.chunk.headers) if r.chunk.headers else ""
        preview = r.chunk.content[:300].strip()

        output += f"### {i}. {filename} (score: {r.score:.2f})\n"
        if headers:
            output += f"**Section:** {headers}\n\n"
        output += f"{preview}...\n\n"
        output += f"---\n\n"

    return output


@mcp.tool()
def index_notes(vault_path: str = DEFAULT_VAULT, force: bool = False) -> str:
    """
    Index or re-index your notes vault. Run this after adding new notes.

    Args:
        vault_path: Path to vault folder (default: ~/Desktop/Notes)
        force: Force re-index all files (default: False)

    Returns:
        Indexing statistics
    """
    stats = index_vault(vault_path, force=force)

    output = f"## Indexing Complete\n\n"
    output += f"- Documents scanned: {stats['documents_scanned']}\n"
    output += f"- Documents indexed: {stats['documents_indexed']}\n"
    output += f"- Chunks created: {stats['chunks_created']}\n"
    output += f"- Time: {stats['time_seconds']:.1f}s\n"

    return output


@mcp.tool()
def get_index_stats() -> str:
    """
    Get statistics about the indexed notes.

    Returns:
        Index statistics including chunk counts and file types
    """
    collection = init_db()
    stats = get_collection_stats(collection)

    output = "## Index Statistics\n\n"
    output += f"- Total chunks: {stats['total_chunks']}\n"
    output += f"- Total files: {stats['total_files']}\n\n"

    if stats['by_type']:
        output += "### By File Type\n\n"
        for ext, count in sorted(stats['by_type'].items(), key=lambda x: -x[1]):
            pct = count / stats['total_chunks'] * 100
            output += f"- .{ext}: {count} ({pct:.1f}%)\n"

    return output


if __name__ == "__main__":
    mcp.run(transport="stdio")
```

---

## Key Changes from Old API

The MCP SDK migrated to **FastMCP** which simplifies everything:

| Old API | New FastMCP API |
|---------|-----------------|
| `from mcp.server import Server` | `from mcp.server.fastmcp import FastMCP` |
| `@server.list_tools()` decorator | Not needed - automatic |
| `@server.call_tool()` dispatcher | Not needed - use `@mcp.tool()` directly |
| Manual Tool() objects | Automatic from function signature |
| `async with stdio_server()` | `mcp.run(transport="stdio")` |
| Return `TextContent` | Return plain strings |

---

## Claude Code Configuration

Add to `~/.claude.json` under "mcpServers":

```json
{
  "mcpServers": {
    "semantic-search": {
      "type": "stdio",
      "command": "C:/Users/ethan/Desktop/Notes/personal-semantic-search-mcp/.venv/Scripts/python.exe",
      "args": ["C:/Users/ethan/Desktop/Notes/personal-semantic-search-mcp/mcp_server.py"]
    }
  }
}
```

---

## Tool Schemas (Auto-generated)

FastMCP automatically generates schemas from function signatures and docstrings.

### search_notes

```
query: str (required) - Natural language search query
limit: int (optional, default 5) - Max results
file_type: str (optional) - Filter by extension
```

### index_notes

```
vault_path: str (optional) - Path to vault folder
force: bool (optional, default false) - Re-index everything
```

### get_index_stats

No parameters required.

---

## Test Plan

### Manual Testing

1. Start server manually (should block on stdin):
   ```bash
   cd personal-semantic-search-mcp
   .venv/Scripts/python.exe mcp_server.py
   ```

2. Test in Claude Code:
   - Run `/mcp` to verify connection
   - "Search my notes for calendar setup"
   - "What do I have indexed?"
   - "Re-index my vault"

### Expected Behavior

| Action | Expected Result |
|--------|-----------------|
| /mcp | Shows semantic-search as connected |
| Search query | Returns top 5 relevant chunks with scores |
| Empty search | Returns "No results found" |
| Index command | Re-indexes changed files, shows stats |
| Stats command | Shows chunk count, file count, breakdown |

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Server fails to connect | Check Python path in config is absolute |
| Import errors | Ensure venv has all dependencies installed |
| No results | Run index_notes first to populate database |
| Timeout | Increase MCP_TIMEOUT env var if needed |

---

## Reference

- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [FastMCP Documentation](https://modelcontextprotocol.io/docs/develop/build-server)

---

## What This Means for Usage

Once configured, you can ask Claude naturally:

- "Search my notes for information about stoicism"
- "Find my notes about the calendar system"
- "What files do I have indexed?"
- "Re-index my vault, I added new notes"

Claude will use the MCP tools automatically when relevant.
