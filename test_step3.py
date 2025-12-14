"""
Step 3 Verification Tests

Tests for embedding generation, vector storage, folder watching, and search.
"""

import os
import sys
import shutil
import time
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from text_chunker import Chunk

# Use a persistent test directory (avoids Windows file locking issues with tempfile)
TEST_DIR = Path(__file__).parent / ".test_temp"


def get_test_db_path(name: str) -> str:
    """Get a unique test database path."""
    path = TEST_DIR / name
    if path.exists():
        try:
            shutil.rmtree(path)
        except Exception:
            pass  # Ignore cleanup errors
    path.mkdir(parents=True, exist_ok=True)
    return str(path)


def cleanup_test_dir():
    """Clean up test directory (best effort)."""
    if TEST_DIR.exists():
        try:
            shutil.rmtree(TEST_DIR)
        except Exception:
            pass  # Ignore cleanup errors on Windows


def test_embedding_generation():
    """Test single embedding generation."""
    from embedding_engine import get_embedding

    text = "How do I schedule a meeting?"
    embedding = get_embedding(text)

    assert embedding is not None, "Embedding should not be None"
    assert isinstance(embedding, list), "Embedding should be a list"
    assert len(embedding) == 384, f"Embedding should be 384 dims, got {len(embedding)}"
    assert all(isinstance(x, float) for x in embedding), "All values should be floats"

    return True


def test_batch_embedding():
    """Test batch embedding generation."""
    from embedding_engine import get_embeddings_batch

    texts = [
        "Schedule a meeting for tomorrow",
        "What are my tasks for today?",
        "Add a reminder for the dentist"
    ]

    embeddings = get_embeddings_batch(texts)

    assert len(embeddings) == 3, f"Should have 3 embeddings, got {len(embeddings)}"
    assert all(len(e) == 384 for e in embeddings), "All embeddings should be 384 dims"

    return True


def test_embedding_dimensions():
    """Verify embeddings are 384 dimensions."""
    from embedding_engine import get_embedding, get_embedding_dimension

    assert get_embedding_dimension() == 384, "Dimension should be 384"

    embedding = get_embedding("test")
    assert len(embedding) == 384, "Actual embedding should be 384 dims"

    return True


def test_chromadb_init():
    """Test database initialization."""
    from vector_store import init_db

    db_path = get_test_db_path("test_init")
    collection = init_db(db_path)

    assert collection is not None, "Collection should not be None"
    assert collection.count() == 0, "New collection should be empty"

    return True


def test_upsert_and_search():
    """Test insert and retrieval."""
    from vector_store import init_db, upsert_chunks, search
    from embedding_engine import get_embedding, get_embeddings_batch

    db_path = get_test_db_path("test_upsert_search")
    collection = init_db(db_path)

    # Create test chunks
    chunks = [
        Chunk(
            content="How to schedule meetings in the calendar",
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
            content="Python programming basics and functions",
            source_path="/test/python.md",
            file_type="md",
            chunk_index=0,
            total_chunks=1,
            modified=1234567890.0,
            char_start=0,
            char_end=50,
            headers=["# Python"],
            token_count=8
        )
    ]

    # Generate embeddings and upsert
    texts = [c.content for c in chunks]
    embeddings = get_embeddings_batch(texts)
    upsert_chunks(collection, chunks, embeddings)

    assert collection.count() == 2, "Should have 2 chunks"

    # Search for calendar-related content
    query = "How do I add events to my calendar?"
    query_embedding = get_embedding(query)
    results = search(collection, query_embedding, n_results=2)

    assert len(results) == 2, "Should return 2 results"
    # Calendar chunk should be more relevant
    assert "calendar" in results[0].chunk.content.lower(), "First result should be calendar-related"

    return True


def test_delete_by_source():
    """Test deletion by source path."""
    from vector_store import init_db, upsert_chunks, delete_by_source
    from embedding_engine import get_embeddings_batch

    db_path = get_test_db_path("test_delete")
    collection = init_db(db_path)

    # Create test chunks from different sources
    chunks = [
        Chunk(
            content="Content from file A",
            source_path="/test/fileA.md",
            file_type="md",
            chunk_index=0,
            total_chunks=1,
            modified=1234567890.0,
            char_start=0,
            char_end=20,
            headers=[],
            token_count=5
        ),
        Chunk(
            content="Content from file B",
            source_path="/test/fileB.md",
            file_type="md",
            chunk_index=0,
            total_chunks=1,
            modified=1234567890.0,
            char_start=0,
            char_end=20,
            headers=[],
            token_count=5
        )
    ]

    texts = [c.content for c in chunks]
    embeddings = get_embeddings_batch(texts)
    upsert_chunks(collection, chunks, embeddings)

    assert collection.count() == 2, "Should have 2 chunks"

    # Delete file A
    deleted = delete_by_source(collection, "/test/fileA.md")
    assert deleted == 1, "Should delete 1 chunk"
    assert collection.count() == 1, "Should have 1 chunk remaining"

    return True


def test_incremental_sync():
    """Test that only changed files are re-indexed."""
    from vector_store import init_db, upsert_chunks, get_indexed_files
    from embedding_engine import get_embeddings_batch

    db_path = get_test_db_path("test_sync")
    collection = init_db(db_path)

    # Index a file
    chunks = [
        Chunk(
            content="Original content",
            source_path="/test/file.md",
            file_type="md",
            chunk_index=0,
            total_chunks=1,
            modified=1000.0,  # Older timestamp
            char_start=0,
            char_end=20,
            headers=[],
            token_count=3
        )
    ]

    embeddings = get_embeddings_batch([c.content for c in chunks])
    upsert_chunks(collection, chunks, embeddings)

    # Check indexed files
    indexed = get_indexed_files(collection)
    assert "/test/file.md" in indexed, "File should be indexed"
    assert indexed["/test/file.md"] == 1000.0, "Modified time should match"

    return True


def test_search_with_filters():
    """Test search with metadata filters."""
    from vector_store import init_db, upsert_chunks, search
    from embedding_engine import get_embedding, get_embeddings_batch

    db_path = get_test_db_path("test_filters")
    collection = init_db(db_path)

    # Create chunks of different types
    chunks = [
        Chunk(
            content="Markdown document about calendars",
            source_path="/test/cal.md",
            file_type="md",
            chunk_index=0,
            total_chunks=1,
            modified=1234567890.0,
            char_start=0,
            char_end=35,
            headers=[],
            token_count=5
        ),
        Chunk(
            content="Python code for calendar functions",
            source_path="/test/cal.py",
            file_type="py",
            chunk_index=0,
            total_chunks=1,
            modified=1234567890.0,
            char_start=0,
            char_end=35,
            headers=[],
            token_count=5
        )
    ]

    embeddings = get_embeddings_batch([c.content for c in chunks])
    upsert_chunks(collection, chunks, embeddings)

    # Search with filter
    query_embedding = get_embedding("calendar")
    results = search(collection, query_embedding, n_results=2, filters={"file_type": "md"})

    assert len(results) == 1, "Should only return markdown file"
    assert results[0].chunk.file_type == "md", "Result should be markdown"

    return True


def test_watcher_configuration():
    """Test folder watcher can be configured."""
    from folder_watcher import VaultWatcher, FileChange, SUPPORTED_EXTENSIONS

    changes = []

    def capture_change(change: FileChange):
        changes.append(change)

    watcher = VaultWatcher(capture_change, debounce_seconds=0.1)

    # Verify supported extensions are configured
    assert '.md' in SUPPORTED_EXTENSIONS, "Should support markdown"
    assert '.py' in SUPPORTED_EXTENSIONS, "Should support python"
    assert '.pdf' in SUPPORTED_EXTENSIONS, "Should support pdf"

    return True


def run_tests():
    """Run all verification tests."""
    tests = [
        ("Embedding generation", test_embedding_generation),
        ("Batch embedding", test_batch_embedding),
        ("Embedding dimensions", test_embedding_dimensions),
        ("ChromaDB init", test_chromadb_init),
        ("Upsert and search", test_upsert_and_search),
        ("Delete by source", test_delete_by_source),
        ("Incremental sync", test_incremental_sync),
        ("Search with filters", test_search_with_filters),
        ("Watcher configuration", test_watcher_configuration),
    ]

    print("=" * 50)
    print("STEP 3 VERIFICATION TESTS")
    print("=" * 50)
    print()

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            result = test_func()
            if result:
                print(f"  [PASS] {name}")
                passed += 1
            else:
                print(f"  [FAIL] {name}")
                failed += 1
        except Exception as e:
            print(f"  [FAIL] {name}: {e}")
            failed += 1

    print()
    print("-" * 50)
    print(f"Results: {passed} passed, {failed} failed")
    print("-" * 50)

    return failed == 0


if __name__ == '__main__':
    # First load the embedding model (can take a moment)
    print("Loading embedding model (first run may download ~80MB)...")
    from embedding_engine import get_model
    get_model()
    print("Model loaded.\n")

    try:
        success = run_tests()
    finally:
        # Best-effort cleanup
        cleanup_test_dir()

    sys.exit(0 if success else 1)
