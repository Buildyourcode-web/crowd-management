"""
RTSPClient — OpenCV VideoCapture wrapper supporting RTSP, HTTP, and local video files.

All methods are BLOCKING (synchronous). Always invoke from a thread executor
so the asyncio event loop is never stalled.
"""
import uuid
from enum import Enum
from typing import Optional

import cv2
import numpy as np
from loguru import logger


class StreamSourceType(str, Enum):
    """Detected stream source type used for logging and backend selection."""
    RTSP = "RTSP"
    HTTP = "HTTP"
    VIDEO_FILE = "VIDEO_FILE"


def _detect_source_type(url: str) -> StreamSourceType:
    """
    Automatically detect the stream source from its URL/path.

    Rules:
        rtsp://...          → RTSP
        http:// / https://  → HTTP
        anything else       → VIDEO_FILE (local path)
    """
    lower = url.lower()
    if lower.startswith("rtsp://"):
        return StreamSourceType.RTSP
    if lower.startswith(("http://", "https://")):
        return StreamSourceType.HTTP
    return StreamSourceType.VIDEO_FILE


class RTSPClient:
    """
    Manages a single cv2.VideoCapture connection to an RTSP stream,
    HTTP stream, or local video file.

    Design principles:
    - One instance per connection attempt (create new instance on reconnect)
    - Source type (RTSP / HTTP / VIDEO_FILE) is auto-detected from the URL
    - Minimal buffer size (1) so read_frame() always returns the latest frame
    - Video files loop automatically when the last frame is reached
    - Never raises — every error is caught and logged
    """

    # Keep only 1 frame in the OpenCV buffer (live streams only)
    _BUFFER_SIZE: int = 1

    def __init__(self, camera_id: uuid.UUID, rtsp_url: str) -> None:
        self._camera_id = camera_id
        self._rtsp_url = rtsp_url
        self._source_type: StreamSourceType = _detect_source_type(rtsp_url)
        self._is_video_file: bool = self._source_type == StreamSourceType.VIDEO_FILE
        self._cap: Optional[cv2.VideoCapture] = None
        self._connected: bool = False

    # ─── Connection ───────────────────────────────────────────────────────────

    def connect(self) -> bool:
        """
        Open the stream using the appropriate OpenCV backend:
          RTSP / HTTP  → cv2.CAP_FFMPEG
          VIDEO_FILE   → default backend (cv2.CAP_ANY)

        Returns:
            True  — stream/file opened successfully.
            False — failed to open.
        """
        try:
            if self._is_video_file:
                cap = cv2.VideoCapture(self._rtsp_url)        # default backend for files
            else:
                import os
                os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|fflags;nobuffer|max_delay;500000|stimeout;2000000|timeout;2000000"
                cap = cv2.VideoCapture(self._rtsp_url, cv2.CAP_FFMPEG)
                cap.set(cv2.CAP_PROP_BUFFERSIZE, self._BUFFER_SIZE)

            if cap.isOpened():
                self._cap = cap
                self._connected = True
                logger.info(
                    "Camera connected | camera_id={cid} | source={src} | url={url}",
                    cid=self._camera_id,
                    src=self._source_type,
                    url=self._rtsp_url,
                )
                return True

            cap.release()
            logger.warning(
                "Camera connection failed | camera_id={cid} | source={src} | url={url}",
                cid=self._camera_id,
                src=self._source_type,
                url=self._rtsp_url,
            )
            return False

        except Exception as exc:
            logger.error(
                "Camera connect exception | camera_id={cid} | error={err}",
                cid=self._camera_id,
                err=str(exc),
            )
            return False

    # ─── Frame Reading ────────────────────────────────────────────────────────

    def read_frame(self) -> Optional[np.ndarray]:
        """
        Grab the next frame from the stream or file.

        Video file behaviour: when the last frame is reached, the capture
        automatically rewinds to frame 0 and continues (infinite loop).

        Returns:
            np.ndarray  — BGR frame (H × W × 3).
            None        — stream broken or not connected; caller should reconnect.
        """
        if not self._connected or self._cap is None:
            return None
        try:
            if not self._is_video_file:
                # Flush accumulated stale frames in OpenCV's buffer to guarantee 0-latency live feed
                for _ in range(3):
                    if not self._cap.grab():
                        break
                ret, frame = self._cap.retrieve()
            else:
                ret, frame = self._cap.read()

            # ── Video file: loop on EOF ───────────────────────────────────────
            if (not ret or frame is None or frame.size == 0) and self._is_video_file:
                self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                logger.info(
                    "Video restarted from beginning | camera_id={cid} | file={f}",
                    cid=self._camera_id,
                    f=self._rtsp_url,
                )
                ret, frame = self._cap.read()

            if not ret or frame is None or frame.size == 0:
                self._connected = False
                logger.warning(
                    "Camera disconnected — read returned no data | camera_id={cid}",
                    cid=self._camera_id,
                )
                return None

            return frame  # type: ignore[return-value]

        except Exception as exc:
            self._connected = False
            logger.error(
                "Camera read exception | camera_id={cid} | error={err}",
                cid=self._camera_id,
                err=str(exc),
            )
            return None

    # ─── Status ───────────────────────────────────────────────────────────────

    @property
    def is_connected(self) -> bool:
        """True when the VideoCapture is open and the last read succeeded."""
        return (
            self._connected
            and self._cap is not None
            and self._cap.isOpened()
        )

    # ─── Cleanup ──────────────────────────────────────────────────────────────

    def close(self) -> None:
        """Release the VideoCapture resource. Safe to call multiple times."""
        self._connected = False
        if self._cap is not None:
            try:
                self._cap.release()
            except Exception:
                pass
            finally:
                self._cap = None
        logger.debug("RTSPClient closed | camera_id={cid}", cid=self._camera_id)
