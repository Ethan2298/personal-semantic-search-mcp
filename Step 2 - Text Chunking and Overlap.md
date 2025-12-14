# Step 2 - Text Chunking and Overlap

**Status:** Complete

---

## Goal

Split documents into semantic chunks optimized for embedding and retrieval. Each chunk should be a coherent unit of meaning with enough context to be useful standalone.

---

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Strategy | Recursive | 89% of vault is Markdown with headers |
| Chunk Size | 512 tokens | Balanced retrieval precision vs. context |
| Overlap | 100 tokens | Prevents context loss at boundaries |
| Library | LangChain | Battle-tested, handles edge cases |
| Output | Flat list | Vector DBs expect flat; metadata preserves relationships |

---

## Input

```python
# From Step 1
from file_reader import Document, extract_all

documents: list[Document] = extract_all(folder_path)

# Document structure:
@dataclass
class Document:
    path: str           # absolute file path
    content: str        # extracted text
    file_type: str      # extension (without dot)
    modified: float     # mtime for sync
```

---

## Output

```python
@dataclass
class Chunk:
    content: str          # The chunk text
    source_path: str      # Absolute path to source file
    file_type: str        # "md", "py", "json", etc.
    chunk_index: int      # Position in source document (0, 1, 2...)
    total_chunks: int     # How many chunks this document produced
    modified: float       # Source file mtime (for incremental sync)
    char_start: int       # Start position in original content
    char_end: int         # End position in original content
    headers: list[str]    # Header hierarchy, e.g. ["# Main", "## Section"]
    token_count: int      # Actual tokens in this chunk
```

---

## Chunking Strategy

### Recursive Character Splitting

Split on natural boundaries in order of preference:

```
Priority 1: Markdown headers     "\n## ", "\n### ", "\n#### "
Priority 2: Paragraphs           "\n\n"
Priority 3: Line breaks          "\n"
Priority 4: Sentences            ". ", "! ", "? "
Priority 5: Words                " "
Priority 6: Characters           ""
```

This ensures we only break mid-sentence as a last resort.

### Overlap Behavior

```
Document: [==========|==========|==========]
Chunk 1:  [==========]
Chunk 2:       [==========]      <- 100 token overlap with Chunk 1
Chunk 3:            [==========] <- 100 token overlap with Chunk 2
```

Overlap ensures context isn't lost at boundaries.

---

## Dependencies

```
langchain-text-splitters
tiktoken
```

Add to `requirements.txt`:

```
beautifulsoup4
PyMuPDF
langchain-text-splitters
tiktoken
```

---

## Implementation

### Files to Create

| File | Purpose |
|------|---------|
| `text_chunker.py` | Main module with `chunk_all()` and `Chunk` dataclass |
| `test_text_chunker.py` | Verification tests |

### Key Functions

```python
# text_chunker.py

from dataclasses import dataclass
from langchain.text_splitter import RecursiveCharacterTextSplitter
import tiktoken

from file_reader import Document

# Token counter for accurate sizing
enc = tiktoken.get_encoding("cl100k_base")

def count_tokens(text: str) -> int:
    """Count tokens using OpenAI's tokenizer."""
    return len(enc.encode(text))


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


def get_splitter() -> RecursiveCharacterTextSplitter:
    """Configure the recursive text splitter."""
    return RecursiveCharacterTextSplitter(
        chunk_size=512,
        chunk_overlap=100,
        length_function=count_tokens,
        separators=[
            "\n## ",      # h2 headers
            "\n### ",     # h3 headers
            "\n#### ",    # h4 headers
            "\n\n",       # paragraphs
            "\n",         # lines
            ". ",         # sentences
            ", ",         # clauses
            " ",          # words
            ""            # characters
        ],
        keep_separator=True
    )


def extract_headers(content: str, char_position: int) -> list[str]:
    """
    Extract the header hierarchy for a given position in the document.
    Returns list like ["# Main Title", "## Section", "### Subsection"]
    """
    headers = []
    lines = content[:char_position].split('\n')

    current_h1 = None
    current_h2 = None
    current_h3 = None

    for line in lines:
        if line.startswith('# ') and not line.startswith('##'):
            current_h1 = line
            current_h2 = None
            current_h3 = None
        elif line.startswith('## ') and not line.startswith('###'):
            current_h2 = line
            current_h3 = None
        elif line.startswith('### '):
            current_h3 = line

    if current_h1:
        headers.append(current_h1)
    if current_h2:
        headers.append(current_h2)
    if current_h3:
        headers.append(current_h3)

    return headers


def chunk_document(doc: Document, splitter: RecursiveCharacterTextSplitter) -> list[Chunk]:
    """
    Split a single document into chunks with metadata.
    """
    # Get raw text chunks
    texts = splitter.split_text(doc.content)

    chunks = []
    char_position = 0

    for i, text in enumerate(texts):
        # Find position in original document
        char_start = doc.content.find(text[:50], char_position)  # Use first 50 chars to find
        if char_start == -1:
            char_start = char_position  # Fallback
        char_end = char_start + len(text)

        chunk = Chunk(
            content=text,
            source_path=doc.path,
            file_type=doc.file_type,
            chunk_index=i,
            total_chunks=len(texts),  # Will update after
            modified=doc.modified,
            char_start=char_start,
            char_end=char_end,
            headers=extract_headers(doc.content, char_start),
            token_count=count_tokens(text)
        )
        chunks.append(chunk)
        char_position = char_start + len(text) - 100  # Account for overlap

    # Update total_chunks now that we know it
    for chunk in chunks:
        chunk.total_chunks = len(chunks)

    return chunks


def chunk_all(documents: list[Document]) -> list[Chunk]:
    """
    Chunk all documents and return a flat list of chunks.

    Args:
        documents: List of Document objects from Step 1

    Returns:
        Flat list of Chunk objects with metadata
    """
    splitter = get_splitter()
    all_chunks = []

    for doc in documents:
        if doc.content.strip():  # Skip empty documents
            chunks = chunk_document(doc, splitter)
            all_chunks.extend(chunks)

    return all_chunks
```

### CLI Interface

```python
# At bottom of text_chunker.py

if __name__ == '__main__':
    import sys
    from file_reader import extract_all

    if len(sys.argv) < 2:
        print("Usage: python text_chunker.py <folder_path>")
        sys.exit(1)

    folder = sys.argv[1]
    print(f"Reading documents from: {folder}")

    docs = extract_all(folder)
    print(f"Found {len(docs)} documents")

    print("Chunking...")
    chunks = chunk_all(docs)

    print(f"\n=== CHUNKING RESULTS ===")
    print(f"Total chunks: {len(chunks)}")
    print(f"Average tokens per chunk: {sum(c.token_count for c in chunks) // len(chunks)}")

    print(f"\nSample chunks:")
    for chunk in chunks[:3]:
        preview = chunk.content[:100].replace('\n', ' ')
        print(f"\n  [{chunk.file_type}] {chunk.source_path.split(chr(92))[-1]}")
        print(f"  Chunk {chunk.chunk_index + 1}/{chunk.total_chunks} | {chunk.token_count} tokens")
        print(f"  Headers: {' > '.join(chunk.headers) if chunk.headers else '(none)'}")
        print(f"  Preview: {preview}...")
```

---

## Test Plan

### Tests to Write

```python
# test_text_chunker.py

def test_chunk_dataclass():
    """Test Chunk dataclass creation."""

def test_count_tokens():
    """Verify token counting accuracy."""

def test_get_splitter_config():
    """Verify splitter is configured correctly."""

def test_extract_headers():
    """Test header hierarchy extraction."""

def test_chunk_document_basic():
    """Test chunking a simple document."""

def test_chunk_document_preserves_metadata():
    """Verify all metadata fields are populated."""

def test_chunk_overlap():
    """Verify chunks overlap by ~100 tokens."""

def test_chunk_all_integration():
    """Integration test with multiple documents."""

def test_empty_document():
    """Empty documents should produce no chunks."""

def test_small_document():
    """Document smaller than chunk_size should be one chunk."""
```

---

## Expected Results

For your Notes vault:

| Metric | Estimated Value |
|--------|-----------------|
| Input documents | 369 |
| Output chunks | ~1,200-1,500 |
| Avg chunks per doc | 3-4 |
| Total tokens | ~700K-800K |
| Avg tokens per chunk | ~450-500 |

---

## Actual Results

### Verification Tests

```
==================================================
TEXT CHUNKER VERIFICATION TESTS
==================================================

  [PASS] Chunk dataclass
  [PASS] count_tokens()
  [PASS] get_splitter_config()
  [PASS] extract_headers()
  [PASS] chunk_document() basic
  [PASS] chunk_document() preserves metadata
  [PASS] chunk_overlap()
  [PASS] chunk_all() integration
  [PASS] Empty document
  [PASS] Small document

--------------------------------------------------
Results: 10 passed, 0 failed
--------------------------------------------------
```

### Real-World Test (Notes Vault)

**Tested:** 2025-12-10

```
=== DETAILED CHUNKING STATISTICS ===

Input documents:        372
Output chunks:          878
Average chunks per doc: 2.4

Total tokens:           266,186
Avg tokens per chunk:   303
Min tokens in chunk:    1
Max tokens in chunk:    512

Chunks by file type:
  .md     718 (81.8%)
  .py      93 (10.6%)
  .html    22 (2.5%)
  .csv     21 (2.4%)
  .txt     11 (1.3%)
  .json    10 (1.1%)
  .ps1      2 (0.2%)
  .bat      1 (0.1%)

Token distribution:
  0-100     147 (16.7%)
  101-200   140 (15.9%)
  201-300   110 (12.5%)
  301-400   115 (13.1%)
  401-512   366 (41.7%)
  513+        0 (0.0%)

Documents with most chunks:
   35 chunks - mcp-html-fetch-server-prd.md
   24 chunks - orchestrator.py
   15 chunks - MT Hiring Pipeline Analysis - YTD 2025.md
   13 chunks - PLAN - Motion-like Calendar System.md
   13 chunks - hiring_pipeline_analysis.py
```

**Verdict:** Working as expected

### Notes on Results

- **Fewer chunks than estimated** - The vault has many small notes (daily logs, quick captures) that don't need splitting
- **Lower avg tokens** - Many atomic notes fit in a single small chunk, pulling down the average
- **41.7% at optimal size** - Larger documents correctly split into ~512 token chunks
- **0 chunks over 512** - Splitter is correctly respecting the token limit
- **81.8% Markdown** - Confirms header-based splitting is the right strategy

---

## What This Means for Step 3

Step 2 provides **semantic chunks with rich metadata**. Step 3 needs to:

1. **Generate embeddings** - Convert each chunk's `content` to a vector
2. **Store vectors** - Save to a vector database with metadata
3. **Enable search** - Query by semantic similarity

### Interface for Step 3

```python
# Step 2 output -> Step 3 input
chunks: list[Chunk] = chunk_all(documents)

# Step 3 transforms to:
@dataclass
class EmbeddedChunk:
    chunk: Chunk              # Original chunk with metadata
    embedding: list[float]    # 1536-dim vector (OpenAI) or 384-dim (local)
```

The `modified` timestamp flows through to enable **incremental sync** - only re-embed chunks from files that changed.

---

## Next Step

[[Step 3 - Embedding Generation]]

---

## Reference

### Token Counts by Content Type

| Content | Approximate Tokens |
|---------|-------------------|
| 1 word | 1-2 tokens |
| 1 sentence | 15-25 tokens |
| 1 paragraph | 50-100 tokens |
| 512 tokens | ~400 words |

### Why These Separators?

```python
separators=[
    "\n## ",    # Markdown h2 - major section breaks
    "\n### ",   # Markdown h3 - subsection breaks
    "\n#### ",  # Markdown h4 - sub-subsection
    "\n\n",     # Paragraph breaks
    "\n",       # Line breaks (lists, code)
    ". ",       # Sentence boundaries
    ", ",       # Clause boundaries
    " ",        # Word boundaries
    ""          # Character (last resort)
]
```

Headers first because your vault is 89% Markdown. This ensures "## Goal" stays with its content, not split across chunks.
