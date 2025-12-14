"""
Search Module - High-Level API

Provides the main interface for indexing and searching your vault.
Ties together file reading, chunking, embedding, and vector storage.
"""

import sys
import time
from pathlib import Path
from typing import Optional

from file_reader import extract_all, Document
from text_chunker import chunk_all, Chunk
from embedding_engine import get_embedding, get_embeddings_batch
from vector_store import (
    init_db, upsert_chunks, delete_by_source, search as vector_search,
    get_indexed_files, get_collection_stats, SearchResult, DEFAULT_DB_PATH
)
from folder_watcher import start_watcher, stop_watcher, FileChange


def index_vault(vault_path: str, db_path: str = DEFAULT_DB_PATH, force: bool = False) -> dict:
    """
    Index all documents in a vault.

    Args:
        vault_path: Path to the vault folder
        db_path: Path for ChromaDB storage
        force: If True, re-index all files regardless of modification time

    Returns:
        Dict with indexing statistics
    """
    start_time = time.time()

    # Initialize database
    collection = init_db(db_path)

    # Get currently indexed files
    indexed_files = get_indexed_files(collection) if not force else {}

    # Extract all documents
    print(f"Scanning {vault_path}...")
    documents = extract_all(vault_path)
    print(f"Found {len(documents)} documents")

    # Determine what needs indexing
    to_index = []
    to_delete = set(indexed_files.keys())  # Start with all indexed, remove as we find them

    for doc in documents:
        if doc.path in to_delete:
            to_delete.remove(doc.path)

        # Check if file needs re-indexing
        indexed_mtime = indexed_files.get(doc.path, 0)
        if force or doc.modified > indexed_mtime:
            to_index.append(doc)

    # Delete removed files
    deleted_count = 0
    for path in to_delete:
        deleted_count += delete_by_source(collection, path)
    if deleted_count:
        print(f"Removed {deleted_count} chunks from {len(to_delete)} deleted files")

    # Index new/modified files
    if not to_index:
        print("No files need indexing")
        return {
            "documents_scanned": len(documents),
            "documents_indexed": 0,
            "chunks_created": 0,
            "chunks_deleted": deleted_count,
            "time_seconds": time.time() - start_time
        }

    print(f"Indexing {len(to_index)} documents...")

    # Chunk all documents
    chunks = chunk_all(to_index)
    print(f"Created {len(chunks)} chunks")

    # Generate embeddings in batches
    print("Generating embeddings...")
    texts = [c.content for c in chunks]
    embeddings = get_embeddings_batch(texts, batch_size=32)

    # Upsert to database
    print("Storing in database...")
    upsert_chunks(collection, chunks, embeddings)

    elapsed = time.time() - start_time
    print(f"Done! Indexed {len(to_index)} documents ({len(chunks)} chunks) in {elapsed:.1f}s")

    return {
        "documents_scanned": len(documents),
        "documents_indexed": len(to_index),
        "chunks_created": len(chunks),
        "chunks_deleted": deleted_count,
        "time_seconds": elapsed
    }


def search_vault(
    query: str,
    db_path: str = DEFAULT_DB_PATH,
    n_results: int = 10,
    filters: Optional[dict] = None
) -> list[SearchResult]:
    """
    Search the indexed vault.

    Args:
        query: Natural language search query
        db_path: Path to ChromaDB storage
        n_results: Maximum number of results
        filters: Optional metadata filters (e.g., {"file_type": "md"})

    Returns:
        List of SearchResult objects sorted by relevance
    """
    collection = init_db(db_path)

    # Generate query embedding
    query_embedding = get_embedding(query)

    # Search
    results = vector_search(collection, query_embedding, n_results, filters)

    return results


def index_single_file(file_path: str, db_path: str = DEFAULT_DB_PATH) -> int:
    """
    Index or re-index a single file.

    Args:
        file_path: Path to the file
        db_path: Path to ChromaDB storage

    Returns:
        Number of chunks created
    """
    path = Path(file_path)
    if not path.exists():
        # File was deleted - remove from index
        collection = init_db(db_path)
        return -delete_by_source(collection, str(path))

    # Create a Document manually
    from file_reader import extract_text
    content = extract_text(path)
    if not content:
        return 0

    doc = Document(
        path=str(path),
        content=content,
        file_type=path.suffix.lstrip('.').lower() or 'txt',
        modified=path.stat().st_mtime
    )

    # Chunk the document
    chunks = chunk_all([doc])
    if not chunks:
        return 0

    # Generate embeddings
    texts = [c.content for c in chunks]
    embeddings = get_embeddings_batch(texts)

    # Delete old chunks for this file first
    collection = init_db(db_path)
    delete_by_source(collection, str(path))

    # Upsert new chunks
    upsert_chunks(collection, chunks, embeddings)

    return len(chunks)


def watch_vault(vault_path: str, db_path: str = DEFAULT_DB_PATH):
    """
    Watch a vault folder and re-index on changes.

    Args:
        vault_path: Path to the vault folder
        db_path: Path to ChromaDB storage
    """
    def handle_change(change: FileChange):
        print(f"[{change.event_type}] {Path(change.path).name}")
        try:
            if change.event_type == 'deleted':
                collection = init_db(db_path)
                deleted = delete_by_source(collection, change.path)
                print(f"  Removed {deleted} chunks")
            else:
                chunks = index_single_file(change.path, db_path)
                print(f"  Indexed {chunks} chunks")
        except Exception as e:
            print(f"  Error: {e}")

    print(f"Watching {vault_path} for changes...")
    print("Press Ctrl+C to stop.\n")

    observer = start_watcher(vault_path, handle_change)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping watcher...")
        stop_watcher(observer)
        print("Done.")


def show_stats(db_path: str = DEFAULT_DB_PATH):
    """Show statistics about the indexed collection."""
    collection = init_db(db_path)
    stats = get_collection_stats(collection)

    print("\n=== INDEX STATISTICS ===")
    print(f"Total chunks:  {stats['total_chunks']}")
    print(f"Total files:   {stats['total_files']}")

    if stats['by_type']:
        print("\nBy file type:")
        for ext, count in sorted(stats['by_type'].items(), key=lambda x: -x[1]):
            pct = count / stats['total_chunks'] * 100
            print(f"  .{ext}: {count} ({pct:.1f}%)")


def main():
    """CLI entry point."""
    if len(sys.argv) < 2:
        print("Personal Semantic Search")
        print("\nUsage:")
        print("  python search.py index <vault_path>   - Index all files")
        print("  python search.py query <query>        - Search the index")
        print("  python search.py watch <vault_path>   - Watch for changes")
        print("  python search.py stats                - Show index statistics")
        print("\nOptions:")
        print("  --force                               - Re-index all files")
        print("  --limit N                             - Limit results (default 10)")
        print("  --type TYPE                           - Filter by file type")
        sys.exit(1)

    command = sys.argv[1]

    if command == "index":
        if len(sys.argv) < 3:
            print("Usage: python search.py index <vault_path> [--force]")
            sys.exit(1)
        vault_path = sys.argv[2]
        force = "--force" in sys.argv
        index_vault(vault_path, force=force)

    elif command == "query":
        if len(sys.argv) < 3:
            print("Usage: python search.py query <query> [--limit N] [--type TYPE]")
            sys.exit(1)

        # Parse query (everything after "query" that's not a flag)
        query_parts = []
        limit = 10
        file_type = None
        i = 2
        while i < len(sys.argv):
            arg = sys.argv[i]
            if arg == "--limit" and i + 1 < len(sys.argv):
                limit = int(sys.argv[i + 1])
                i += 2
            elif arg == "--type" and i + 1 < len(sys.argv):
                file_type = sys.argv[i + 1]
                i += 2
            else:
                query_parts.append(arg)
                i += 1

        query = " ".join(query_parts)
        if not query:
            print("Please provide a search query")
            sys.exit(1)

        filters = {"file_type": file_type} if file_type else None
        results = search_vault(query, n_results=limit, filters=filters)

        print(f"\n=== SEARCH RESULTS for '{query}' ===\n")
        if not results:
            print("No results found.")
        else:
            for i, r in enumerate(results, 1):
                filename = Path(r.chunk.source_path).name
                preview = r.chunk.content[:150].replace('\n', ' ')
                headers = " > ".join(r.chunk.headers) if r.chunk.headers else "(no headers)"

                # Handle Unicode on Windows console
                try:
                    print(f"{i}. [{r.score:.3f}] {filename}")
                    print(f"   Section: {headers}")
                    print(f"   {preview}...")
                    print()
                except UnicodeEncodeError:
                    # Fallback: encode with replacement
                    safe_preview = preview.encode('ascii', 'replace').decode('ascii')
                    print(f"{i}. [{r.score:.3f}] {filename}")
                    print(f"   Section: {headers}")
                    print(f"   {safe_preview}...")
                    print()

    elif command == "watch":
        if len(sys.argv) < 3:
            print("Usage: python search.py watch <vault_path>")
            sys.exit(1)
        vault_path = sys.argv[2]
        watch_vault(vault_path)

    elif command == "stats":
        show_stats()

    else:
        print(f"Unknown command: {command}")
        print("Use: index, query, watch, or stats")
        sys.exit(1)


if __name__ == '__main__':
    main()
