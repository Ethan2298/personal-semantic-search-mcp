# Personal Semantic Search MCP

A Model Context Protocol (MCP) server that enables semantic search over your local notes and documents. Built for use with Claude Code and other MCP-compatible clients.

## Features

- **Semantic Search**: Find notes by meaning, not just keywords
- **Multiple File Types**: Supports Markdown, Python, HTML, JSON, CSV, and plain text
- **Smart Chunking**: Preserves document structure with header hierarchy
- **Fast Local Embeddings**: Uses `all-MiniLM-L6-v2` (384 dimensions, runs on CPU)
- **ChromaDB Storage**: Persistent vector database with incremental indexing
- **File Watching**: Optional real-time re-indexing on file changes

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Claude Code    │────▶│   MCP Server     │────▶│   ChromaDB      │
│  (MCP Client)   │     │   (FastMCP)      │     │   (Vectors)     │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                               │
                               ▼
                        ┌──────────────────┐
                        │ Sentence-        │
                        │ Transformers     │
                        │ (Embeddings)     │
                        └──────────────────┘
```

## Installation

```bash
# Clone the repository
git clone https://github.com/Ethan2298/personal-semantic-search-mcp.git
cd personal-semantic-search-mcp

# Create virtual environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\activate

# Activate (Unix/macOS)
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Configuration

### Claude Code Setup

Add to your `~/.claude/.mcp.json`:

```json
{
  "mcpServers": {
    "semantic-search": {
      "command": "/path/to/your/.venv/Scripts/python.exe",
      "args": ["/path/to/your/mcp_server.py"]
    }
  }
}
```

Then enable in `~/.claude/settings.json`:

```json
{
  "enabledMcpjsonServers": ["semantic-search"]
}
```

## Usage

### MCP Tools (via Claude Code)

Once configured, Claude Code can use these tools:

| Tool | Description |
|------|-------------|
| `search_notes` | Semantic search with natural language queries |
| `index_notes` | Index or re-index your vault |
| `get_index_stats` | Show indexing statistics |

### CLI Usage

```bash
# Index a folder
python search.py index ~/Desktop/Notes

# Search
python search.py query "how to implement authentication"

# Watch for changes (real-time indexing)
python search.py watch ~/Desktop/Notes

# Show statistics
python search.py stats
```

## Module Overview

| File | Purpose |
|------|---------|
| `mcp_server.py` | FastMCP server exposing tools via stdio |
| `search.py` | High-level search and indexing API |
| `embedding_engine.py` | Sentence-transformer embeddings |
| `vector_store.py` | ChromaDB storage and retrieval |
| `text_chunker.py` | Document chunking with overlap |
| `file_reader.py` | Multi-format text extraction |
| `folder_watcher.py` | File system change detection |

## How It Works

1. **File Reading**: Extracts text from various formats (Markdown, Python, HTML, etc.)
2. **Chunking**: Splits documents into ~500 token chunks with 50 token overlap, preserving header hierarchy
3. **Embedding**: Converts chunks to 384-dimensional vectors using `all-MiniLM-L6-v2`
4. **Storage**: Stores vectors in ChromaDB with metadata (file path, headers, timestamps)
5. **Search**: Embeds queries and finds nearest neighbors by cosine similarity

## Performance Notes

- **First startup**: ~10 seconds (loading sentence-transformers model)
- **Indexing speed**: ~100 documents/minute (depends on size)
- **Search latency**: <100ms after warmup
- **Model size**: ~80MB (downloaded on first run)

## Requirements

- Python 3.10+
- ~500MB disk space (model + dependencies)
- Works on CPU (no GPU required)

## License

MIT
