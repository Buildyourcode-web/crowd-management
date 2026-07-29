"""
Face Matcher — cosine similarity matching (Tasks 5, 6).

═══════════════════════════════════════════════════════════════════════
Matching overview
═══════════════════════════════════════════════════════════════════════

FaceMatcher compares a query embedding (from a live camera frame) against
all registered embeddings held in the in-memory FaceDatabase cache.

Algorithm:
    1. For each (person_id, name, embedding) in the cache:
           score = cosine_similarity(query, stored_embedding)
    2. Find the highest score across all registered persons.
    3. If max_score >= threshold → MATCH (return identity)
       If max_score <  threshold → UNKNOWN (return UNKNOWN)

Cosine similarity on L2-normalized unit vectors is equivalent to the
dot product, which is very fast (numpy vectorized).

═══════════════════════════════════════════════════════════════════════
Threshold (Task 5)
═══════════════════════════════════════════════════════════════════════

    DEFAULT_THRESHOLD = 0.55

Typical real-world values for ArcFace 512-dim:
    > 0.80 → very high confidence (same person, same conditions)
    > 0.55 → moderate confidence (works well for temple entry scenario)
    < 0.55 → different persons

The threshold is configurable per-worker when calling face_manager.start_worker().

═══════════════════════════════════════════════════════════════════════
Unknown face handling (Task 6)
═══════════════════════════════════════════════════════════════════════

If max_score < threshold, MatchResult.matched = False and person_id = "UNKNOWN".
UNKNOWN results are NEVER inserted into the database.
The worker only publishes Redis events for matched (matched=True) results.
"""
from dataclasses import dataclass
from typing import List, Optional, Tuple

import numpy as np
from loguru import logger

from app.face_recognition.embedding import cosine_similarity

DEFAULT_THRESHOLD: float = 0.55  # Configurable per camera worker


@dataclass
class MatchResult:
    """
    Result of matching one face embedding against the registered database.

    Fields:
        person_id:  Matched person's ID, or "UNKNOWN".
        name:       Matched person's name, or "UNKNOWN".
        similarity: Highest cosine similarity score found [-1.0, 1.0].
        matched:    True if similarity >= threshold, False otherwise.
    """

    person_id: str
    name: str
    similarity: float
    matched: bool


class FaceMatcher:
    """
    Stateless cosine-similarity matcher.

    One instance is shared across all FaceWorkers.
    Thread-safe — pure computation, no shared mutable state.

    Usage:
        registered = face_database.get_all_for_matching()
        result = face_matcher.match(face.embedding, registered)
        if result.matched:
            print(result.person_id, result.similarity)
    """

    def match(
        self,
        query_embedding: np.ndarray,
        registered: List[Tuple[str, str, np.ndarray]],
        threshold: float = DEFAULT_THRESHOLD,
    ) -> MatchResult:
        """
        Compare query_embedding against all registered embeddings.

        Args:
            query_embedding: L2-normalized 512-dim float32 array from
                             FaceDetector (live frame).
            registered:      List of (person_id, name, embedding) tuples
                             from FaceDatabase.get_all_for_matching().
            threshold:       Minimum cosine similarity to declare a match.

        Returns:
            MatchResult with matched=True (known person) or
            matched=False (UNKNOWN).
        """
        if not registered:
            return MatchResult(
                person_id="UNKNOWN",
                name="UNKNOWN",
                similarity=0.0,
                matched=False,
            )

        best_pid = "UNKNOWN"
        best_name = "UNKNOWN"
        best_score = -1.0

        for person_id, name, stored_emb in registered:
            score = cosine_similarity(query_embedding, stored_emb)
            if score > best_score:
                best_score = score
                best_pid = person_id
                best_name = name

        matched = best_score >= threshold

        logger.debug(
            "FaceMatcher | best={pid} | score={s:.4f} | threshold={t} | matched={m}",
            pid=best_pid if matched else "UNKNOWN",
            s=best_score,
            t=threshold,
            m=matched,
        )

        return MatchResult(
            person_id=best_pid if matched else "UNKNOWN",
            name=best_name if matched else "UNKNOWN",
            similarity=round(best_score, 4),
            matched=matched,
        )

    def is_duplicate(
        self,
        new_embedding: np.ndarray,
        registered: List[Tuple[str, str, np.ndarray]],
        duplicate_threshold: float = 0.95,
    ) -> Optional[str]:
        """
        Check if new_embedding is a near-duplicate of any registered embedding.

        Used during person registration (Task 16) to prevent duplicate entries.

        Args:
            new_embedding:       Embedding from the registration image.
            registered:          Current registered embeddings list.
            duplicate_threshold: Cosine similarity above which embeddings
                                 are considered duplicates. Default 0.95.

        Returns:
            person_id of the duplicate person, or None if no duplicate found.
        """
        for person_id, name, stored_emb in registered:
            score = cosine_similarity(new_embedding, stored_emb)
            if score >= duplicate_threshold:
                logger.warning(
                    "Duplicate embedding detected | new matches '{pid}' | score={s:.4f}",
                    pid=person_id,
                    s=score,
                )
                return person_id
        return None


# ─── Singleton ────────────────────────────────────────────────────────────────

face_matcher: FaceMatcher = FaceMatcher()
