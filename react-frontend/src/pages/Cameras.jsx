import React, { useState, useEffect, useRef, useCallback } from 'react';
import DashboardLayout from '../components/layout/DashboardLayout';
import { fetchCameras } from '../services/api';

const CAM_BASE = import.meta.env.VITE_CAMERAS_API_URL || 'http://127.0.0.1:8001/api/v1';

/**
 * Camera card – identical to the inline template in cameras.blade.php
 */
function CameraCard({ cam, onZoom }) {
  const streamSrc = cam.stream_url || `${CAM_BASE}/cameras/${cam.id || cam.camera_id}/stream`;
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
      onClick={() => onZoom(camName, streamSrc)}
    >
      <div className="camera-video-container">
        <img
          src={streamSrc}
          onError={e => { e.target.src = '/images/detection-placeholder.jpg'; }}
          alt={camName}
          className="camera-video-placeholder"
          style={{ opacity: 0.9 }}
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
function CctvZoomModal({ isOpen, cameraName, streamSrc, onClose }) {
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

  return (
    <div
      id="cctv-zoom-modal"
      className="cctv-zoom-modal active"
      onClick={onClose}
    >
      <button type="button" className="btn-close-zoom" onClick={onClose}>&times;</button>
      <div className="zoom-content-wrapper" onClick={e => e.stopPropagation()}>
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
      </div>
    </div>
  );
}

/**
 * CCTV Grid page – pixel-identical to dashboard/cameras.blade.php
 * Includes all inline CSS from that file via a <style> tag.
 */
export default function Cameras() {
  const [cameras, setCameras]       = useState([]);
  const [loading, setLoading]       = useState(true);
  const [error, setError]           = useState(false);
  const [zoomCam, setZoomCam]       = useState(null);   // { name, src }

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

  const countLabel = loading ? 'Loading...' : `${cameras.length} ${cameras.length === 1 ? 'Feed' : 'Feeds'}`;

  return (
    <DashboardLayout pageTitle="AI Crowd Management Dashboard">
      {/* Inline styles from cameras.blade.php */}
      <style>{`
        .cctv-wall-section { padding: 0 24px; margin-top: 20px; }
        .cameras-grid { display: grid; grid-template-columns: repeat(4, 1fr) !important; gap: 20px; margin-bottom: 24px; }
        @media (max-width: 1200px) { .cameras-grid { grid-template-columns: repeat(2, 1fr) !important; } }
        @media (max-width: 600px)  { .cameras-grid { grid-template-columns: 1fr !important; } }
        .camera-card { background-color: #0b0f19; border-radius: var(--border-radius-lg); border: 1px solid rgba(51,65,85,.45) !important; overflow: hidden; position: relative; cursor: pointer; box-shadow: 0 4px 15px rgba(0,0,0,.25) !important; transition: transform .25s cubic-bezier(.4,0,.2,1), border-color .25s !important; }
        .camera-card:hover { transform: scale(1.025); border-color: rgba(34,197,94,.5) !important; }
        .camera-video-container { width: 100%; height: 200px; background-color: #000; position: relative; overflow: hidden; }
        .camera-video-placeholder { width: 100%; height: 100%; object-fit: cover; opacity: 1; transition: opacity .3s; }
        .camera-scanner-overlay { display: none; }
        .camera-scanline { display: none; }
        .camera-telemetry { position: absolute; top: 12px; left: 12px; right: 12px; display: flex; justify-content: space-between; align-items: center; color: #22c55e; font-family: monospace; font-size: 10px; text-shadow: 1px 1px 2px #000; font-weight: bold; z-index: 4; }
        .camera-rec-dot { display: flex; align-items: center; gap: 6px; text-transform: uppercase; }
        .rec-dot { width: 7px; height: 7px; border-radius: 50%; background-color: #ef4444; display: inline-block; animation: cctv-blink 1s infinite alternate; }
        @keyframes cctv-blink { 0% { opacity: .2; } 100% { opacity: 1; } }
        .camera-name-overlay { position: absolute; bottom: 12px; left: 12px; color: #22c55e; font-family: monospace; font-size: 11px; font-weight: bold; text-shadow: 1px 1px 2px #000; z-index: 4; letter-spacing: .5px; }
        .cctv-zoom-modal { position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background-color: #000; z-index: 99999; display: none; justify-content: center; align-items: center; opacity: 0; transition: opacity .2s ease-in-out; }
        .cctv-zoom-modal.active { display: flex; opacity: 1; }
        .zoom-content-wrapper { position: relative; width: 100vw; height: 100vh; background-color: #000; overflow: hidden; transform: scale(1); }
        .zoomed-camera-img { width: 100%; height: 100%; object-fit: cover; }
        .btn-close-zoom { position: absolute; top: 24px; right: 32px; background: rgba(15,23,42,.7); border: 1px solid rgba(255,255,255,.2); border-radius: 50%; width: 48px; height: 48px; color: #fff; font-size: 28px; display: flex; justify-content: center; align-items: center; cursor: pointer; z-index: 100000; transition: background-color .2s; }
        .btn-close-zoom:hover { background-color: #ef4444; }
        .zoomed-camera-name { font-family: monospace; font-weight: bold; font-size: 14px; letter-spacing: .5px; color: #22c55e; text-shadow: 1px 1px 2px #000; }
      `}</style>

      <section className="cctv-wall-section">
        <h2 className="section-title" style={{ marginBottom: '20px' }}>
          <i className="fa-solid fa-shield-halved"></i> Live CCTV Video Wall (
          <span id="cctv-count-label">{countLabel}</span>)
        </h2>

        <div className="cameras-grid" id="cameras-grid-container">
          {loading && (
            <div style={{ gridColumn: '1/-1', textAlign: 'center', color: '#94a3b8', padding: '40px' }}>
              <i className="fa-solid fa-spinner fa-spin" style={{ fontSize: '32px', marginBottom: '12px', color: '#3b82f6', display: 'block' }}></i>
              <p style={{ fontSize: '14px', fontWeight: 500 }}>Connecting to FastAPI AI Engine and loading live camera streams...</p>
            </div>
          )}

          {!loading && error && (
            <div style={{ gridColumn: '1/-1', textAlign: 'center', color: '#ef4444', padding: '36px', background: '#0b0f19', borderRadius: '12px', border: '1px solid #7f1d1d' }}>
              <i className="fa-solid fa-triangle-exclamation" style={{ fontSize: '36px', marginBottom: '10px', display: 'block' }}></i>
              <p style={{ fontSize: '14px', fontWeight: 600 }}>Unable to load camera feeds from AI backend.</p>
            </div>
          )}

          {!loading && !error && cameras.length === 0 && (
            <div style={{ gridColumn: '1/-1', textAlign: 'center', color: '#94a3b8', padding: '48px', background: '#0b0f19', borderRadius: '12px', border: '1px solid #1e293b' }}>
              <i className="fa-solid fa-video-slash" style={{ fontSize: '42px', marginBottom: '12px', color: '#64748b', display: 'block' }}></i>
              <h3 style={{ fontSize: '16px', color: '#f8fafc', fontWeight: 700, marginBottom: '6px' }}>No Active Live Cameras Found</h3>
              <p style={{ fontSize: '13px', color: '#64748b' }}>Connect an RTSP camera stream or register a CCTV camera to stream live AI detections.</p>
            </div>
          )}

          {!loading && !error && cameras.map(cam => (
            <CameraCard
              key={cam.id || cam.camera_id || Math.random()}
              cam={cam}
              onZoom={(name, src) => setZoomCam({ name, src })}
            />
          ))}
        </div>
      </section>

      {/* Fullscreen zoom modal */}
      <CctvZoomModal
        isOpen={!!zoomCam}
        cameraName={zoomCam?.name || ''}
        streamSrc={zoomCam?.src  || ''}
        onClose={() => setZoomCam(null)}
      />
    </DashboardLayout>
  );
}
