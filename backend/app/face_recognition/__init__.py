"""Face Recognition pipeline — Phase 7."""
from app.face_recognition.manager import face_manager, FaceManager
from app.face_recognition.worker import FaceWorker
from app.face_recognition.detector import face_model_manager, face_detector, FaceModelManager, FaceDetector
from app.face_recognition.embedding import normalize_embedding, serialize_embedding, deserialize_embedding, cosine_similarity
from app.face_recognition.matcher import face_matcher, FaceMatcher, MatchResult, DEFAULT_THRESHOLD
from app.face_recognition.database import face_database, FaceDatabase, KnownPerson
from app.face_recognition.schemas import (
    FaceWorkerStatus,
    PersonRecord,
)

__all__ = [
    "face_manager", "FaceManager",
    "FaceWorker",
    "face_model_manager", "FaceModelManager",
    "face_detector", "FaceDetector",
    "face_matcher", "FaceMatcher", "MatchResult", "DEFAULT_THRESHOLD",
    "face_database", "FaceDatabase", "KnownPerson",
    "normalize_embedding", "serialize_embedding", "deserialize_embedding", "cosine_similarity",
    "FaceWorkerStatus", "PersonRecord",
]
