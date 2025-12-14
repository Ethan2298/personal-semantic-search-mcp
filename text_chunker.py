"""
Text Chunking Module

Splits documents into semantic chunks optimized for embedding and retrieval.
Each chunk is a coherent unit of meaning with enough context to be useful standalone.
"""

from dataclasses import dataclass
from langchain_text_splitters import RecursiveCharacterTextSplitter
import tiktoken

from file_reader import Document


# Token counter for accurate sizing (cl100k_base is used by most modern models)
enc = tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    """Count tokens using OpenAI's tokenizer."""
    return len(enc.encode(text))


@dataclass
class Chunk:
    """Represents a semantic chunk of a document."""
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
        # Use first 50 chars to find position, handling overlap edge cases
        search_text = text[:50] if len(text) >= 50 else text
        char_start = doc.content.find(search_text, max(0, char_position - 150))
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


# CLI for testing
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

    if chunks:
        avg_tokens = sum(c.token_count for c in chunks) // len(chunks)
        print(f"Average tokens per chunk: {avg_tokens}")

        print(f"\nSample chunks:")
        for chunk in chunks[:3]:
            preview = chunk.content[:100].replace('\n', ' ')
            # Handle both forward and back slashes for cross-platform
            filename = chunk.source_path.replace('\\', '/').split('/')[-1]
            print(f"\n  [{chunk.file_type}] {filename}")
            print(f"  Chunk {chunk.chunk_index + 1}/{chunk.total_chunks} | {chunk.token_count} tokens")
            print(f"  Headers: {' > '.join(chunk.headers) if chunk.headers else '(none)'}")
            print(f"  Preview: {preview}...")
