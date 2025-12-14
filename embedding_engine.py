"""
Embedding Engine Module

Generates vector embeddings using sentence-transformers (all-MiniLM-L6-v2).
This model produces 384-dimensional embeddings optimized for semantic similarity.
"""

from sentence_transformers import SentenceTransformer

# Model: all-MiniLM-L6-v2
# - 384 dimensions
# - ~80MB download (first run)
# - Fast inference on CPU (~2000 sentences/sec)
# - Good semantic similarity performance

# Lazy loading - model loads on first use
_model = None


def get_model() -> SentenceTransformer:
    """Get or initialize the embedding model (lazy loading)."""
    global _model
    if _model is None:
        _model = SentenceTransformer('all-MiniLM-L6-v2')
    return _model


def get_embedding(text: str) -> list[float]:
    """
    Generate embedding for a single text.

    Args:
        text: The text to embed

    Returns:
        384-dimensional embedding as list of floats
    """
    model = get_model()
    return model.encode(text).tolist()


def get_embeddings_batch(texts: list[str], batch_size: int = 32) -> list[list[float]]:
    """
    Generate embeddings for multiple texts efficiently.

    Args:
        texts: List of texts to embed
        batch_size: Batch size for processing (default 32)

    Returns:
        List of 384-dimensional embeddings
    """
    model = get_model()
    return model.encode(texts, batch_size=batch_size, show_progress_bar=len(texts) > 100).tolist()


def get_embedding_dimension() -> int:
    """Return the embedding dimension (384 for all-MiniLM-L6-v2)."""
    return 384


# CLI for testing
if __name__ == '__main__':
    print("Testing embedding engine...")
    print(f"Loading model: all-MiniLM-L6-v2")

    # Test single embedding
    test_text = "How do I add tasks to my calendar?"
    embedding = get_embedding(test_text)
    print(f"\nSingle embedding test:")
    print(f"  Text: {test_text}")
    print(f"  Embedding dimension: {len(embedding)}")
    print(f"  First 5 values: {embedding[:5]}")

    # Test batch embedding
    test_texts = [
        "Schedule a meeting for tomorrow",
        "What are my tasks for today?",
        "Add a reminder for the dentist appointment"
    ]
    embeddings = get_embeddings_batch(test_texts)
    print(f"\nBatch embedding test:")
    print(f"  Texts: {len(test_texts)}")
    print(f"  Embeddings generated: {len(embeddings)}")
    print(f"  All correct dimension: {all(len(e) == 384 for e in embeddings)}")

    print("\n✓ Embedding engine working correctly!")
