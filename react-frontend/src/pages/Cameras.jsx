import React, { useState, useEffect, useRef, useCallback } from 'react';
import DashboardLayout from '../components/layout/DashboardLayout';
import { fetchCameras } from '../services/api';

const CAM_BASE = import.meta.env.VITE_CAMERAS_API_URL || 'http://127.0.0.1:8000/api/v1';

/**
 * Camera card – identical to the inline template in cameras.blade.php
 */
function CameraCard({ cam, onZoom }) {
  const cid = String(cam.id || cam.camera_id || '');
  const isQueueCam = cid.includes('4e09b542') || cid.includes('67676767') || cam.camera_type === 'QUEUE';
  const streamSrc  = isQueueCam
    ? `/api/v1/cameras/${cam.id || cam.camera_id}/queue-stream`
    : (cam.stream_url || `${CAM_BASE}/cameras/${cam.id || cam.camera_id}/stream`);

  const camName   = cam.name  || cam.camera_name  || `Camera ${cam.id || ''}`;
  const zoneName  = cam.zone_name || cam.zone || 'Main Zone';

  const [timeStr, setTimeStr] = useState(() => new Date().toLocaleTimeString());
  useEffect(() => {
    const t = setInterval(() => setTimeStr(new Date().toLocaleTimeString()), 1000);
    return () => clearInterval(t);
  }, []);

  return (
    <div
      className="camera-card"
      id={`camera-card-${cam.id || '1'}`}
      onClick={() => onZoom(camName, streamSrc, cam.id || cam.camera_id, isQueueCam)}
    >
      <div className="camera-video-container">
        <img
          src={streamSrc}
          onError={e => {
            if (!isQueueCam) {
              e.target.src = '/images/detection-placeholder.jpg';
            }
          }}
          alt={camName}
          className="camera-video-placeholder"
          style={{ width: '100%', height: '100%', objectFit: 'cover', opacity: 1, backgroundColor: '#000' }}
        />
        <div className="camera-scanner-overlay"></div>
        <div className="camera-scanline"></div>
        <div className="camera-telemetry">
          <span className="camera-rec-dot">
            <span className="rec-dot"></span> LIVE
          </span>
          <span className="camera-timestamp font-numeric">REC // {timeStr}</span>
        </div>
        <div className="camera-name-overlay">{camName} [{zoneName}]</div>
      </div>
    </div>
  );
}

/**
 * Fullscreen CCTV zoom modal – replicates the cctv-zoom-modal in cameras.blade.php
 */
function CctvZoomModal({ isOpen, cameraName, streamSrc, camId, isQueueCam, onClose }) {
  const [timeStr, setTimeStr] = useState(() => new Date().toLocaleTimeString());
  useEffect(() => {
    if (!isOpen) return;
    const t = setInterval(() => setTimeStr(new Date().toLocaleTimeString()), 1000);
    return () => clearInterval(t);
  }, [isOpen]);

  useEffect(() => {
    function onKey(e) { if (e.key === 'Escape') onClose(); }
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [onClose]);

  if (!isOpen) return null;

  const isQueue = Boolean(isQueueCam) || (streamSrc || '').includes('queue') || (camId || '').includes('4e09b542') || (camId || '').includes('67676767');
  const viewerUrl = `/api/v1/cameras/${camId || '4e09b542-98b1-4974-9e6c-8f3a8c3d7f0a'}/queue-viewer`;

  return (
    <div
      id="cctv-zoom-modal"
      className="cctv-zoom-modal active"
      onClick={onClose}
    >
      <button type="button" className="btn-close-zoom" onClick={onClose}>&times;</button>
      <div className="zoom-content-wrapper" onClick={e => e.stopPropagation()} style={{ width: '96vw', height: '94vh', padding: 0, borderRadius: '14px', overflow: 'hidden' }}>
        {isQueue ? (
          <iframe
            src={viewerUrl}
            title={`${cameraName} — 5-Level Live Viewer`}
            style={{ width: '100%', height: '100%', border: 'none' }}
          />
        ) : (
          <>
            <img
              id="zoomed-camera-img"
              src={streamSrc}
              alt="CCTV Zoomed Feed"
              className="zoomed-camera-img"
              onError={e => { e.target.src = '/images/detection-placeholder.jpg'; }}
            />
            <div className="camera-telemetry" style={{ top: '16px', left: '16px', right: '16px' }}>
              <span className="camera-rec-dot" style={{ fontSize: '13px' }}>
                <span className="rec-dot" style={{ width: '9px', height: '9px' }}></span> LIVE CCTV FEED
              </span>
              <span id="zoomed-camera-name" className="zoomed-camera-name">{cameraName}</span>
              <span className="camera-timestamp font-numeric" style={{ fontSize: '13px' }}>
                REC // {timeStr}
              </span>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

/**
 * CCTV Grid page – pixel-identical to dashboard/cameras.blade.php
 * Includes all inline CSS from that file via a <style> tag.
 */
export default function Cameras() {
  const [cameras, setCameras] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState(false);
  const [zoomCam, setZoomCam] = useState(null); // { name, src, camId, isQueueCam }

  const loadCameras = useCallback(async () => {
    setLoading(true);
    setError(false);
    try {
      const data = await fetchCameras();
      setCameras(data);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadCameras(); }, [loadCameras]);

  // Construct 12 total CCTV camera slots
  const TOTAL_SCREENS = 12;
  const displayCameras = Array.from({ length: TOTAL_SCREENS }, (_, idx) => {
    const existing = cameras[idx];

    // Default slots for 12 CCTV screens
    if (idx === 0) {
      return {
        id: '4e09b542-98b1-4974-9e6c-8f3a8c3d7f0a',
        name: 'Queue Monitor 1 — 4e09b542',
        stream_url: '/api/v1/cameras/4e09b542-98b1-4974-9e6c-8f3a8c3d7f0a/queue-stream',
        zone_name: 'Main Queue Pathway 1',
        camera_type: 'QUEUE',
      };
    }

    if (idx === 1) {
      return {
        id: '67676767-6767-4e67-a676-676767676767',
        name: 'Queue Monitor 2 — 67676767',
        stream_url: '/api/v1/cameras/67676767-6767-4e67-a676-676767676767/queue-stream',
        zone_name: 'Main Queue Pathway 2',
        camera_type: 'QUEUE',
      };
    }

    if (idx === 2) {
      return {
        id: '33333333-3333-4333-a333-333333333333',
        name: 'Entry Counter Camera 3',
        stream_url: '/api/v1/cameras/33333333-3333-4333-a333-333333333333/stream',
        zone_name: 'Main Gate Entrance 3',
        camera_type: 'ENTRY',
      };
    }

    if (existing) return existing;

    return {
      id: `cam-slot-${idx + 1}`,
      name: `CCTV Camera ${String(idx + 1).padStart(2, '0')}`,
      stream_url: '/images/detection-placeholder.jpg',
      zone_name: `Zone ${String(Math.floor(idx / 3) + 1).padStart(2, '0')}`,
    };
  });

  return (
    <DashboardLayout pageTitle="AI Crowd Management Dashboard">
      <style>{`
        .cctv-wall-section { padding: 0 24px; margin-top: 20px; }
        .cameras-grid { display: grid; grid-template-columns: repeat(4, 1fr) !important; gap: 20px; margin-bottom: 24px; }
        @media (max-width: 1200px) { .cameras-grid { grid-template-columns: repeat(3, 1fr) !important; } }
        @media (max-width: 800px)  { .cameras-grid { grid-template-columns: repeat(2, 1fr) !important; } }
        @media (max-width: 500px)  { .cameras-grid { grid-template-columns: 1fr !important; } }
        .camera-card { background-color: #0b0f19; border-radius: var(--border-radius-lg); border: 1px solid rgba(51,65,85,.45) !important; overflow: hidden; position: relative; cursor: pointer; box-shadow: 0 4px 15px rgba(0,0,0,.25) !important; transition: transform .25s cubic-bezier(.4,0,.2,1), border-color .25s !important; }
        .camera-card:hover { transform: scale(1.025); border-color: rgba(34,197,94,.5) !important; }
        .camera-video-container { width: 100%; height: 210px; background-color: #000; position: relative; overflow: hidden; }
        .camera-video-placeholder { width: 100%; height: 100%; object-fit: cover; opacity: 1; transition: opacity .3s; }
        .camera-scanner-overlay { display: none; }
        .camera-scanline { display: none; }
        .camera-telemetry { position: absolute; top: 12px; left: 12px; right: 12px; display: flex; justify-content: space-between; align-items: center; color: #22c55e; font-family: monospace; font-size: 10px; text-shadow: 1px 1px 2px #000; font-weight: bold; z-index: 4; }
        .camera-rec-dot { display: flex; align-items: center; gap: 6px; text-transform: uppercase; }
        .rec-dot { width: 7px; height: 7px; border-radius: 50%; background-color: #ef4444; display: inline-block; animation: cctv-blink 1s infinite alternate; }
        @keyframes cctv-blink { 0% { opacity: .2; } 100% { opacity: 1; } }
        .camera-name-overlay { position: absolute; bottom: 12px; left: 12px; color: #22c55e; font-family: monospace; font-size: 11px; font-weight: bold; text-shadow: 1px 1px 2px #000; z-index: 4; letter-spacing: .5px; background: rgba(0,0,0,0.6); padding: 2px 6px; border-radius: 4px; }
        .cctv-zoom-modal { position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background-color: rgba(0,0,0,0.95); z-index: 99999; display: none; justify-content: center; align-items: center; opacity: 0; transition: opacity .2s ease-in-out; }
        .cctv-zoom-modal.active { display: flex; opacity: 1; }
        .zoom-content-wrapper { position: relative; width: 95vw; height: 90vh; background-color: #000; border-radius: 12px; overflow: hidden; border: 1px solid #1e293b; box-shadow: 0 20px 50px rgba(0,0,0,0.8); }
        .zoomed-camera-img { width: 100%; height: 100%; object-fit: contain; }
        .btn-close-zoom { position: absolute; top: 24px; right: 32px; background: rgba(15,23,42,.8); border: 1px solid rgba(255,255,255,.3); border-radius: 50%; width: 48px; height: 48px; color: #fff; font-size: 28px; display: flex; justify-content: center; align-items: center; cursor: pointer; z-index: 100000; transition: background-color .2s; }
        .btn-close-zoom:hover { background-color: #ef4444; }
        .zoomed-camera-name { font-family: monospace; font-weight: bold; font-size: 14px; letter-spacing: .5px; color: #22c55e; text-shadow: 1px 1px 2px #000; }
      `}</style>

      <section className="cctv-wall-section">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <h2 className="section-title" style={{ margin: 0 }}>
            <i className="fa-solid fa-shield-halved" style={{ color: '#22c55e', marginRight: '8px' }}></i> Live CCTV Video Wall (12 Screens)
          </h2>
          <span style={{ fontSize: '12px', color: '#94a3b8', background: '#0b0f19', padding: '6px 12px', borderRadius: '6px', border: '1px solid #1e293b' }}>
            <i className="fa-solid fa-expand" style={{ marginRight: '6px' }}></i> Click any screen to maximize
          </span>
        </div>

        <div className="cameras-grid" id="cameras-grid-container">
          {displayCameras.map((cam, idx) => (
            <CameraCard
              key={cam.id || `cam-${idx}`}
              cam={cam}
              onZoom={(name, src, cid, isQueue) => setZoomCam({ name, src, camId: cid, isQueueCam: isQueue })}
            />
          ))}
        </div>
      </section>

      {/* Fullscreen MAXIMIZE zoom modal */}
      <CctvZoomModal
        isOpen={!!zoomCam}
        cameraName={zoomCam?.name || ''}
        streamSrc={zoomCam?.src  || ''}
        camId={zoomCam?.camId || ''}
        isQueueCam={zoomCam?.isQueueCam || false}
        onClose={() => setZoomCam(null)}
      />
    </DashboardLayout>
  );
}
