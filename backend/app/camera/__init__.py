"""RTSP camera infrastructure — Phase 2 streaming layer."""
from app.camera.camera_manager import camera_manager
from app.camera.frame_buffer import FrameBuffer, FrameEntry

__all__ = ["camera_manager", "FrameBuffer", "FrameEntry"]
