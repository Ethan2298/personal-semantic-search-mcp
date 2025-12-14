"""
Vector Store Module

ChromaDB wrapper for storing and querying embeddings.
Handles persistence, upserts, deletions, and similarity search.
"""

import os
from dataclasses import dataclass
from pathlib import Path

import chromadb
from chromadb.config import Settings

from text_chunker import Chunk


# Default storage location
DEFAULT_DB_PATH = os.path.expanduser("~/.semantic-search/chroma")


@dataclass
class SearchResult:
    """Represents a search result with chunk and similarity score."""
    chunk: Chunk              # Original chunk with all metadata
    score: float              # Similarity score (0-1, higher = more similar)
    distance: float           # Raw distance from query


def make_chunk_id(chunk: Chunk) -> str:
    """
    Create unique, deterministic ID for a chunk.
    Normalized for cross-platform consistency.
    """
    normalized_path = chunk.source_path.replace('\\', '/')
    return f"{normalized_path}::chunk_{chunk.chunk_index}"


def chunk_to_metadata(chunk: Chunk) -> dict:
    """Convert chunk to ChromaDB metadata dict."""
    return {
        "source_path": chunk.source_path,
        "file_name": Path(chunk.source_path).name,
        "file_type": chunk.file_type,
        "chunk_index": chunk.chunk_index,
        "total_chunks": chunk.total_chunks,
        "modified": chunk.modified,
        "headers": " > ".join(chunk.headers) if chunk.headers else "",
        "token_count": chunk.token_count,
        "char_start": chunk.char_start,
        "char_end": chunk.char_end
    }


def metadata_to_chunk(metadata: dict, content: str) -> Chunk:
    """Reconstruct Chunk from ChromaDB metadata and content."""
    headers = metadata.get("headers", "")
    return Chunk(
        content=content,
        source_path=metadata["source_path"],
        file_type=metadata["file_type"],
        chunk_index=metadata["chunk_index"],
        total_chunks=metadata["total_chunks"],
        modified=metadata["modified"],
        char_start=metadata["char_start"],
        char_end=metadata["char_end"],
        headers=headers.split(" > ") if headers else [],
        token_count=metadata["token_count"]
    )


def init_db(path: str = DEFAULT_DB_PATH) -> chromadb.Collection:
    """
    Initialize ChromaDB with persistent storage.

    Args:
        path: Directory for database persistence

    Returns:
        ChromaDB collection ready for use
    """
    # Ensure directory exists
    Path(path).mkdir(parents=True, exist_ok=True)

    # Initialize client with persistence
    client = chromadb.PersistentClient(path=path)

    # Get or create collection
    collection = client.get_or_create_collection(
        name="semantic_search",
        metadata={"description": "Personal semantic search index"}
    )

    return collection


def upsert_chunks(
    collection: chromadb.Collection,
    chunks: list[Chunk],
    embeddings: list[list[float]]
) -> int:
    """
    Insert or update chunks in the database.

    Args:
        collection: ChromaDB collection
        chunks: List of Chunk objects
        embeddings: Corresponding embeddings

    Returns:
        Number of chunks upserted
    """
    if not chunks:
        return 0

    ids = [make_chunk_id(c) for c in chunks]
    documents = [c.content for c in chunks]
    metadatas = [chunk_to_metadata(c) for c in chunks]

    collection.upsert(
        ids=ids,
        documents=documents,
        embeddings=embeddings,
        metadatas=metadatas
    )

    return len(chunks)


def delete_by_source(collection: chromadb.Collection, source_path: str) -> int:
    """
    Delete all chunks from a specific source file.

    Args:
        collection: ChromaDB collection
        source_path: Path to the source file

    Returns:
        Number of chunks deleted
    """
    # Query to find all chunks from this source
    results = collection.get(
        where={"source_path": source_path},
        include=[]
    )

    if results["ids"]:
        collection.delete(ids=results["ids"])
        return len(results["ids"])

    return 0


def search(
    collection: chromadb.Collection,
    query_embedding: list[float],
    n_results: int = 10,
    filters: dict = None
) -> list[SearchResult]:
    """
    Search for similar chunks.

    Args:
        collection: ChromaDB collection
        query_embedding: Query vector
        n_results: Maximum number of results
        filters: Optional metadata filters (e.g., {"file_type": "md"})

    Returns:
        List of SearchResult objects sorted by relevance
    """
    # Build query parameters
    query_params = {
        "query_embeddings": [query_embedding],
        "n_results": n_results,
        "include": ["documents", "metadatas", "distances"]
    }

    if filters:
        query_params["where"] = filters

    results = collection.query(**query_params)

    # Convert to SearchResult objects
    search_results = []
    if results["ids"] and results["ids"][0]:
        for i, doc_id in enumerate(results["ids"][0]):
            content = results["documents"][0][i]
            metadata = results["metadatas"][0][i]
            distance = results["distances"][0][i]

            # Convert distance to similarity score (0-1, higher = more similar)
            # ChromaDB uses L2 distance by default
            score = 1 / (1 + distance)

            chunk = metadata_to_chunk(metadata, content)
            search_results.append(SearchResult(
                chunk=chunk,
                score=score,
                distance=distance
            ))

    return search_results


def get_indexed_files(collection: chromadb.Collection) -> dict[str, float]:
    """
    Get map of source_path -> modified timestamp for all indexed files.

    Returns:
        Dict mapping file paths to their indexed modification times
    """
    # Get all unique source paths and their modified times
    results = collection.get(include=["metadatas"])

    file_map = {}
    if results["metadatas"]:
        for metadata in results["metadatas"]:
            source_path = metadata["source_path"]
            modified = metadata["modified"]
            # Keep the most recent modified time for each file
            if source_path not in file_map or modified > file_map[source_path]:
                file_map[source_path] = modified

    return file_map


def get_collection_stats(collection: chromadb.Collection) -> dict:
    """
    Get statistics about the collection.

    Returns:
        Dict with count, file types, etc.
    """
    count = collection.count()

    if count == 0:
        return {"total_chunks": 0, "total_files": 0, "by_type": {}}

    results = collection.get(include=["metadatas"])

    files = set()
    by_type = {}

    for metadata in results["metadatas"]:
        files.add(metadata["source_path"])
        file_type = metadata["file_type"]
        by_type[file_type] = by_type.get(file_type, 0) + 1

    return {
        "total_chunks": count,
        "total_files": len(files),
        "by_type": by_type
    }


# CLI for testing
if __name__ == '__main__':
    import tempfile
    from embedding_engine import get_embedding, get_embeddings_batch

    print("Testing vector store...")

    # Use temp directory for test
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_chroma")
        collection = init_db(db_path)
        print(f"✓ Database initialized at {db_path}")

        # Create test chunks
        test_chunks = [
            Chunk(
                content="How to schedule meetings in the calendar app",
                source_path="/test/calendar.md",
                file_type="md",
                chunk_index=0,
                total_chunks=1,
                modified=1234567890.0,
                char_start=0,
                char_end=50,
                headers=["# Calendar"],
                token_count=10
            ),
            Chunk(
                content="Setting up task reminders and notifications",
                source_path="/test/tasks.md",
                file_type="md",
                chunk_index=0,
                total_chunks=1,
                modified=1234567890.0,
                char_start=0,
                char_end=50,
                headers=["# Tasks"],
                token_count=8
            )
        ]

        # Generate embeddings and upsert
        texts = [c.content for c in test_chunks]
        embeddings = get_embeddings_batch(texts)
        count = upsert_chunks(collection, test_chunks, embeddings)
        print(f"✓ Upserted {count} chunks")

        # Test search
        query = "How do I add events to my calendar?"
        query_embedding = get_embedding(query)
        results = search(collection, query_embedding, n_results=2)
        print(f"✓ Search returned {len(results)} results")
        for r in results:
            print(f"  - {r.chunk.content[:50]}... (score: {r.score:.3f})")

        # Test stats
        stats = get_collection_stats(collection)
        print(f"✓ Stats: {stats}")

        # Test delete
        deleted = delete_by_source(collection, "/test/calendar.md")
        print(f"✓ Deleted {deleted} chunks")

        print("\n✓ Vector store working correctly!")
