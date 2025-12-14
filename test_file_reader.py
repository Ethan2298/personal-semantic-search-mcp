"""
Verification tests for file_reader.py
"""

import tempfile
import os
import json
from pathlib import Path

from file_reader import (
    Document, extract_all, extract_text, should_skip, is_hidden,
    extract_html, extract_json, extract_csv, SKIP_DIRS, BINARY_EXTENSIONS
)


def create_test_files(test_dir: Path):
    """Create sample files of each supported type."""

    # Markdown
    (test_dir / "readme.md").write_text("# Hello World\n\nThis is a test.")

    # Plain text
    (test_dir / "notes.txt").write_text("Plain text content here.")

    # Python
    (test_dir / "script.py").write_text('"""Docstring"""\ndef hello():\n    return "world"')

    # JavaScript
    (test_dir / "app.js").write_text('const x = 1;\nconsole.log("hello");')

    # HTML
    (test_dir / "page.html").write_text('<html><head><title>Test</title></head><body><p>Hello</p></body></html>')

    # JSON
    (test_dir / "config.json").write_text('{"name": "test", "value": 123}')

    # CSV
    (test_dir / "data.csv").write_text('name,age,city\nAlice,30,NYC\nBob,25,LA')

    # Hidden file (should be skipped)
    (test_dir / ".hidden").write_text("secret")

    # Hidden folder
    hidden_dir = test_dir / ".git"
    hidden_dir.mkdir()
    (hidden_dir / "config").write_text("git config")

    # node_modules (should be skipped)
    nm_dir = test_dir / "node_modules"
    nm_dir.mkdir()
    (nm_dir / "package.json").write_text('{}')

    # Binary file (should be skipped)
    (test_dir / "image.png").write_bytes(b'\x89PNG\r\n\x1a\n' + b'\x00' * 100)

    # Nested folder
    nested = test_dir / "subfolder"
    nested.mkdir()
    (nested / "nested.md").write_text("# Nested file")


def test_document_dataclass():
    """Test Document dataclass creation."""
    doc = Document(
        path="/test/file.md",
        content="Hello world",
        file_type="md",
        modified=1234567890.0
    )
    assert doc.path == "/test/file.md"
    assert doc.content == "Hello world"
    assert doc.file_type == "md"
    assert doc.modified == 1234567890.0
    print("  [PASS] Document dataclass")


def test_is_hidden():
    """Test hidden file detection."""
    assert is_hidden(Path(".git/config")) == True
    assert is_hidden(Path("src/.env")) == True
    assert is_hidden(Path("normal/file.txt")) == False
    assert is_hidden(Path("my.file.txt")) == False
    print("  [PASS] is_hidden()")


def test_should_skip():
    """Test skip logic."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)

        # Create test files
        normal = tmp_path / "normal.txt"
        normal.write_text("hello")

        binary = tmp_path / "image.png"
        binary.write_bytes(b'\x00' * 100)

        large = tmp_path / "large.txt"
        large.write_text("x" * (2 * 1024 * 1024))  # 2MB

        assert should_skip(normal) == False, "Normal file should not be skipped"
        assert should_skip(binary) == True, "Binary file should be skipped"
        assert should_skip(large) == True, "Large file should be skipped"

    print("  [PASS] should_skip()")


def test_extract_text_types():
    """Test extraction for each file type."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)

        # Markdown
        md = tmp_path / "test.md"
        md.write_text("# Header\n\nContent")
        assert "# Header" in extract_text(md)

        # JSON
        js = tmp_path / "test.json"
        js.write_text('{"key": "value"}')
        result = extract_text(js)
        assert "key" in result and "value" in result

        # CSV
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("a,b,c\n1,2,3")
        result = extract_text(csv_file)
        assert "a | b | c" in result

        # HTML
        html = tmp_path / "test.html"
        html.write_text("<html><body><p>Hello World</p></body></html>")
        result = extract_text(html)
        assert "Hello World" in result
        assert "<p>" not in result  # Tags should be stripped

    print("  [PASS] extract_text() for all types")


def test_extract_all_integration():
    """Integration test for extract_all()."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        create_test_files(tmp_path)

        docs = extract_all(tmp)

        # Check we got expected documents
        paths = [d.path for d in docs]
        types = [d.file_type for d in docs]

        # Should include these
        assert any("readme.md" in p for p in paths), "Should find readme.md"
        assert any("notes.txt" in p for p in paths), "Should find notes.txt"
        assert any("script.py" in p for p in paths), "Should find script.py"
        assert any("app.js" in p for p in paths), "Should find app.js"
        assert any("page.html" in p for p in paths), "Should find page.html"
        assert any("config.json" in p for p in paths), "Should find config.json"
        assert any("data.csv" in p for p in paths), "Should find data.csv"
        assert any("nested.md" in p for p in paths), "Should find nested file"

        # Should NOT include these
        assert not any(".hidden" in p for p in paths), "Should skip hidden files"
        assert not any(".git" in p for p in paths), "Should skip .git folder"
        assert not any("node_modules" in p for p in paths), "Should skip node_modules"
        assert not any("image.png" in p for p in paths), "Should skip binary files"

        # Check file types detected correctly
        assert "md" in types
        assert "txt" in types
        assert "py" in types
        assert "js" in types
        assert "html" in types
        assert "json" in types
        assert "csv" in types

        # Check content is extracted
        md_doc = next(d for d in docs if "readme.md" in d.path)
        assert "Hello World" in md_doc.content
        assert md_doc.modified > 0

    print("  [PASS] extract_all() integration")


def test_extract_all_error_handling():
    """Test error handling for invalid paths."""
    try:
        extract_all("/nonexistent/path/that/doesnt/exist")
        assert False, "Should raise ValueError"
    except ValueError as e:
        assert "does not exist" in str(e)

    print("  [PASS] Error handling")


def run_all_tests():
    """Run all verification tests."""
    print("\n" + "="*50)
    print("FILE READER VERIFICATION TESTS")
    print("="*50 + "\n")

    tests = [
        test_document_dataclass,
        test_is_hidden,
        test_should_skip,
        test_extract_text_types,
        test_extract_all_integration,
        test_extract_all_error_handling,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"  [FAIL] {test.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"  [ERROR] {test.__name__}: {e}")
            failed += 1

    print("\n" + "-"*50)
    print(f"Results: {passed} passed, {failed} failed")
    print("-"*50 + "\n")

    return failed == 0


if __name__ == "__main__":
    import sys
    success = run_all_tests()
    sys.exit(0 if success else 1)
