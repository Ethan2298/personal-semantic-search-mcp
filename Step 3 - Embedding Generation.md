# Step 3 - Embedding Generation

**Status:** Complete ✓

---

## Goal

Convert text chunks into vector embeddings and store them in a local vector database. Include a folder watcher for automatic incremental re-indexing when files change.

---

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Embedding Model | `all-MiniLM-L6-v2` | Free, private, 384 dims, good quality |
| Vector Database | ChromaDB | Local, Python-native, perfect for ~1K chunks |
| Persistence | `~/.semantic-search/` | Survives vault moves |
| Watcher | watchdog | Battle-tested Python file watcher |
| Sync Strategy | Incremental | Only re-embed changed/new files |
| Batch Size | 32 | Optimal for local GPU/CPU |

---

## Input

```python
# From Step 2
from text_chunker import Chunk, chunk_all

chunks: list[Chunk] = chunk_all(documents)

# Chunk structure:
@dataclass
class Chunk:
    content: str
    source_path: str
    file_type: str
    chunk_index: int
    total_chunks: int
    modified: float
    char_start: int
    char_end: int
    headers: list[str]
    token_count: int
```

---

## Output

```python
@dataclass
class SearchResult:
    chunk: Chunk              # Original chunk with all metadata
    score: float              # Similarity score (0-1, higher = more similar)
    distance: float           # Raw distance from query
```

---

## Architecture

```
Notes Vault
     │
     ▼
┌─────────────────┐
│  Folder Watcher │ ◄── Detects changes (create/modify/delete)
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌─────────────────┐
│  File Reader    │ ──► │  Text Chunker   │
│  (Step 1)       │     │  (Step 2)       │
└─────────────────┘     └────────┬────────┘
                                 │
                                 ▼
                        ┌─────────────────┐
                        │ Embedding Engine│ ◄── all-MiniLM-L6-v2
                        └────────┬────────┘
                                 │
                                 ▼
                        ┌─────────────────┐
                        │  Vector Store   │ ◄── ChromaDB
                        │  (ChromaDB)     │
                        └────────┬────────┘
                                 │
                                 ▼
                        ┌─────────────────┐
                        │  Search API     │
                        └─────────────────┘
```

---

## Dependencies

```
sentence-transformers
chromadb
watchdog
```

Add to `requirements.txt`:

```
beautifulsoup4
PyMuPDF
langchain-text-splitters
tiktoken
sentence-transformers
chromadb
watchdog
```

---

## Implementation

### Files to Create
 
| File                  | Purpose                                      |
| --------------------- | -------------------------------------------- |
| `embedding_engine.py` | Local embedding with sentence-transformers   |
| `vector_store.py`     | ChromaDB wrapper with CRUD operations        |
| `folder_watcher.py`   | Watch vault folder, trigger incremental sync |
| `search.py`           | High-level search API                        |
| `test_step3.py`       | Verification tests                           |

---

### embedding_engine.py

```python
from sentence_transformers import SentenceTransformer
from dataclasses import dataclass

# Model: all-MiniLM-L6-v2
# - 384 dimensions
# - ~80MB download
# - Fast inference on CPU
# - Good semantic similarity performance

model = SentenceTransformer('all-MiniLM-L6-v2')

def get_embedding(text: str) -> list[float]:
    """Generate embedding for a single text."""
    return model.encode(text).tolist()

def get_embeddings_batch(texts: list[str], batch_size: int = 32) -> list[list[float]]:
    """Generate embeddings for multiple texts efficiently."""
    return model.encode(texts, batch_size=batch_size).tolist()
```

---

### vector_store.py

```python
import chromadb
from chromadb.config import Settings

def init_db(path: str = "~/.semantic-search/chroma") -> chromadb.Collection:
    """Initialize ChromaDB with persistent storage."""

def upsert_chunks(collection, chunks: list[Chunk], embeddings: list[list[float]]):
    """Insert or update chunks in the database."""

def delete_by_source(collection, source_path: str):
    """Delete all chunks from a specific source file."""

def search(collection, query_embedding: list[float], n_results: int = 10,
           filters: dict = None) -> list[SearchResult]:
    """Search for similar chunks."""

def get_indexed_files(collection) -> dict[str, float]:
    """Get map of source_path -> modified timestamp for all indexed files."""
```

---

### folder_watcher.py

```python
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class VaultWatcher(FileSystemEventHandler):
    """Watch vault folder and trigger re-indexing on changes."""

    def on_created(self, event):
        """Handle new file creation."""

    def on_modified(self, event):
        """Handle file modification."""

    def on_deleted(self, event):
        """Handle file deletion."""

def start_watcher(vault_path: str, on_change_callback):
    """Start watching a folder for changes."""

def stop_watcher(observer):
    """Stop the folder watcher."""
```

---

### Incremental Sync Logic

```python
def sync_vault(vault_path: str, collection):
    """
    Sync vault with vector store incrementally.

    1. Get all current files from vault (Step 1)
    2. Get all indexed files from ChromaDB
    3. Determine:
       - New files (in vault, not in DB)
       - Modified files (mtime changed)
       - Deleted files (in DB, not in vault)
    4. Process changes:
       - Delete chunks for removed/modified files
       - Chunk and embed new/modified files
       - Upsert to database
    """
```

---

## ID Strategy

```python
# Deterministic IDs for upsert support
def make_chunk_id(chunk: Chunk) -> str:
    """Create unique, deterministic ID for a chunk."""
    # Normalize path for cross-platform consistency
    normalized_path = chunk.source_path.replace('\\', '/')
    return f"{normalized_path}::chunk_{chunk.chunk_index}"
```

---

## Metadata Schema

```python
metadata = {
    "source_path": str,      # Full path to source file
    "file_name": str,        # Just the filename
    "file_type": str,        # Extension without dot
    "chunk_index": int,      # Position in document
    "total_chunks": int,     # Total chunks in document
    "modified": float,       # Source file mtime
    "headers": str,          # Joined header hierarchy
    "token_count": int,      # Tokens in chunk
    "char_start": int,       # Position in original
    "char_end": int          # End position
}
```

---

## Test Plan

### Tests to Write

```python
def test_embedding_generation():
    """Test single embedding generation."""

def test_batch_embedding():
    """Test batch embedding generation."""

def test_embedding_dimensions():
    """Verify embeddings are 384 dimensions."""

def test_chromadb_init():
    """Test database initialization."""

def test_upsert_and_search():
    """Test insert and retrieval."""

def test_delete_by_source():
    """Test deletion by source path."""

def test_incremental_sync():
    """Test that only changed files are re-indexed."""

def test_watcher_detects_changes():
    """Test folder watcher triggers on file changes."""
```

---

## Expected Performance

| Operation | Estimated Time |
|-----------|---------------|
| Initial index (878 chunks) | ~30-60 seconds |
| Single file re-index | ~1-2 seconds |
| Search query | ~50-100ms |
| Watcher detection | ~1 second delay |

---

## CLI Interface

```bash
# Full index
python search.py index "C:\Users\ethan\Desktop\Notes"

# Search
python search.py query "how do I use the calendar system"

# Start watcher (runs continuously)
python search.py watch "C:\Users\ethan\Desktop\Notes"

# Show stats
python search.py stats
```

---

## What This Means for Step 4

Step 3 provides **searchable vector storage with automatic sync**. Step 4 needs to:

1. **Expose as MCP Server** - Make search available to Claude
2. **Format results** - Present chunks with context
3. **Handle queries** - Natural language to vector search

### Interface for Step 4

```python
# Step 3 output -> Step 4 input
from search import search_vault

results: list[SearchResult] = search_vault(
    query="how do I add tasks to my calendar",
    n_results=5,
    filters={"file_type": "md"}
)

# SearchResult contains full chunk + metadata + score
```

---

## Next Step

[[Step 4 - MCP Server Integration]]

---

## Reference

### all-MiniLM-L6-v2 Specs

| Property | Value |
|----------|-------|
| Dimensions | 384 |
| Max Sequence | 256 tokens |
| Model Size | ~80MB |
| Speed | ~2000 sentences/sec (CPU) |
| Quality | Good for semantic similarity |

### ChromaDB Limits

| Property | Value |
|----------|-------|
| Max collection size | Millions of vectors |
| Metadata size | 64KB per document |
| Query batch | 10,000 vectors |

For 878 chunks, we're well within all limits.
