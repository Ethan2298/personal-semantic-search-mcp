"""
File Reader and Text Extraction Module

Scans directories and extracts text content from supported file types.
"""

import os
import json
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from io import StringIO


@dataclass
class Document:
    """Represents an extracted document."""
    path: str           # absolute file path
    content: str        # extracted text
    file_type: str      # extension (without dot)
    modified: float     # mtime for sync


# Configuration
MAX_FILE_SIZE = 1 * 1024 * 1024  # 1MB default
CSV_MAX_ROWS = 100

# Directories/files to skip
SKIP_DIRS = {
    '.git', 'node_modules', '__pycache__', '.venv', 'venv',
    '.idea', '.vscode', 'dist', 'build', '.obsidian'
}

# Extensions that are plain text (read directly)
TEXT_EXTENSIONS = {'.md', '.txt', '.rst', '.py', '.js', '.ts', '.jsx', '.tsx'}

# Binary extensions to skip
BINARY_EXTENSIONS = {
    '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.ico', '.svg',
    '.mp3', '.mp4', '.wav', '.avi', '.mov', '.mkv',
    '.exe', '.dll', '.so', '.dylib',
    '.zip', '.tar', '.gz', '.rar', '.7z',
    '.db', '.sqlite', '.pickle', '.pkl'
}


def is_hidden(path: Path) -> bool:
    """Check if path or any parent is hidden."""
    for part in path.parts:
        if part.startswith('.') and part not in {'.', '..'}:
            return True
    return False


def should_skip(path: Path, max_size: int = MAX_FILE_SIZE) -> bool:
    """Determine if a file should be skipped."""
    # Skip hidden files/folders
    if is_hidden(path):
        return True

    # Skip binary extensions
    if path.suffix.lower() in BINARY_EXTENSIONS:
        return True

    # Skip files that are too large
    try:
        if path.stat().st_size > max_size:
            return True
    except OSError:
        return True

    return False


def extract_text(file_path: Path) -> Optional[str]:
    """Extract text content from a file based on its type."""
    suffix = file_path.suffix.lower()

    try:
        # Plain text files
        if suffix in TEXT_EXTENSIONS:
            return file_path.read_text(encoding='utf-8', errors='ignore')

        # HTML files
        elif suffix in {'.html', '.htm'}:
            return extract_html(file_path)

        # JSON files
        elif suffix == '.json':
            return extract_json(file_path)

        # CSV files
        elif suffix == '.csv':
            return extract_csv(file_path)

        # PDF files
        elif suffix == '.pdf':
            return extract_pdf(file_path)

        # Unknown but possibly text - try reading
        else:
            try:
                content = file_path.read_text(encoding='utf-8', errors='strict')
                return content
            except UnicodeDecodeError:
                return None

    except Exception as e:
        print(f"Warning: Could not extract {file_path}: {e}")
        return None


def extract_html(file_path: Path) -> str:
    """Extract text from HTML using BeautifulSoup."""
    try:
        from bs4 import BeautifulSoup
        html = file_path.read_text(encoding='utf-8', errors='ignore')
        soup = BeautifulSoup(html, 'html.parser')

        # Remove script and style elements
        for element in soup(['script', 'style']):
            element.decompose()

        return soup.get_text(separator='\n', strip=True)
    except ImportError:
        # Fallback: basic tag stripping
        import re
        html = file_path.read_text(encoding='utf-8', errors='ignore')
        text = re.sub(r'<[^>]+>', ' ', html)
        return ' '.join(text.split())


def extract_json(file_path: Path) -> str:
    """Extract JSON as formatted text."""
    content = file_path.read_text(encoding='utf-8', errors='ignore')
    try:
        data = json.loads(content)
        return json.dumps(data, indent=2, ensure_ascii=False)
    except json.JSONDecodeError:
        return content


def extract_csv(file_path: Path) -> str:
    """Extract CSV with headers and first N rows."""
    content = file_path.read_text(encoding='utf-8', errors='ignore')
    lines = []

    try:
        reader = csv.reader(StringIO(content))
        for i, row in enumerate(reader):
            if i >= CSV_MAX_ROWS + 1:  # +1 for header
                lines.append(f"... ({i} more rows)")
                break
            lines.append(' | '.join(row))
    except csv.Error:
        return content

    return '\n'.join(lines)


def extract_pdf(file_path: Path) -> Optional[str]:
    """Extract text from PDF using PyMuPDF."""
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(file_path)
        text_parts = []

        for page in doc:
            text_parts.append(page.get_text())

        doc.close()
        return '\n'.join(text_parts)

    except ImportError:
        print("Warning: PyMuPDF not installed. Skipping PDF extraction.")
        return None
    except Exception as e:
        print(f"Warning: Could not extract PDF {file_path}: {e}")
        return None


def extract_all(folder_path: str, max_size: int = MAX_FILE_SIZE) -> list[Document]:
    """
    Scan a directory and extract text from all supported files.

    Args:
        folder_path: Path to the directory to scan
        max_size: Maximum file size in bytes (default 1MB)

    Returns:
        List of Document objects with extracted content
    """
    documents = []
    root = Path(folder_path).resolve()

    if not root.exists():
        raise ValueError(f"Folder does not exist: {folder_path}")

    if not root.is_dir():
        raise ValueError(f"Path is not a directory: {folder_path}")

    for file_path in root.rglob('*'):
        # Skip directories
        if file_path.is_dir():
            continue

        # Skip if in a skip directory
        relative = file_path.relative_to(root)
        if any(part in SKIP_DIRS for part in relative.parts):
            continue

        # Skip based on other criteria
        if should_skip(file_path, max_size):
            continue

        # Extract content
        content = extract_text(file_path)

        if content is not None and content.strip():
            doc = Document(
                path=str(file_path),
                content=content,
                file_type=file_path.suffix.lstrip('.').lower() or 'txt',
                modified=file_path.stat().st_mtime
            )
            documents.append(doc)

    return documents


# CLI for testing
if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print("Usage: python file_reader.py <folder_path>")
        sys.exit(1)

    folder = sys.argv[1]
    print(f"Scanning: {folder}")

    docs = extract_all(folder)
    print(f"\nFound {len(docs)} documents:\n")

    for doc in docs:
        preview = doc.content[:100].replace('\n', ' ')
        print(f"  [{doc.file_type}] {doc.path}")
        print(f"        {preview}...")
        print()
