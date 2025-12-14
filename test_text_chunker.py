"""
Verification Tests for Text Chunker

Run with: python test_text_chunker.py
"""

import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from text_chunker import Chunk, count_tokens, get_splitter, extract_headers, chunk_document, chunk_all
from file_reader import Document


def test_chunk_dataclass():
    """Test Chunk dataclass creation."""
    chunk = Chunk(
        content="Test content",
        source_path="/test/path.md",
        file_type="md",
        chunk_index=0,
        total_chunks=1,
        modified=1234567890.0,
        char_start=0,
        char_end=12,
        headers=["# Header"],
        token_count=2
    )
    assert chunk.content == "Test content"
    assert chunk.source_path == "/test/path.md"
    assert chunk.file_type == "md"
    assert chunk.chunk_index == 0
    assert chunk.total_chunks == 1
    assert chunk.headers == ["# Header"]
    return True


def test_count_tokens():
    """Verify token counting accuracy."""
    # Simple words
    assert count_tokens("hello") == 1
    assert count_tokens("hello world") == 2

    # Longer text
    text = "This is a test sentence with several words in it."
    tokens = count_tokens(text)
    assert 8 <= tokens <= 12  # Approximate range

    # Empty string
    assert count_tokens("") == 0

    return True


def test_get_splitter_config():
    """Verify splitter is configured correctly."""
    splitter = get_splitter()

    # Check key configuration
    assert splitter._chunk_size == 512
    assert splitter._chunk_overlap == 100

    # Check separators exist
    assert "\n## " in splitter._separators
    assert "\n\n" in splitter._separators
    assert ". " in splitter._separators

    return True


def test_extract_headers():
    """Test header hierarchy extraction."""
    content = """# Main Title

Some intro text.

## Section One

Content in section one.

### Subsection A

More details here.

## Section Two

Different section.
"""

    # Position in intro should only have h1
    headers = extract_headers(content, 20)
    assert headers == ["# Main Title"]

    # Position in Section One should have h1 + h2
    pos = content.find("Content in section one")
    headers = extract_headers(content, pos)
    assert headers == ["# Main Title", "## Section One"]

    # Position in Subsection A should have h1 + h2 + h3
    pos = content.find("More details here")
    headers = extract_headers(content, pos)
    assert headers == ["# Main Title", "## Section One", "### Subsection A"]

    # Position in Section Two should reset (new h2)
    pos = content.find("Different section")
    headers = extract_headers(content, pos)
    assert headers == ["# Main Title", "## Section Two"]

    return True


def test_chunk_document_basic():
    """Test chunking a simple document."""
    doc = Document(
        path="/test/simple.md",
        content="This is a simple document with some text content.",
        file_type="md",
        modified=1234567890.0
    )

    splitter = get_splitter()
    chunks = chunk_document(doc, splitter)

    # Simple doc should produce one chunk
    assert len(chunks) == 1
    assert chunks[0].source_path == "/test/simple.md"
    assert chunks[0].chunk_index == 0
    assert chunks[0].total_chunks == 1

    return True


def test_chunk_document_preserves_metadata():
    """Verify all metadata fields are populated."""
    doc = Document(
        path="/test/metadata.md",
        content="# Title\n\nSome content here.",
        file_type="md",
        modified=9999999999.0
    )

    splitter = get_splitter()
    chunks = chunk_document(doc, splitter)

    chunk = chunks[0]
    assert chunk.source_path == "/test/metadata.md"
    assert chunk.file_type == "md"
    assert chunk.modified == 9999999999.0
    assert chunk.char_start >= 0
    assert chunk.char_end > chunk.char_start
    assert chunk.token_count > 0

    return True


def test_chunk_overlap():
    """Verify chunks overlap by approximately 100 tokens."""
    # Create a document large enough to produce multiple chunks
    # 512 tokens per chunk = roughly 400 words
    # We need ~3 chunks worth = ~1200 words
    paragraphs = []
    for i in range(30):
        paragraphs.append(f"This is paragraph number {i}. It contains several sentences about various topics. " * 5)

    long_content = "\n\n".join(paragraphs)

    doc = Document(
        path="/test/long.md",
        content=long_content,
        file_type="md",
        modified=1234567890.0
    )

    splitter = get_splitter()
    chunks = chunk_document(doc, splitter)

    # Should produce multiple chunks
    assert len(chunks) >= 2, f"Expected multiple chunks, got {len(chunks)}"

    # Verify each chunk is around target size
    for chunk in chunks:
        # Allow some variance but should be in the right ballpark
        assert chunk.token_count <= 600, f"Chunk too large: {chunk.token_count} tokens"

    # Check that consecutive chunks have overlapping content
    if len(chunks) >= 2:
        chunk1_end = chunks[0].content[-200:]  # Last 200 chars
        chunk2_start = chunks[1].content[:200]  # First 200 chars

        # There should be some overlap (shared substring)
        # Find common sequences
        found_overlap = False
        for i in range(0, len(chunk1_end) - 20):
            if chunk1_end[i:i+20] in chunk2_start:
                found_overlap = True
                break

        assert found_overlap, "No overlap detected between consecutive chunks"

    return True


def test_chunk_all_integration():
    """Integration test with multiple documents."""
    docs = [
        Document(
            path="/test/doc1.md",
            content="# Document One\n\nFirst document content.",
            file_type="md",
            modified=1111111111.0
        ),
        Document(
            path="/test/doc2.py",
            content='def hello():\n    """Say hello."""\n    print("Hello!")',
            file_type="py",
            modified=2222222222.0
        ),
        Document(
            path="/test/doc3.txt",
            content="Plain text content here.",
            file_type="txt",
            modified=3333333333.0
        )
    ]

    chunks = chunk_all(docs)

    # Should have at least 3 chunks (one per doc minimum)
    assert len(chunks) >= 3

    # Check all file types represented
    types = {c.file_type for c in chunks}
    assert "md" in types
    assert "py" in types
    assert "txt" in types

    # Check source paths are preserved
    paths = {c.source_path for c in chunks}
    assert "/test/doc1.md" in paths
    assert "/test/doc2.py" in paths
    assert "/test/doc3.txt" in paths

    return True


def test_empty_document():
    """Empty documents should produce no chunks."""
    docs = [
        Document(
            path="/test/empty.md",
            content="",
            file_type="md",
            modified=1234567890.0
        ),
        Document(
            path="/test/whitespace.md",
            content="   \n\n   \t  ",
            file_type="md",
            modified=1234567890.0
        )
    ]

    chunks = chunk_all(docs)
    assert len(chunks) == 0

    return True


def test_small_document():
    """Document smaller than chunk_size should be one chunk."""
    doc = Document(
        path="/test/small.md",
        content="Small doc.",
        file_type="md",
        modified=1234567890.0
    )

    splitter = get_splitter()
    chunks = chunk_document(doc, splitter)

    assert len(chunks) == 1
    assert chunks[0].content == "Small doc."

    return True


def run_tests():
    """Run all tests and report results."""
    tests = [
        ("Chunk dataclass", test_chunk_dataclass),
        ("count_tokens()", test_count_tokens),
        ("get_splitter_config()", test_get_splitter_config),
        ("extract_headers()", test_extract_headers),
        ("chunk_document() basic", test_chunk_document_basic),
        ("chunk_document() preserves metadata", test_chunk_document_preserves_metadata),
        ("chunk_overlap()", test_chunk_overlap),
        ("chunk_all() integration", test_chunk_all_integration),
        ("Empty document", test_empty_document),
        ("Small document", test_small_document),
    ]

    print("=" * 50)
    print("TEXT CHUNKER VERIFICATION TESTS")
    print("=" * 50)
    print()

    passed = 0
    failed = 0

    for name, test_fn in tests:
        try:
            result = test_fn()
            if result:
                print(f"  [PASS] {name}")
                passed += 1
            else:
                print(f"  [FAIL] {name} - returned False")
                failed += 1
        except Exception as e:
            print(f"  [FAIL] {name} - {e}")
            failed += 1

    print()
    print("-" * 50)
    print(f"Results: {passed} passed, {failed} failed")
    print("-" * 50)

    return failed == 0


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
