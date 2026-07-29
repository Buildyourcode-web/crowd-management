"""Camera configuration API endpoints — Phase 1."""
import asyncio
import uuid
from typing import AsyncGenerator, Optional

import cv2
import numpy as np
from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.responses import StreamingResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.camera.camera_manager import camera_manager
from app.common.response import ApiResponse, PagedResponse
from app.database.connection import get_db
from app.dependencies.auth import get_current_user
from app.schemas.camera import CameraCreate, CameraResponse, CameraUpdate
from app.services.camera.camera_config_service import CameraConfigService
from app.utils.pagination import get_pagination, PaginationParams

router = APIRouter()


def get_service(db: AsyncSession = Depends(get_db)) -> CameraConfigService:
    return CameraConfigService(db)


@router.post(
    "",
    response_model=ApiResponse[CameraResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Add camera",
)
async def add_camera(
    data: CameraCreate,
    request: Request,
    service: CameraConfigService = Depends(get_service),
    current_user: dict = Depends(get_current_user),
):
    camera = await service.add_camera(data)
    return ApiResponse.created(
        data=CameraResponse.model_validate(camera),
        message="Camera added successfully",
        request_id=getattr(request.state, "request_id", None),
    )


@router.get(
    "",
    response_model=PagedResponse[CameraResponse],
    summary="List cameras",
)
async def list_cameras(
    request: Request,
    active_only: bool = Query(default=False, description="Return only active cameras"),
    pagination: PaginationParams = Depends(get_pagination),
    service: CameraConfigService = Depends(get_service),
):
    cameras = await service.list_cameras(
        skip=pagination.offset,
        limit=pagination.page_size,
        active_only=active_only,
    )
    total = await service.count_cameras(active_only=active_only)
    return PagedResponse.build(
        data=[CameraResponse.model_validate(c) for c in cameras],
        page=pagination.page,
        page_size=pagination.page_size,
        total=total,
        request_id=getattr(request.state, "request_id", None),
    )


@router.get(
    "/{camera_id}",
    response_model=ApiResponse[CameraResponse],
    summary="Get camera",
)
async def get_camera(
    camera_id: uuid.UUID,
    request: Request,
    service: CameraConfigService = Depends(get_service),
):
    camera = await service.get_camera(camera_id)
    return ApiResponse.ok(
        data=CameraResponse.model_validate(camera),
        request_id=getattr(request.state, "request_id", None),
    )


@router.put(
    "/{camera_id}",
    response_model=ApiResponse[CameraResponse],
    summary="Edit camera",
)
async def edit_camera(
    camera_id: uuid.UUID,
    data: CameraUpdate,
    request: Request,
    service: CameraConfigService = Depends(get_service),
    current_user: dict = Depends(get_current_user),
):
    camera = await service.edit_camera(camera_id, data)
    return ApiResponse.ok(
        data=CameraResponse.model_validate(camera),
        message="Camera updated successfully",
        request_id=getattr(request.state, "request_id", None),
    )


@router.delete(
    "/{camera_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete camera",
)
async def delete_camera(
    camera_id: uuid.UUID,
    service: CameraConfigService = Depends(get_service),
    current_user: dict = Depends(get_current_user),
):
    await service.delete_camera(camera_id)


@router.post(
    "/{camera_id}/activate",
    response_model=ApiResponse[CameraResponse],
    summary="Activate camera",
)
async def activate_camera(
    camera_id: uuid.UUID,
    request: Request,
    service: CameraConfigService = Depends(get_service),
    current_user: dict = Depends(get_current_user),
):
    camera = await service.activate_camera(camera_id)
    return ApiResponse.ok(
        data=CameraResponse.model_validate(camera),
        message="Camera activated",
        request_id=getattr(request.state, "request_id", None),
    )


@router.post(
    "/{camera_id}/deactivate",
    response_model=ApiResponse[CameraResponse],
    summary="Deactivate camera",
)
async def deactivate_camera(
    camera_id: uuid.UUID,
    request: Request,
    service: CameraConfigService = Depends(get_service),
    current_user: dict = Depends(get_current_user),
):
    camera = await service.deactivate_camera(camera_id)
    return ApiResponse.ok(
        data=CameraResponse.model_validate(camera),
        message="Camera deactivated",
        request_id=getattr(request.state, "request_id", None),
    )


# ─────────────────────────────────────────────────────────────────────────────
# GET /{camera_id}/snapshot  →  Single JPEG frame from FrameBuffer
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/{camera_id}/snapshot",
    summary="Get latest JPEG snapshot from camera",
    response_class=Response,
)
async def camera_snapshot(camera_id: uuid.UUID):
    """Return the latest frame from FrameBuffer as a JPEG image."""
    frame_buffer = camera_manager.frame_buffer

    entry = await frame_buffer.get(camera_id)
    if entry is None or entry.latest_frame is None:
        # Return a grey placeholder image when camera is offline
        placeholder = np.full((480, 640, 3), 50, dtype=np.uint8)
        cv2.putText(placeholder, "Camera Offline", (140, 240),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.4, (100, 100, 255), 2)
        ok, buf = cv2.imencode(".jpg", placeholder)
        return Response(content=buf.tobytes(), media_type="image/jpeg")

    frame = entry.latest_frame.copy()
    ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
    return Response(content=buf.tobytes(), media_type="image/jpeg")


# ─────────────────────────────────────────────────────────────────────────────
# GET /{camera_id}/stream  →  MJPEG live stream (browser-viewable)
# ─────────────────────────────────────────────────────────────────────────────

async def _mjpeg_generator(camera_id: uuid.UUID) -> AsyncGenerator[bytes, None]:
    """Yield MJPEG frames continuously from FrameBuffer."""
    frame_buffer = camera_manager.frame_buffer

    # Offline placeholder frame
    placeholder = np.full((480, 640, 3), 30, dtype=np.uint8)
    cv2.putText(placeholder, "Connecting...", (160, 230),
                cv2.FONT_HERSHEY_SIMPLEX, 1.2, (80, 80, 255), 2)
    cv2.putText(placeholder, str(camera_id)[:18], (80, 270),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1)
    _, ph_buf = cv2.imencode(".jpg", placeholder)
    placeholder_bytes = ph_buf.tobytes()

    last_frame_number = -1
    while True:
        entry = await frame_buffer.get(camera_id)

        if entry is None or entry.latest_frame is None:
            # Camera not yet connected — send placeholder
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n"
                + placeholder_bytes +
                b"\r\n"
            )
            await asyncio.sleep(0.5)
            continue

        # Only encode if frame is new
        if entry.frame_number != last_frame_number:
            last_frame_number = entry.frame_number
            frame = entry.latest_frame.copy()
            h, w = frame.shape[:2]

            from app.person_counter.worker import person_counter_manager
            worker_obj = person_counter_manager._workers.get(str(camera_id))
            worker_status = person_counter_manager.get_status(camera_id)

            # ── Draw bounding boxes for tracked persons ───────────────────────
            if worker_obj is not None:
                for person in worker_obj._latest_tracked:
                    x1, y1 = int(person.x1), int(person.y1)
                    x2, y2 = int(person.x2), int(person.y2)
                    tid = person.track_id
                    conf = person.confidence

                    # 🟢 Green  = not yet crossed the line (eligible to count)
                    # 🔵 Cyan   = already crossed and counted
                    already_counted = tid in worker_obj._counted_ids
                    box_color = (255, 200, 0) if already_counted else (0, 230, 0)

                    # Bounding box
                    cv2.rectangle(frame, (x1, y1), (x2, y2), box_color, 2)

                    # Label: ID + confidence
                    label = f"ID:{tid} {conf:.2f}"
                    lbl_y = max(y1 - 8, 20)
                    cv2.rectangle(frame, (x1, lbl_y - 18), (x1 + len(label) * 10, lbl_y + 4), (0, 0, 0), -1)
                    cv2.putText(frame, label, (x1 + 2, lbl_y),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.55, box_color, 2)

                    # Centroid dot
                    cx, cy = int(person.cx), int(person.cy)
                    cv2.circle(frame, (cx, cy), 5, box_color, -1)

            # ── Draw counting LINE ────────────────────────────────────────────
            if worker_obj and hasattr(worker_obj, '_line'):
                line = worker_obj._line
                lx1 = int(line.start_x)
                ly1 = int(line.start_y)
                lx2 = int(line.end_x)
                ly2 = int(line.end_y)
                # Main line — bright white with black shadow for visibility
                cv2.line(frame, (lx1, ly1), (lx2, ly2), (0, 0, 0), 5)    # shadow
                cv2.line(frame, (lx1, ly1), (lx2, ly2), (255, 255, 255), 2)  # line
                # Small ENTRY/EXIT label above the line
                cv2.putText(frame, "v ENTRY / EXIT ^",
                            (lx1 + 10, ly1 - 8),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)

            # ── Top status bar ────────────────────────────────────────────────
            cv2.rectangle(frame, (0, 0), (w, 52), (0, 0, 0), -1)
            if worker_status is not None:
                status_txt = (
                    f"IN:{worker_status.entry_count}  "
                    f"OUT:{worker_status.exit_count}  "
                    f"INSIDE:{worker_status.current_occupancy}  "
                    f"FPS:{entry.fps:.1f}  "
                    f"PERSONS:{len(worker_obj._latest_tracked) if worker_obj else 0}"
                )
            else:
                status_txt = f"FPS:{entry.fps:.1f} | No counter"
            cv2.putText(frame, status_txt, (10, 35),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2)


            ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
            if ok:
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n"
                    + buf.tobytes() +
                    b"\r\n"
                )

        await asyncio.sleep(0.05)  # ~20 fps max for stream


@router.get(
    "/{camera_id}/stream",
    summary="Live MJPEG stream from camera",
)
async def camera_stream(camera_id: uuid.UUID):
    """Stream live MJPEG video from the camera's FrameBuffer."""
    return StreamingResponse(
        _mjpeg_generator(camera_id),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={"Cache-Control": "no-cache"},
    )


# ─────────────────────────────────────────────────────────────────────────────
# GET /{camera_id}/viewer  →  HTML page with live feed + counter stats
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/{camera_id}/viewer",
    summary="HTML viewer — live feed + person counter",
)
async def camera_viewer(camera_id: uuid.UUID):
    """Serve a standalone HTML page with live MJPEG feed and real-time person counter."""
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Camera Viewer — {camera_id}</title>
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{
      background: #0a0a0f;
      color: #e0e0e0;
      font-family: 'Segoe UI', sans-serif;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 20px;
    }}
    h1 {{
      font-size: 1.2rem;
      color: #7cb9e8;
      margin-bottom: 16px;
      letter-spacing: 2px;
      text-transform: uppercase;
    }}
    .layout {{
      display: grid;
      grid-template-columns: 1fr 300px;
      gap: 16px;
      width: 100%;
      max-width: 1200px;
    }}
    .feed-box {{
      background: #111;
      border: 1px solid #222;
      border-radius: 12px;
      overflow: hidden;
      position: relative;
    }}
    .feed-box img {{
      width: 100%;
      height: auto;
      display: block;
    }}
    .feed-label {{
      position: absolute;
      top: 10px; left: 10px;
      background: rgba(0,0,0,0.6);
      padding: 4px 10px;
      border-radius: 20px;
      font-size: 0.75rem;
      color: #4caf50;
      display: flex; align-items: center; gap: 6px;
    }}
    .dot {{ width: 8px; height: 8px; border-radius: 50%; background: #4caf50; animation: pulse 1.5s infinite; }}
    @keyframes pulse {{ 0%,100% {{ opacity:1; }} 50% {{ opacity:0.3; }} }}
    .stats-panel {{
      display: flex;
      flex-direction: column;
      gap: 12px;
    }}
    .stat-card {{
      background: #111827;
      border: 1px solid #1f2937;
      border-radius: 12px;
      padding: 20px;
      text-align: center;
    }}
    .stat-label {{
      font-size: 0.75rem;
      color: #6b7280;
      text-transform: uppercase;
      letter-spacing: 1px;
      margin-bottom: 8px;
    }}
    .stat-value {{
      font-size: 2.8rem;
      font-weight: 700;
      line-height: 1;
    }}
    .entry {{ color: #22c55e; }}
    .exit  {{ color: #f87171; }}
    .inside{{ color: #60a5fa; }}
    .fps   {{ color: #a78bfa; font-size: 1.4rem; }}
    .status-bar {{
      width: 100%;
      max-width: 1200px;
      background: #111827;
      border: 1px solid #1f2937;
      border-radius: 8px;
      padding: 10px 16px;
      margin-top: 12px;
      font-size: 0.8rem;
      color: #6b7280;
      display: flex;
      justify-content: space-between;
    }}
    .line-indicator {{
      background: #111827;
      border: 1px solid #1f2937;
      border-radius: 12px;
      padding: 16px;
      font-size: 0.78rem;
      color: #9ca3af;
    }}
    .line-indicator h3 {{ color: #d1d5db; margin-bottom: 8px; font-size: 0.9rem; }}
  </style>
</head>
<body>
  <h1>📹 Live Camera Feed + Person Counter</h1>

  <div class="layout">
    <!-- Live MJPEG Feed -->
    <div class="feed-box">
      <img src="/api/v1/cameras/{camera_id}/stream" alt="Live Feed">
      <div class="feed-label">
        <span class="dot"></span> LIVE
      </div>
    </div>

    <!-- Stats Panel -->
    <div class="stats-panel">
      <div class="stat-card">
        <div class="stat-label">Entry Count</div>
        <div class="stat-value entry" id="entry">—</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Exit Count</div>
        <div class="stat-value exit" id="exit">—</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Currently Inside</div>
        <div class="stat-value inside" id="inside">—</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Stream FPS</div>
        <div class="stat-value fps" id="fps">—</div>
      </div>
      <div class="line-indicator">
        <h3>⚡ Counting Line</h3>
        X: start_x → end_x at Y position<br>
        (Configurable via API)<br><br>
        ↑ Cross upward = <span style="color:#f87171">Exit</span><br>
        ↓ Cross downward = <span style="color:#22c55e">Entry</span>
      </div>
    </div>
  </div>

  <div class="status-bar">
    <span>Camera ID: {camera_id}</span>
    <span id="last-update">Last update: —</span>
    <span id="worker-status">Worker: checking...</span>
  </div>

  <script>
    const CAMERA_ID = "{camera_id}";
    const API = "http://127.0.0.1:8000/api/v1";

    async function fetchStats() {{
      try {{
        const res = await fetch(`${{API}}/person-counter/status/${{CAMERA_ID}}`);
        const json = await res.json();
        const d = json.data || {{}};

        document.getElementById("entry").textContent  = d.entry_count  ?? "—";
        document.getElementById("exit").textContent   = d.exit_count   ?? "—";
        document.getElementById("inside").textContent = d.current_inside ?? (d.entry_count - d.exit_count) ?? "—";
        document.getElementById("fps").textContent    = (d.fps ?? 0).toFixed(1);
        document.getElementById("last-update").textContent = "Last update: " + new Date().toLocaleTimeString();
        document.getElementById("worker-status").textContent =
          "Worker: " + (d.worker_running ? "✅ Running" : "❌ Stopped");
      }} catch(e) {{
        document.getElementById("worker-status").textContent = "Worker: ⚠️ API unreachable";
      }}
    }}

    // Poll every 2 seconds
    fetchStats();
    setInterval(fetchStats, 2000);

    // WebSocket for instant updates
    try {{
      const ws = new WebSocket("ws://127.0.0.1:8000/ws/person_counter");
      ws.onmessage = (e) => {{
        const msg = JSON.parse(e.data);
        if (msg.payload?.camera_id === CAMERA_ID) {{
          document.getElementById("entry").textContent  = msg.payload.entry_count  ?? "—";
          document.getElementById("exit").textContent   = msg.payload.exit_count   ?? "—";
          document.getElementById("inside").textContent = msg.payload.current_inside ?? "—";
          document.getElementById("last-update").textContent = "Live ⚡ " + new Date().toLocaleTimeString();
        }}
      }};
    }} catch(e) {{}}
  </script>
</body>
</html>"""
    return Response(content=html, media_type="text/html")


# ─────────────────────────────────────────────────────────────────────────────
# ZONE MONITORING  —  dots-only stream + zone count + alert
# ─────────────────────────────────────────────────────────────────────────────

async def _zone_mjpeg_generator(
    camera_id: uuid.UUID,
    zone_x1: int, zone_y1: int,
    zone_x2: int, zone_y2: int,
    threshold: int,
) -> AsyncGenerator[bytes, None]:
    """MJPEG frames: dots for people, coloured zone, alert banner when over threshold."""
    frame_buffer = camera_manager.frame_buffer

    placeholder = np.full((480, 640, 3), 20, dtype=np.uint8)
    cv2.putText(placeholder, "Connecting...", (150, 230),
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (80, 140, 255), 2)
    _, ph_buf = cv2.imencode(".jpg", placeholder)
    placeholder_bytes = ph_buf.tobytes()

    last_frame_number = -1
    while True:
        entry = await frame_buffer.get(camera_id)
        if entry is None or entry.latest_frame is None:
            yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n"
                   + placeholder_bytes + b"\r\n")
            await asyncio.sleep(0.5)
            continue

        if entry.frame_number != last_frame_number:
            last_frame_number = entry.frame_number
            frame = entry.latest_frame.copy()
            h, w = frame.shape[:2]

            # Clamp zone to frame
            zx1 = max(0, min(zone_x1, w - 1))
            zy1 = max(0, min(zone_y1, h - 1))
            zx2 = max(0, min(zone_x2, w - 1))
            zy2 = max(0, min(zone_y2, h - 1))

            from app.person_counter.worker import person_counter_manager
            worker_obj = person_counter_manager._workers.get(str(camera_id))
            tracked = worker_obj._latest_tracked if worker_obj else []

            # ── Count people in zone + draw dots ─────────────────────────────
            in_zone = 0
            for person in tracked:
                cx, cy = int(person.cx), int(person.cy)
                inside = (zx1 <= cx <= zx2 and zy1 <= cy <= zy2)
                if inside:
                    in_zone += 1
                    # Bright red/orange dot — inside zone
                    cv2.circle(frame, (cx, cy), 12, (0, 30, 200), -1)
                    cv2.circle(frame, (cx, cy), 12, (0, 80, 255), 3)
                    cv2.circle(frame, (cx, cy), 4,  (255, 255, 255), -1)
                else:
                    # Dim grey dot — outside zone
                    cv2.circle(frame, (cx, cy), 9, (160, 160, 160), -1)
                    cv2.circle(frame, (cx, cy), 9, (100, 100, 100), 2)

            alert = in_zone > threshold

            # ── Draw zone rectangle ───────────────────────────────────────────
            zone_color = (0, 40, 230) if alert else (30, 200, 80)
            overlay = frame.copy()
            cv2.rectangle(overlay, (zx1, zy1), (zx2, zy2), zone_color, -1)
            alpha = 0.22 if alert else 0.12
            cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)
            cv2.rectangle(frame, (zx1, zy1), (zx2, zy2), zone_color, 3)

            # Zone label above rectangle
            tag = f"  ZONE: {in_zone} person{'s' if in_zone != 1 else ''}  {'⚠ ALERT' if alert else '✓ OK'}  "
            tag_color = (0, 30, 230) if alert else (20, 180, 60)
            (tw, th), _ = cv2.getTextSize(tag, cv2.FONT_HERSHEY_SIMPLEX, 0.75, 2)
            ty = max(zy1 - 8, th + 4)
            cv2.rectangle(frame, (zx1, ty - th - 6), (zx1 + tw + 4, ty + 4), (0, 0, 0), -1)
            cv2.putText(frame, tag, (zx1 + 2, ty),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.75, tag_color, 2)

            # ── Alert banner (top of frame) ───────────────────────────────────
            if alert:
                banner = frame[0:58].copy()
                frame[0:58] = [0, 0, 160]
                cv2.addWeighted(frame[0:58], 0.75, banner, 0.25, 0, frame[0:58])
                msg = f"  ⚠  CROWD ALERT — {in_zone} people in zone  (threshold: {threshold})"
                cv2.putText(frame, msg, (8, 38),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.85, (255, 255, 255), 2)

            # ── Bottom status bar ─────────────────────────────────────────────
            cv2.rectangle(frame, (0, h - 38), (w, h), (10, 10, 20), -1)
            status_txt = (
                f"IN ZONE: {in_zone}  |  TOTAL DETECTED: {len(tracked)}"
                f"  |  THRESHOLD: {threshold}  |  {'⚠ ALERT' if alert else 'OK'}"
            )
            bar_color = (60, 80, 255) if alert else (60, 200, 100)
            cv2.putText(frame, status_txt, (10, h - 14),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.52, bar_color, 1)

            ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 82])
            if ok:
                yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n"
                       + buf.tobytes() + b"\r\n")

        await asyncio.sleep(0.033)


@router.get(
    "/{camera_id}/zone-stream",
    summary="Zone monitoring — MJPEG stream (dots only, no bounding boxes)",
)
async def zone_stream(
    camera_id: uuid.UUID,
    x1: int = Query(default=0,    description="Zone left edge (pixels)"),
    y1: int = Query(default=0,    description="Zone top edge (pixels)"),
    x2: int = Query(default=1920, description="Zone right edge (pixels)"),
    y2: int = Query(default=1080, description="Zone bottom edge (pixels)"),
    threshold: int = Query(default=5, description="Alert when people in zone exceed this"),
):
    """Live MJPEG stream with dot markers for each person and zone monitoring."""
    return StreamingResponse(
        _zone_mjpeg_generator(camera_id, x1, y1, x2, y2, threshold),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={"Cache-Control": "no-cache"},
    )


@router.get(
    "/{camera_id}/zone-status",
    summary="Zone count — current JSON status",
)
async def zone_status(
    camera_id: uuid.UUID,
    x1: int = Query(default=0),
    y1: int = Query(default=0),
    x2: int = Query(default=1920),
    y2: int = Query(default=1080),
    threshold: int = Query(default=5),
):
    """Return current count of people inside the zone + alert flag."""
    from app.person_counter.worker import person_counter_manager
    worker_obj = person_counter_manager._workers.get(str(camera_id))
    tracked = worker_obj._latest_tracked if worker_obj else []

    in_zone = sum(
        1 for p in tracked
        if x1 <= p.cx <= x2 and y1 <= p.cy <= y2
    )
    return {
        "camera_id": str(camera_id),
        "zone": {"x1": x1, "y1": y1, "x2": x2, "y2": y2},
        "in_zone": in_zone,
        "total_detected": len(tracked),
        "threshold": threshold,
        "alert": in_zone > threshold,
    }


@router.get(
    "/{camera_id}/zone-viewer",
    summary="Zone monitoring — HTML viewer (dots + zone + alert)",
)
async def zone_viewer(
    camera_id: uuid.UUID,
    x1: int = Query(default=0),
    y1: int = Query(default=0),
    x2: int = Query(default=1920),
    y2: int = Query(default=1080),
    threshold: int = Query(default=5),
):
    """Premium HTML viewer for zone-based crowd monitoring."""
    zone_params = f"x1={x1}&y1={y1}&x2={x2}&y2={y2}&threshold={threshold}"
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Zone Monitor — {camera_id}</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
    * {{ margin:0; padding:0; box-sizing:border-box; }}
    body {{
      background: #06060f;
      color: #e0e0f0;
      font-family: 'Inter', 'Segoe UI', sans-serif;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 20px;
      gap: 16px;
    }}
    h1 {{
      font-size: 1.1rem;
      letter-spacing: 3px;
      text-transform: uppercase;
      color: #818cf8;
      display: flex;
      align-items: center;
      gap: 10px;
    }}
    .layout {{
      display: grid;
      grid-template-columns: 1fr 280px;
      gap: 16px;
      width: 100%;
      max-width: 1280px;
    }}
    .feed-box {{
      background: #0d0d1a;
      border: 1px solid #1e1e3a;
      border-radius: 14px;
      overflow: hidden;
      position: relative;
    }}
    .feed-box img {{ width:100%; height:auto; display:block; }}
    .live-badge {{
      position: absolute;
      top: 12px; left: 12px;
      background: rgba(0,0,0,0.65);
      padding: 5px 12px;
      border-radius: 20px;
      font-size: 0.72rem;
      color: #4ade80;
      display: flex; align-items: center; gap: 6px;
      backdrop-filter: blur(4px);
    }}
    .pulse {{ width:8px; height:8px; border-radius:50%; background:#4ade80;
              animation: pulse 1.5s ease-in-out infinite; }}
    @keyframes pulse {{ 0%,100%{{opacity:1;transform:scale(1);}} 50%{{opacity:0.4;transform:scale(0.8);}} }}

    .panel {{
      display: flex;
      flex-direction: column;
      gap: 12px;
    }}
    .card {{
      background: #0f0f1e;
      border: 1px solid #1e1e38;
      border-radius: 14px;
      padding: 20px;
      text-align: center;
      transition: border-color 0.3s;
    }}
    .card.alert-active {{
      border-color: #ef4444;
      box-shadow: 0 0 20px rgba(239,68,68,0.3);
      animation: alertFlash 0.8s ease-in-out infinite alternate;
    }}
    @keyframes alertFlash {{
      from {{ box-shadow: 0 0 10px rgba(239,68,68,0.2); }}
      to   {{ box-shadow: 0 0 30px rgba(239,68,68,0.6); }}
    }}
    .card-label {{
      font-size: 0.68rem;
      color: #6b7280;
      text-transform: uppercase;
      letter-spacing: 1.5px;
      margin-bottom: 10px;
    }}
    .card-value {{
      font-size: 3.4rem;
      font-weight: 800;
      line-height: 1;
    }}
    .v-zone  {{ color: #f59e0b; }}
    .v-total {{ color: #60a5fa; }}
    .v-fps   {{ color: #a78bfa; font-size: 1.6rem; }}

    .alert-banner {{
      background: linear-gradient(135deg, #7f1d1d, #991b1b);
      border: 1px solid #ef4444;
      border-radius: 12px;
      padding: 14px 16px;
      text-align: center;
      font-weight: 700;
      color: #fca5a5;
      font-size: 0.85rem;
      display: none;
      animation: alertFlash 0.8s ease-in-out infinite alternate;
    }}
    .alert-banner.visible {{ display: block; }}

    .ok-banner {{
      background: #052e16;
      border: 1px solid #16a34a;
      border-radius: 12px;
      padding: 14px 16px;
      text-align: center;
      font-weight: 600;
      color: #4ade80;
      font-size: 0.85rem;
    }}

    .zone-info {{
      background: #0f0f1e;
      border: 1px solid #1e1e38;
      border-radius: 12px;
      padding: 14px 16px;
      font-size: 0.75rem;
      color: #6b7280;
      line-height: 1.7;
    }}
    .zone-info b {{ color: #9ca3af; }}

    .status-bar {{
      width: 100%;
      max-width: 1280px;
      background: #0f0f1e;
      border: 1px solid #1e1e38;
      border-radius: 8px;
      padding: 10px 18px;
      font-size: 0.75rem;
      color: #6b7280;
      display: flex;
      justify-content: space-between;
    }}

    /* Dot legend */
    .legend {{
      display: flex;
      gap: 14px;
      font-size: 0.72rem;
      color: #6b7280;
      align-items: center;
      flex-wrap: wrap;
    }}
    .dot-in  {{ display:inline-block; width:10px; height:10px; border-radius:50%;
                background:#e02020; margin-right:4px; vertical-align:middle; }}
    .dot-out {{ display:inline-block; width:9px;  height:9px;  border-radius:50%;
                background:#a0a0a0; margin-right:4px; vertical-align:middle; }}
  </style>
</head>
<body>
  <h1>🎯 Zone Monitoring — Person Density</h1>

  <div class="layout">
    <!-- Live zone stream (dots only) -->
    <div class="feed-box">
      <img src="/api/v1/cameras/{camera_id}/zone-stream?{zone_params}" alt="Zone Feed" id="feed">
      <div class="live-badge">
        <span class="pulse"></span> LIVE ZONE MONITOR
      </div>
    </div>

    <!-- Stats panel -->
    <div class="panel">
      <div class="alert-banner" id="alert-banner">
        ⚠️ CROWD ALERT<br>Zone occupancy exceeds threshold!
      </div>

      <div class="card" id="zone-card">
        <div class="card-label">In Zone</div>
        <div class="card-value v-zone" id="in-zone">—</div>
      </div>

      <div class="card">
        <div class="card-label">Total Detected</div>
        <div class="card-value v-total" id="total-detected">—</div>
      </div>

      <div class="card">
        <div class="card-label">Alert Threshold</div>
        <div class="card-value v-fps">&gt; {threshold}</div>
      </div>

      <div class="ok-banner" id="ok-banner">✓ Zone OK — capacity normal</div>

      <div class="zone-info">
        <b>Zone Coordinates</b><br>
        X: {x1} → {x2} px<br>
        Y: {y1} → {y2} px<br><br>
        <b>Dot legend:</b><br>
        <div class="legend">
          <span><span class="dot-in"></span>Inside zone</span>
          <span><span class="dot-out"></span>Outside zone</span>
        </div>
      </div>
    </div>
  </div>

  <div class="status-bar">
    <span>Camera: {camera_id}</span>
    <span id="last-update">Last update: —</span>
    <span id="worker-status">Status: checking...</span>
  </div>

  <script>
    const CAMERA_ID = "{camera_id}";
    const API = "http://127.0.0.1:8000/api/v1";
    const ZONE_PARAMS = "{zone_params}";
    const THRESHOLD = {threshold};

    async function fetchZoneStatus() {{
      try {{
        const res = await fetch(`${{API}}/cameras/${{CAMERA_ID}}/zone-status?${{ZONE_PARAMS}}`);
        const d = await res.json();

        document.getElementById("in-zone").textContent = d.in_zone ?? "—";
        document.getElementById("total-detected").textContent = d.total_detected ?? "—";
        document.getElementById("last-update").textContent = "Last update: " + new Date().toLocaleTimeString();

        const alertBanner = document.getElementById("alert-banner");
        const okBanner    = document.getElementById("ok-banner");
        const zoneCard    = document.getElementById("zone-card");

        if (d.alert) {{
          alertBanner.classList.add("visible");
          okBanner.style.display = "none";
          zoneCard.classList.add("alert-active");
          document.getElementById("worker-status").textContent = "⚠ ALERT — zone overcrowded";
        }} else {{
          alertBanner.classList.remove("visible");
          okBanner.style.display = "block";
          zoneCard.classList.remove("alert-active");
          document.getElementById("worker-status").textContent = "✅ Zone OK";
        }}
      }} catch(e) {{
        document.getElementById("worker-status").textContent = "⚠️ API unreachable";
      }}
    }}

    fetchZoneStatus();
    setInterval(fetchZoneStatus, 1500);
  </script>
</body>
</html>"""
    return Response(content=html, media_type="text/html")



# ─────────────────────────────────────────────────────────────────────────────
# QUEUE MANAGEMENT STREAM + VIEWER  —  live camera + ROI + 5-level metrics
# ─────────────────────────────────────────────────────────────────────────────

_HEALTH_COLORS_BGR = {
    "MOVING":    (60,  210, 60),
    "SLOW":      (200, 200, 40),
    "VERY SLOW": (30,  160, 255),
    "BLOCKED":   (40,  40,  230),
    "EMPTY":     (140, 140, 140),
    "UNKNOWN":   (140, 140, 140),
}


async def _queue_mjpeg_generator(
    camera_id: uuid.UUID,
    qx1: int, qy1: int, qx2: int, qy2: int,
) -> AsyncGenerator[bytes, None]:
    """MJPEG frames with queue ROI + dots + 5-level metric overlay."""
    frame_buffer = camera_manager.frame_buffer

    placeholder = np.full((480, 640, 3), 18, dtype=np.uint8)
    cv2.putText(placeholder, "Waiting for queue worker...", (50, 230),
                cv2.FONT_HERSHEY_SIMPLEX, 0.85, (80, 140, 255), 2)
    _, ph_buf = cv2.imencode(".jpg", placeholder)
    ph_bytes = ph_buf.tobytes()

    last_fn = -1
    while True:
        entry = await frame_buffer.get(camera_id)
        if entry is None or entry.latest_frame is None:
            yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + ph_bytes + b"\r\n"
            await asyncio.sleep(0.5)
            continue

        if entry.frame_number != last_fn:
            last_fn = entry.frame_number
            frame = entry.latest_frame.copy()
            h, w = frame.shape[:2]

            # Clamp ROI
            rx1 = max(0, min(qx1, w - 1))
            ry1 = max(0, min(qy1, h - 1))
            rx2 = max(0, min(qx2, w - 1))
            ry2 = max(0, min(qy2, h - 1))

            # ── Fetch metrics ─────────────────────────────────────────────────
            from app.queue_management.manager import queue_manager
            from app.person_counter.worker import person_counter_manager

            qs = queue_manager.get_status(camera_id)
            worker_obj = person_counter_manager._workers.get(str(camera_id))
            tracked = worker_obj._latest_tracked if worker_obj else []

            people     = qs.people_inside_queue if qs else 0
            speed      = qs.speed_px_per_sec    if qs else 0.0
            movement   = qs.movement_px          if qs else 0.0
            health     = qs.queue_health         if qs else "UNKNOWN"
            stag_sec   = qs.stagnation_seconds   if qs else 0.0
            stag_label = qs.stagnation_label     if qs else "OK"
            q_stat     = qs.queue_status         if qs else "EMPTY"

            hbgr = _HEALTH_COLORS_BGR.get(health, (140, 140, 140))
            is_crit = stag_label == "CRITICAL"

            # ── People dots ───────────────────────────────────────────────────
            for p in tracked:
                cx, cy = int(p.cx), int(p.cy)
                inside = rx1 <= cx <= rx2 and ry1 <= cy <= ry2
                if inside:
                    cv2.circle(frame, (cx, cy), 12, (0, 30, 200), -1)
                    cv2.circle(frame, (cx, cy), 12, (0, 80, 255), 3)
                    cv2.circle(frame, (cx, cy), 4,  (255, 255, 255), -1)
                else:
                    cv2.circle(frame, (cx, cy), 8, (160, 160, 160), -1)
                    cv2.circle(frame, (cx, cy), 8, (100, 100, 100), 2)

            # ── Queue ROI rectangle ───────────────────────────────────────────
            ov = frame.copy()
            cv2.rectangle(ov, (rx1, ry1), (rx2, ry2), hbgr, -1)
            cv2.addWeighted(ov, 0.14, frame, 0.86, 0, frame)
            cv2.rectangle(frame, (rx1, ry1), (rx2, ry2), hbgr, 3)

            tag = f"  {health}  |  {q_stat}  |  {people} people  "
            (tw, th), _ = cv2.getTextSize(tag, cv2.FONT_HERSHEY_SIMPLEX, 0.70, 2)
            ty = max(ry1 - 8, th + 6)
            cv2.rectangle(frame, (rx1, ty - th - 6), (rx1 + tw + 4, ty + 4), (10, 10, 20), -1)
            cv2.putText(frame, tag, (rx1 + 2, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.70, hbgr, 2)

            # ── Alert banner ──────────────────────────────────────────────────
            if is_crit:
                bc = frame[0:54].copy()
                frame[0:54] = (20, 20, 180)
                cv2.addWeighted(frame[0:54], 0.75, bc, 0.25, 0, frame[0:54])
                cv2.putText(frame,
                    f"  CRITICAL — Blocked {stag_sec:.0f}s | IMMEDIATE ACTION",
                    (8, 34), cv2.FONT_HERSHEY_SIMPLEX, 0.82, (255, 255, 255), 2)
            elif stag_label == "BLOCKED":
                bc = frame[0:44].copy()
                frame[0:44] = (20, 80, 200)
                cv2.addWeighted(frame[0:44], 0.70, bc, 0.30, 0, frame[0:44])
                cv2.putText(frame, f"  WARNING — Queue stagnant {stag_sec:.0f}s",
                    (8, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.76, (255, 255, 255), 2)

            # ── Bottom bar ────────────────────────────────────────────────────
            cv2.rectangle(frame, (0, h - 40), (w, h), (10, 10, 20), -1)
            cv2.putText(frame,
                f"People:{people}  Speed:{speed:.1f}px/s  Mvt:{movement:.1f}px"
                f"  Health:{health}  Stagnation:{stag_sec:.0f}s [{stag_label}]",
                (8, h - 14), cv2.FONT_HERSHEY_SIMPLEX, 0.50, hbgr, 1)

            ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 82])
            if ok:
                yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + buf.tobytes() + b"\r\n"

        await asyncio.sleep(0.033)


@router.get("/{camera_id}/queue-stream",
            summary="Queue management — MJPEG stream with ROI + metrics overlay")
async def queue_mgmt_stream(
    camera_id: uuid.UUID,
    x1: int = Query(default=0),
    y1: int = Query(default=0),
    x2: int = Query(default=1920),
    y2: int = Query(default=1080),
):
    """Live MJPEG stream: camera feed + queue ROI + dots + 5-level metric bar."""
    return StreamingResponse(
        _queue_mjpeg_generator(camera_id, x1, y1, x2, y2),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={"Cache-Control": "no-cache"},
    )


@router.get("/{camera_id}/queue-viewer",
            summary="Queue management — premium HTML viewer (all 5 levels)")
async def queue_mgmt_viewer(
    camera_id: uuid.UUID,
    x1: int = Query(default=0),
    y1: int = Query(default=0),
    x2: int = Query(default=1920),
    y2: int = Query(default=1080),
):
    """Premium HTML viewer: live camera + queue ROI + animated 5-level dashboard."""
    cam_id = str(camera_id)
    qp = f"x1={x1}&y1={y1}&x2={x2}&y2={y2}"
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1.0">
  <title>Queue Monitor — {cam_id[:8]}</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;800;900&display=swap');
    *{{margin:0;padding:0;box-sizing:border-box}}
    body{{background:#06060f;color:#e2e2f0;font-family:'Inter','Segoe UI',sans-serif;
          min-height:100vh;display:flex;flex-direction:column;align-items:center;padding:16px;gap:14px}}
    header{{display:flex;align-items:center;gap:10px;font-size:.78rem;letter-spacing:3px;
            text-transform:uppercase;color:#818cf8}}
    .dot{{width:8px;height:8px;border-radius:50%;background:#4ade80;
          animation:pulse 1.4s ease-in-out infinite}}
    @keyframes pulse{{0%,100%{{opacity:1;transform:scale(1)}}50%{{opacity:.4;transform:scale(.7)}}}}
    .layout{{display:grid;grid-template-columns:1fr 296px;gap:14px;width:100%;max-width:1360px}}
    .feed-wrap{{background:#0b0b1a;border:1px solid #1a1a30;border-radius:14px;
                overflow:hidden;position:relative}}
    .feed-wrap img{{width:100%;height:auto;display:block}}
    .live-tag{{position:absolute;top:12px;left:12px;background:rgba(0,0,0,.65);
               backdrop-filter:blur(4px);padding:5px 14px;border-radius:20px;
               font-size:.68rem;color:#4ade80;display:flex;align-items:center;gap:6px}}
    .panel{{display:flex;flex-direction:column;gap:10px}}
    .card{{background:#0e0e1e;border:1px solid #1e1e38;border-radius:13px;
           padding:15px 17px;transition:border-color .35s,box-shadow .35s}}
    .lbl{{font-size:.62rem;text-transform:uppercase;letter-spacing:1.8px;color:#6b7280;margin-bottom:8px}}
    .val{{font-size:2.5rem;font-weight:900;line-height:1}}
    .sub{{font-size:.73rem;color:#6b7280;margin-top:5px}}
    .c-purple{{color:#a78bfa}}.c-cyan{{color:#22d3ee}}.c-green{{color:#4ade80}}
    .c-amber{{color:#f59e0b}}.c-red{{color:#f87171}}.c-gray{{color:#9ca3af}}
    .card.bl{{border-color:#f59e0b;box-shadow:0 0 16px rgba(245,158,11,.25)}}
    .card.cr{{border-color:#ef4444;animation:cf .7s ease-in-out infinite alternate}}
    @keyframes cf{{from{{box-shadow:0 0 10px rgba(239,68,68,.2)}}to{{box-shadow:0 0 34px rgba(239,68,68,.6)}}}}
    .badge{{display:inline-block;padding:5px 16px;border-radius:20px;font-size:.72rem;font-weight:700}}
    .bm{{background:#052e16;color:#4ade80;border:1px solid #16a34a}}
    .bs{{background:#1c3a3a;color:#22d3ee;border:1px solid #0e7490}}
    .bv{{background:#2a2400;color:#f59e0b;border:1px solid #b45309}}
    .bb{{background:#2a0e0e;color:#f87171;border:1px solid #b91c1c}}
    .be{{background:#18181b;color:#71717a;border:1px solid #3f3f46}}
    .meter-bg{{height:6px;border-radius:3px;background:#1e1e38;overflow:hidden;margin-top:8px}}
    .meter-fill{{height:100%;border-radius:3px;transition:width .6s,background .6s}}
    .stag-ring{{width:76px;height:76px;border-radius:50%;display:flex;align-items:center;
                justify-content:center;font-size:1.05rem;font-weight:800;margin:2px auto 6px;
                border:3px solid #1e1e38;transition:border-color .4s,color .4s}}
    .ab{{border-radius:11px;padding:12px 15px;text-align:center;font-weight:700;
         font-size:.8rem;display:none;animation:cf .7s ease-in-out infinite alternate}}
    .ab.show{{display:block}}
    .ab.bl2{{background:#1c0a00;border:1px solid #f59e0b;color:#fcd34d}}
    .ab.cr2{{background:#1a0202;border:1px solid #ef4444;color:#fca5a5}}
    .roi-info{{font-size:.7rem;color:#6b7280;line-height:1.8}}
    .roi-info b{{color:#9ca3af}}
    .footer{{width:100%;max-width:1360px;background:#0e0e1e;border:1px solid #1e1e38;
             border-radius:8px;padding:8px 16px;font-size:.7rem;color:#6b7280;
             display:flex;justify-content:space-between}}
  </style>
</head>
<body>
<header><span class="dot"></span>Queue Management — 5-Level Live Monitor</header>

<div class="layout">
  <div class="feed-wrap">
    <img src="/api/v1/cameras/{cam_id}/queue-stream?{qp}" alt="Queue Feed">
    <div class="live-tag"><span class="dot"></span>LIVE CAMERA</div>
  </div>

  <div class="panel">
    <div class="ab bl2" id="ab-bl">⚠️ Queue Stagnant — consider intervention</div>
    <div class="ab cr2" id="ab-cr">🚨 CRITICAL — Immediate action required!</div>

    <div class="card">
      <div class="lbl">Level 1 · Occupancy</div>
      <div class="val c-purple" id="people">—</div>
      <div class="sub">Status: <span id="q-status" class="c-purple">—</span></div>
    </div>

    <div class="card">
      <div class="lbl">Level 2 & 3 · Movement · Speed</div>
      <div class="val c-cyan" id="speed-val">—</div>
      <div class="sub">Movement: <span id="mvt">—</span> px/frame</div>
      <div class="meter-bg"><div class="meter-fill" id="meter" style="width:0%;background:#22d3ee"></div></div>
    </div>

    <div class="card" id="hcard">
      <div class="lbl">Level 4 · Queue Health</div>
      <div style="margin-top:6px"><span class="badge be" id="hbadge">—</span></div>
    </div>

    <div class="card" id="scard">
      <div class="lbl">Level 5 · Stagnation</div>
      <div class="stag-ring" id="sring">0s</div>
      <div class="sub" style="text-align:center">Label: <span id="slabel" class="c-green">OK</span></div>
    </div>

    <div class="card roi-info">
      <b>Queue ROI</b><br>
      X: {x1} → {x2} px<br>Y: {y1} → {y2} px<br><br>
      <span style="margin-right:12px">🔴 Inside queue</span><span>⚫ Outside queue</span>
    </div>
  </div>
</div>

<div class="footer">
  <span>Camera: {cam_id}</span>
  <span id="ts">—</span>
  <span id="ws">Connecting...</span>
</div>

<script>
const CAM="{cam_id}",API="http://127.0.0.1:8000/api/v1";
const HCOL={{"MOVING":"#4ade80","SLOW":"#22d3ee","VERY SLOW":"#f59e0b","BLOCKED":"#f87171","EMPTY":"#9ca3af","UNKNOWN":"#9ca3af"}};
const BADGE={{"MOVING":["bm","MOVING ▶"],"SLOW":["bs","SLOW ↘"],"VERY SLOW":["bv","VERY SLOW ⚠"],"BLOCKED":["bb","BLOCKED ✖"],"EMPTY":["be","EMPTY"],"UNKNOWN":["be","UNKNOWN"]}};

async function poll(){{
  try{{
    const r=await fetch(`${{API}}/queue/status/${{CAM}}`);
    const j=await r.json();
    const d=j.data??j;
    const people=d.people_inside_queue??0,speed=d.speed_px_per_sec??0,
          mvt=d.movement_px??0,health=d.queue_health??"UNKNOWN",
          ss=d.stagnation_seconds??0,sl=d.stagnation_label??"OK",
          qs=d.queue_status??"EMPTY";

    document.getElementById("people").textContent=people;
    document.getElementById("q-status").textContent=qs;
    document.getElementById("speed-val").innerHTML=
      `${{speed.toFixed(1)}} <span style="font-size:.9rem;font-weight:400;color:#6b7280">px/s</span>`;
    document.getElementById("mvt").textContent=mvt.toFixed(1);

    const pct=Math.min((speed/30)*100,100),col=HCOL[health]??"#9ca3af";
    const m=document.getElementById("meter");
    m.style.width=pct+"%"; m.style.background=col;

    const [bc,bt]=BADGE[health]??["be","—"];
    const b=document.getElementById("hbadge");
    b.className="badge "+bc; b.textContent=bt;
    document.getElementById("hcard").className=
      health==="BLOCKED"?"card bl":health==="VERY SLOW"?"card bl":"card";

    const sr=document.getElementById("sring");
    sr.textContent=ss<60?`${{Math.round(ss)}}s`:`${{(ss/60).toFixed(1)}}m`;
    sr.style.color=sl==="CRITICAL"?"#f87171":sl==="BLOCKED"?"#fcd34d":"#4ade80";
    sr.style.borderColor=sl==="CRITICAL"?"#ef4444":sl==="BLOCKED"?"#f59e0b":"#1e1e38";
    document.getElementById("scard").className=
      sl==="CRITICAL"?"card cr":sl==="BLOCKED"?"card bl":"card";

    const slEl=document.getElementById("slabel");
    slEl.textContent=sl;
    slEl.className=sl==="CRITICAL"?"c-red":sl==="BLOCKED"?"c-amber":"c-green";

    document.getElementById("ab-bl").classList.toggle("show",sl==="BLOCKED");
    document.getElementById("ab-cr").classList.toggle("show",sl==="CRITICAL");

    document.getElementById("ts").textContent="Updated: "+new Date().toLocaleTimeString();
    document.getElementById("ws").textContent=d.worker_running?"✅ Worker active":"⚠️ Worker stopped";
  }}catch(e){{
    document.getElementById("ws").textContent="⚠️ API unreachable";
  }}
}}
poll(); setInterval(poll,1500);
</script>
</body>
</html>"""
    return Response(content=html, media_type="text/html")
