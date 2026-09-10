from __future__ import annotations

import numpy as np


def vector_to_blob(vector: list[float]) -> bytes:
    values = np.asarray(vector, dtype=np.float32)
    if values.ndim != 1 or values.size == 0:
        raise ValueError("embedding must be a non-empty one-dimensional vector")
    return values.tobytes()


def blob_to_vector(blob: bytes) -> np.ndarray:
    values = np.frombuffer(blob, dtype=np.float32)
    if values.size == 0:
        raise ValueError("stored embedding is empty")
    return values


def cosine_similarity(left: np.ndarray, right: np.ndarray) -> float:
    if left.shape != right.shape:
        raise ValueError("embedding dimensions do not match")
    denominator = float(np.linalg.norm(left) * np.linalg.norm(right))
    if denominator == 0:
        return 0.0
    return float(np.dot(left, right) / denominator)

