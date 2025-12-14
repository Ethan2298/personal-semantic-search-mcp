"""
Tests for server warmup/eager initialization.

These tests verify that the MCP server pre-loads heavy dependencies
at startup to avoid cold-start delays on first tool call.
"""

import time
import pytest


class TestWarmup:
    """Tests for the warmup() function."""

    def test_warmup_loads_embedding_model(self):
        """
        Scenario 1: Server pre-loads embedding model.

        Given the warmup function exists
        When warmup() is called
        Then the embedding model should be loaded (not None)
        """
        from mcp_server import warmup
        from embedding_engine import _model

        # Before warmup, model might be None (lazy)
        # After warmup, model should be loaded
        warmup()

        from embedding_engine import _model as model_after
        assert model_after is not None, "Embedding model should be loaded after warmup"

    def test_warmup_initializes_chromadb(self):
        """
        Scenario 2: Server pre-loads ChromaDB.

        Given the warmup function exists
        When warmup() is called
        Then ChromaDB collection should be accessible
        """
        from mcp_server import warmup

        warmup()

        # Verify we can get stats without delay
        from vector_store import init_db, get_collection_stats
        collection = init_db()
        stats = get_collection_stats(collection)

        assert stats is not None
        assert 'total_chunks' in stats

    def test_warmup_logs_timing(self, capsys):
        """
        Warmup should log how long initialization took.
        """
        from mcp_server import warmup

        warmup()

        captured = capsys.readouterr()
        # Should see timing in output
        assert 'warmup' in captured.out.lower() or 'init' in captured.out.lower() or 'loaded' in captured.out.lower()


class TestToolResponseTime:
    """Tests for tool response time after warmup."""

    def test_get_index_stats_responds_quickly_after_warmup(self):
        """
        Scenario 2: Tool calls respond immediately after init.

        Given the server has completed warmup
        When get_index_stats is called
        Then response should be returned within 1 second
        """
        from mcp_server import warmup, get_index_stats

        # Warmup first
        warmup()

        # Now time the tool call
        start = time.time()
        result = get_index_stats()
        elapsed = time.time() - start

        assert elapsed < 1.0, f"get_index_stats took {elapsed:.2f}s, should be <1s"
        assert "Index Statistics" in result

    def test_search_notes_responds_quickly_after_warmup(self):
        """
        Scenario 3: Search works on first call.

        Given the server has completed warmup
        When search_notes is called
        Then results should be returned within 1 second
        """
        from mcp_server import warmup, search_notes

        # Warmup first
        warmup()

        # Now time the search
        start = time.time()
        result = search_notes("test query")
        elapsed = time.time() - start

        assert elapsed < 1.0, f"search_notes took {elapsed:.2f}s, should be <1s"
        # Result should be a string (either results or "No results found")
        assert isinstance(result, str)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
