"""
Folder Watcher Module

Watches a folder for file changes and triggers incremental re-indexing.
Uses watchdog for cross-platform file system event monitoring.
"""

import time
from pathlib import Path
from typing import Callable, Optional
from dataclasses import dataclass

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent

from file_reader import SKIP_DIRS, is_hidden


# Supported extensions for indexing (defined here to avoid import issues)
SUPPORTED_EXTENSIONS = {
    # Text files
    '.md', '.txt', '.rst', '.py', '.js', '.ts', '.jsx', '.tsx',
    # HTML
    '.html', '.htm',
    # Data files
    '.json', '.csv',
    # PDF
    '.pdf'
}


@dataclass
class FileChange:
    """Represents a file change event."""
    path: str
    event_type: str  # 'created', 'modified', 'deleted'


class VaultWatcher(FileSystemEventHandler):
    """
    Watch vault folder and trigger re-indexing on changes.

    Debounces rapid changes and filters to supported file types.
    """

    def __init__(
        self,
        on_change: Callable[[FileChange], None],
        debounce_seconds: float = 1.0
    ):
        """
        Initialize the watcher.

        Args:
            on_change: Callback function for file changes
            debounce_seconds: Time to wait before processing changes (debouncing)
        """
        super().__init__()
        self.on_change = on_change
        self.debounce_seconds = debounce_seconds
        self._last_events: dict[str, float] = {}

    def _should_process(self, path: str) -> bool:
        """Check if this file should trigger indexing."""
        file_path = Path(path)

        # Skip directories
        if file_path.is_dir():
            return False

        # Skip hidden files/folders
        if is_hidden(file_path):
            return False

        # Skip files in skip directories
        if any(part in SKIP_DIRS for part in file_path.parts):
            return False

        # Only process supported extensions
        if file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            return False

        return True

    def _is_debounced(self, path: str) -> bool:
        """Check if this event should be debounced (skipped)."""
        now = time.time()
        last_time = self._last_events.get(path, 0)

        if now - last_time < self.debounce_seconds:
            return True

        self._last_events[path] = now
        return False

    def _handle_event(self, event: FileSystemEvent, event_type: str):
        """Handle a file system event."""
        if event.is_directory:
            return

        path = event.src_path

        if not self._should_process(path):
            return

        if self._is_debounced(path):
            return

        change = FileChange(path=path, event_type=event_type)
        self.on_change(change)

    def on_created(self, event: FileSystemEvent):
        """Handle new file creation."""
        self._handle_event(event, 'created')

    def on_modified(self, event: FileSystemEvent):
        """Handle file modification."""
        self._handle_event(event, 'modified')

    def on_deleted(self, event: FileSystemEvent):
        """Handle file deletion."""
        if event.is_directory:
            return

        path = event.src_path

        # For deletions, skip the normal checks (file doesn't exist anymore)
        # but still check extension
        if Path(path).suffix.lower() not in SUPPORTED_EXTENSIONS:
            return

        if self._is_debounced(path):
            return

        change = FileChange(path=path, event_type='deleted')
        self.on_change(change)

    def on_moved(self, event: FileSystemEvent):
        """Handle file move/rename."""
        # Treat as delete + create
        if hasattr(event, 'src_path'):
            self._handle_event(
                type('Event', (), {'is_directory': event.is_directory, 'src_path': event.src_path})(),
                'deleted'
            )
        if hasattr(event, 'dest_path'):
            self._handle_event(
                type('Event', (), {'is_directory': event.is_directory, 'src_path': event.dest_path})(),
                'created'
            )


def start_watcher(
    vault_path: str,
    on_change: Callable[[FileChange], None],
    debounce_seconds: float = 1.0
) -> Observer:
    """
    Start watching a folder for changes.

    Args:
        vault_path: Path to the folder to watch
        on_change: Callback for file changes
        debounce_seconds: Debounce interval

    Returns:
        Observer instance (call stop_watcher to stop)
    """
    path = Path(vault_path)
    if not path.exists():
        raise ValueError(f"Folder does not exist: {vault_path}")

    handler = VaultWatcher(on_change, debounce_seconds)
    observer = Observer()
    observer.schedule(handler, str(path), recursive=True)
    observer.start()

    return observer


def stop_watcher(observer: Observer):
    """
    Stop the folder watcher.

    Args:
        observer: Observer instance from start_watcher
    """
    observer.stop()
    observer.join()


# CLI for testing
if __name__ == '__main__':
    import sys

    def print_change(change: FileChange):
        print(f"  [{change.event_type}] {change.path}")

    if len(sys.argv) < 2:
        print("Usage: python folder_watcher.py <folder_path>")
        print("\nWatches the folder and prints file changes.")
        print("Press Ctrl+C to stop.")
        sys.exit(1)

    folder = sys.argv[1]
    print(f"Watching: {folder}")
    print("Press Ctrl+C to stop.\n")

    observer = start_watcher(folder, print_change)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping watcher...")
        stop_watcher(observer)
        print("Done.")
