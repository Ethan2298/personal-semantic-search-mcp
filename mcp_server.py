"""
MCP Server for Personal Semantic Search

Exposes semantic search as an MCP server so Claude can search your vault.
Uses FastMCP with stdio transport for local use with Claude Code.
"""

import os
import sys
from pathlib import Path
from typing import Optional

import time

from mcp.server.fastmcp import FastMCP

# Import from local modules
from search import search_vault, index_vault
from vector_store import init_db, get_collection_stats
from embedding_engine import get_model

# Default vault path
DEFAULT_VAULT = os.path.expanduser("~/Desktop/Notes")

# Create the FastMCP server
mcp = FastMCP("semantic-search")


def warmup():
    """
    Pre-load heavy dependencies to avoid cold-start delays.

    This should be called before mcp.run() to ensure:
    - Embedding model is loaded (~10s on first load)
    - ChromaDB connection is established
    """
    start = time.time()

    # Load embedding model (this takes ~10s first time)
    print("Loading embedding model...", flush=True)
    get_model()

    # Initialize ChromaDB connection
    print("Initializing ChromaDB...", flush=True)
    init_db()

    elapsed = time.time() - start
    print(f"Warmup complete in {elapsed:.1f}s", flush=True)


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
    warmup()
    mcp.run(transport="stdio")
