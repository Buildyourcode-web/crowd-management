"""
Embedding utilities — Phase 7 (Task 4).

═══════════════════════════════════════════════════════════════════════
Embedding overview
═══════════════════════════════════════════════════════════════════════

InsightFace's ArcFace model produces 512-dimensional float32 embeddings.
These embeddings are already L2-normalized by InsightFace internally,
but we always call normalize_embedding() again for safety (idempotent
on unit vectors).

All embeddings stored in memory cache and in PostgreSQL are L2-normalized
so that cosine similarity reduces to a simple dot product:

    cosine_similarity(a, b) = dot(a, b)   (when ‖a‖ = ‖b‖ = 1)

═══════════════════════════════════════════════════════════════════════
Storage format
═══════════════════════════════════════════════════════════════════════

PostgreSQL stores embeddings as raw bytes (LargeBinary column):
    serialize_embedding(emb)   → float32 bytes
    deserialize_embedding(data) → numpy float32 ndarray, shape (512,)

This requires no pgvector extension and is fully portable.
"""
import numpy as np


def normalize_embedding(embedding: np.ndarray) -> np.ndarray:
    """
    L2-normalize an embedding to unit length.

    Idempotent — safe to call on an already-normalized vector.

    Args:
        embedding: Raw float32 array from InsightFace (typically 512-dim).

    Returns:
        Unit-length float32 array. Returns the input unchanged if its
        norm is effectively zero (degenerate embedding).
    """
    norm = float(np.linalg.norm(embedding))
    if norm < 1e-10:
        return embedding.astype(np.float32)
    return (embedding / norm).astype(np.float32)


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """
    Cosine similarity between two L2-normalized unit vectors.

    When both vectors are L2-normalized, cosine similarity = dot product.
    Range: [-1.0, 1.0].  Values > 0.55 indicate the same person.

    Args:
        a: Normalized embedding (unit vector).
        b: Normalized embedding (unit vector).

    Returns:
        Scalar float in [-1.0, 1.0].
    """
    return float(np.dot(a, b))


def serialize_embedding(embedding: np.ndarray) -> bytes:
    """
    Serialize a float32 embedding to raw bytes for PostgreSQL storage.

    Args:
        embedding: numpy float32 array.

    Returns:
        Raw bytes (little-endian float32).
    """
    return embedding.astype(np.float32).tobytes()


def deserialize_embedding(data: bytes) -> np.ndarray:
    """
    Deserialize raw bytes back to a float32 numpy array.

    Args:
        data: Raw bytes from the PostgreSQL LargeBinary column.

    Returns:
        numpy float32 array of shape (512,).
        Returns a copy (not a read-only view).
    """
    return np.frombuffer(data, dtype=np.float32).copy()


def embeddings_are_duplicate(
    a: np.ndarray,
    b: np.ndarray,
    duplicate_threshold: float = 0.95,
) -> bool:
    """
    Return True if two embeddings represent the same face (Task 16).

    A very high cosine similarity (≥ 0.95) indicates the same person's
    face from the same or very similar source image.

    Args:
        a: Normalized embedding.
        b: Normalized embedding.
        duplicate_threshold: Cosine similarity above which two embeddings
                             are considered duplicate. Default 0.95.
    """
    return cosine_similarity(a, b) >= duplicate_threshold
