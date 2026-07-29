"""
Face Recognition REST API — Task 10.

═══════════════════════════════════════════════════════════════════════
REST API overview (Task 17)
═══════════════════════════════════════════════════════════════════════

Registration workflow:
    POST /face/register
        1. Receive multipart: image file + person_id + name
        2. Validate image (JPEG/PNG, readable)
        3. Ensure InsightFace model is loaded
        4. detect() → must find EXACTLY ONE face (Task 15)
        5. Reject: no face, multiple faces, low quality, too small
        6. Extract + normalize 512-dim embedding
        7. Check for duplicate person_id and duplicate embedding (Task 16)
        8. Persist to PostgreSQL + update in-memory cache

Recognition workflow:
    POST /face/start/{camera_id}
        → Starts FaceWorker (loads model on first start)
        → Worker reads frames, detects faces, matches against cache
        → Publishes to Redis channel:face.match on match (30s cooldown)

REST APIs:
    POST   /face/register            — Register a new person
    PUT    /face/{person_id}         — Update name / photo
    DELETE /face/{person_id}         — Remove person
    POST   /face/reload              — Reload cache from DB
    POST   /face/start/{camera_id}   — Start recognition worker
    POST   /face/stop/{camera_id}    — Stop recognition worker
    GET    /face/status/{camera_id}  — Worker status
    GET    /face/persons             — List registered persons
"""
import io
import uuid

import numpy as np
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from loguru import logger

from app.common.response import ApiResponse
from app.face_recognition.database import face_database
from app.face_recognition.detector import (
    face_detector,
    face_model_manager,
    MIN_DETECTION_SCORE,
    MIN_FACE_SIZE_PX,
)
from app.face_recognition.embedding import serialize_embedding
from app.face_recognition.manager import face_manager
from app.face_recognition.matcher import DEFAULT_THRESHOLD, face_matcher

router = APIRouter(tags=["Face Recognition"])

# Supported image MIME types for registration
_ALLOWED_MIME = {"image/jpeg", "image/png", "image/jpg"}


# ─────────────────────────────────────────────────────────────────────────────
# POST /face/register
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/face/register",
    response_model=ApiResponse,
    summary="Register a new known person",
)
async def register_person(
    image: UploadFile = File(..., description="JPEG or PNG face photo"),
    person_id: str = Form(..., description="Unique person identifier (e.g. 'P102')"),
    name: str = Form(..., description="Full name (e.g. 'John Doe')"),
) -> ApiResponse:
    """
    Register a new person with one reference face image.

    **Requirements (Tasks 15, 16):**
    - Image must contain **exactly one** face
    - Face must have detection confidence ≥ 0.5
    - Face must be at least 40×40 pixels
    - `person_id` must be unique
    - Embedding must not be a near-duplicate of an existing person

    **Multipart fields:**
    - `image` — JPEG or PNG file
    - `person_id` — unique string identifier
    - `name` — non-empty person name
    """
    # ── Validate name ─────────────────────────────────────────────────────────
    name = name.strip()
    if not name:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="name must not be empty",
        )

    person_id = person_id.strip()
    if not person_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="person_id must not be empty",
        )

    # ── Validate image MIME type ──────────────────────────────────────────────
    if image.content_type not in _ALLOWED_MIME:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported image type: {image.content_type}. Use JPEG or PNG.",
        )

    # ── Read image bytes ──────────────────────────────────────────────────────
    try:
        image_bytes = await image.read()
        if not image_bytes:
            raise ValueError("Empty file")
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Cannot read image: {exc}",
        )

    # ── Decode image with OpenCV ──────────────────────────────────────────────
    try:
        import cv2
        buf = np.frombuffer(image_bytes, dtype=np.uint8)
        frame = cv2.imdecode(buf, cv2.IMREAD_COLOR)
        if frame is None:
            raise ValueError("cv2.imdecode returned None")
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Corrupted or invalid image: {exc}",
        )

    # ── Ensure model loaded (lazy, idempotent) ────────────────────────────────
    import asyncio
    await asyncio.to_thread(face_model_manager.ensure_loaded, 0)
    await face_database.ensure_initialized()

    # ── Detect faces ──────────────────────────────────────────────────────────
    faces = await asyncio.to_thread(face_detector.detect, frame)

    if len(faces) == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "No face detected in the provided image. "
                "Please use a clear, front-facing photo."
            ),
        )

    if len(faces) > 1:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Multiple faces detected ({len(faces)}). "
                "Registration image must contain exactly ONE face."
            ),
        )

    face = faces[0]

    if face.is_low_quality(MIN_DETECTION_SCORE):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Low quality face detected (score={face.confidence:.2f}, "
                f"minimum={MIN_DETECTION_SCORE}). Use a clearer photo."
            ),
        )

    if face.is_too_small(MIN_FACE_SIZE_PX):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Face too small ({face.width:.0f}×{face.height:.0f}px, "
                f"minimum {MIN_FACE_SIZE_PX}px). Use a closer photo."
            ),
        )

    # ── Check duplicate person_id ─────────────────────────────────────────────
    if face_database.exists(person_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"person_id '{person_id}' is already registered.",
        )

    # ── Check duplicate embedding ─────────────────────────────────────────────
    registered = face_database.get_all_for_matching()
    dup_pid = face_matcher.is_duplicate(face.embedding, registered)
    if dup_pid:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"This face appears to already be registered as '{dup_pid}'. "
                "Use PUT /api/v1/face/{person_id} to update an existing person."
            ),
        )

    # ── Persist ───────────────────────────────────────────────────────────────
    try:
        await face_database.register(
            person_id=person_id,
            name=name,
            embedding_bytes=serialize_embedding(face.embedding),
            image_bytes=image_bytes,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        )
    except Exception as exc:
        logger.error("register_person DB error | {err}", err=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error during registration.",
        )

    logger.info(
        "Person registered via API | person_id={pid} | name={n}",
        pid=person_id, n=name,
    )
    return ApiResponse.ok(
        data={
            "person_id": person_id,
            "name": name,
            "face_confidence": round(face.confidence, 4),
            "embedding_dim": len(face.embedding),
            "total_registered": face_database.count,
        },
        message=f"Person '{name}' registered successfully",
    )


# ─────────────────────────────────────────────────────────────────────────────
# PUT /face/{person_id}
# ─────────────────────────────────────────────────────────────────────────────

@router.put(
    "/face/{person_id}",
    response_model=ApiResponse,
    summary="Update a registered person's name or photo",
)
async def update_person(
    person_id: str,
    image: UploadFile = File(None, description="New face photo (optional)"),
    name: str = Form(None, description="New name (optional)"),
) -> ApiResponse:
    """
    Update an existing person's name and/or reference photo.

    At least one of `name` or `image` must be provided.
    **Returns** `404` if person_id not found.
    """
    if not face_database.exists(person_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"person_id '{person_id}' not found.",
        )

    if name is not None:
        name = name.strip()
        if not name:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="name must not be empty",
            )

    new_embedding_bytes = None
    new_image_bytes = None

    if image and image.filename:
        import asyncio, cv2

        image_bytes = await image.read()
        buf = np.frombuffer(image_bytes, dtype=np.uint8)
        frame = cv2.imdecode(buf, cv2.IMREAD_COLOR)
        if frame is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Cannot decode the provided image.",
            )

        await asyncio.to_thread(face_model_manager.ensure_loaded, 0)
        faces = await asyncio.to_thread(face_detector.detect, frame)

        if len(faces) != 1:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Image must contain exactly 1 face, found {len(faces)}.",
            )

        new_embedding_bytes = serialize_embedding(faces[0].embedding)
        new_image_bytes = image_bytes

    if name is None and new_embedding_bytes is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Provide at least one of: name, image.",
        )

    await face_database.update(
        person_id=person_id,
        name=name,
        embedding_bytes=new_embedding_bytes,
        image_bytes=new_image_bytes,
    )

    return ApiResponse.ok(
        data={"person_id": person_id, "updated": True},
        message=f"Person '{person_id}' updated",
    )


# ─────────────────────────────────────────────────────────────────────────────
# DELETE /face/{person_id}
# ─────────────────────────────────────────────────────────────────────────────

@router.delete(
    "/face/{person_id}",
    response_model=ApiResponse,
    summary="Delete a registered person",
)
async def delete_person(person_id: str) -> ApiResponse:
    """
    Remove a person from the database and in-memory cache.
    **Returns** `404` if person_id not found.
    """
    deleted = await face_database.delete(person_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"person_id '{person_id}' not found.",
        )
    logger.info("Person deleted via API | person_id={pid}", pid=person_id)
    return ApiResponse.ok(
        data={"person_id": person_id, "deleted": True},
        message=f"Person '{person_id}' deleted",
    )


# ─────────────────────────────────────────────────────────────────────────────
# POST /face/reload
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/face/reload",
    response_model=ApiResponse,
    summary="Reload embedding cache from PostgreSQL",
)
async def reload_database() -> ApiResponse:
    """
    Force-reload the in-memory embedding cache from PostgreSQL.

    Use this after manual database edits or to recover from a cache
    inconsistency. Running workers continue using the new cache immediately.
    """
    count = await face_database.reload()
    return ApiResponse.ok(
        data={"persons_loaded": count},
        message=f"Cache reloaded — {count} persons in memory",
    )


# ─────────────────────────────────────────────────────────────────────────────
# POST /face/start/{camera_id}
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/face/start/{camera_id}",
    response_model=ApiResponse,
    summary="Start face recognition for a camera",
)
async def start_face_recognition(
    camera_id: uuid.UUID,
    threshold: float = DEFAULT_THRESHOLD,
) -> ApiResponse:
    """
    Start a face recognition worker for the specified camera.

    Query param `threshold` (default 0.55) sets the cosine similarity
    threshold above which a face is considered a match.

    **Returns** `409` if a worker is already running.
    """
    started = await face_manager.start_worker(
        camera_id, threshold=threshold
    )
    if not started:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A face recognition worker is already running for camera {camera_id}.",
        )
    logger.info(
        "FaceWorker started via API | camera_id={cid} | threshold={t}",
        cid=camera_id, t=threshold,
    )
    return ApiResponse.ok(
        data={
            "camera_id": str(camera_id),
            "started": True,
            "threshold": threshold,
            "registered_persons": face_database.count,
            "note": "InsightFace model loads on first start (~10s). "
                    "Subsequent starts are instant.",
        },
        message=f"Face recognition started for camera {camera_id}",
    )


# ─────────────────────────────────────────────────────────────────────────────
# POST /face/stop/{camera_id}
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/face/stop/{camera_id}",
    response_model=ApiResponse,
    summary="Stop face recognition for a camera",
)
async def stop_face_recognition(camera_id: uuid.UUID) -> ApiResponse:
    """
    Stop the face recognition worker for the specified camera.
    **Returns** `404` if no worker is running.
    """
    final = face_manager.get_status(camera_id)
    stopped = await face_manager.stop_worker(camera_id)
    if not stopped:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No face recognition worker found for camera {camera_id}.",
        )
    logger.info(
        "FaceWorker stopped via API | camera_id={cid}", cid=camera_id
    )
    return ApiResponse.ok(
        data={
            "camera_id": str(camera_id),
            "stopped": True,
            "final_stats": final.model_dump() if final else {},
        },
        message=f"Face recognition stopped for camera {camera_id}",
    )


# ─────────────────────────────────────────────────────────────────────────────
# GET /face/status/{camera_id}
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/face/status/{camera_id}",
    response_model=ApiResponse,
    summary="Get face recognition status for one camera",
)
async def get_face_status(camera_id: uuid.UUID) -> ApiResponse:
    """
    Returns live face recognition stats for a camera.
    **Returns** `404` if no worker has been started.
    """
    s = face_manager.get_status(camera_id)
    if s is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"No face recognition worker for camera {camera_id}. "
                f"Use POST /api/v1/face/start/{camera_id} first."
            ),
        )
    return ApiResponse.ok(data=s.model_dump(), message="Face recognition status")


# ─────────────────────────────────────────────────────────────────────────────
# GET /face/persons
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/face/persons",
    response_model=ApiResponse,
    summary="List all registered persons",
)
async def get_persons() -> ApiResponse:
    """
    Returns all registered persons ordered by registration date (newest first).

    Embeddings are never returned — only person_id, name, status, created_at.
    """
    await face_database.ensure_initialized()
    persons = await face_database.get_all_persons()
    return ApiResponse.ok(
        data={
            "persons": persons,
            "total": len(persons),
            "cached_active": face_database.count,
        },
        message="Registered persons retrieved",
    )
