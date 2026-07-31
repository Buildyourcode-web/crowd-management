import React, { useState, useCallback } from 'react';
import { acknowledgeCriminalDetection } from '../services/api';

function formatTime(dateStr) {
  if (!dateStr) return '00:00 AM';
  const d = new Date(dateStr);
  let h   = d.getHours();
  const ampm = h >= 12 ? 'PM' : 'AM';
  h = h % 12 || 12;
  return `${String(h).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')} ${ampm}`;
}

/**
 * Criminal Identification Panel – full replica of the criminal-panel in index.blade.php
 * and all the criminal display logic from dashboard.js
 *
 * Props:
 *   criminalRecords     – watchlist records from /api/criminal-records
 *   activeDetections    – live detections from /api/criminal-detections
 *   currentDetectionIdx – controlled index
 *   setCurrentDetectionIdx
 *   onRefresh           – callback to reload data after acknowledge
 */
export default function CriminalPanel({
  criminalRecords = [],
  activeDetections = [],
  currentDetectionIdx = 0,
  setCurrentDetectionIdx,
  onRefresh,
}) {
  const [isProcessing, setIsProcessing] = useState(false);
  const [lightboxSrc, setLightboxSrc]   = useState(null);

  const unacked = activeDetections.filter(d => d.status === 'detected');
  const det     = unacked[currentDetectionIdx % Math.max(1, unacked.length)];
  const rec     = criminalRecords[0]; // fallback watchlist record

  const hasDetections = unacked.length > 0;
  const isEmpty       = criminalRecords.length === 0 && activeDetections.length === 0;

  const navigate = useCallback((dir) => {
    setCurrentDetectionIdx(i => {
      const next = dir === 'next' ? i + 1 : i - 1;
      return ((next % unacked.length) + unacked.length) % unacked.length;
    });
  }, [unacked.length, setCurrentDetectionIdx]);

  async function handleAcknowledge() {
    if (!det || isProcessing) return;
    setIsProcessing(true);
    try {
      await acknowledgeCriminalDetection(det.id);
      if (onRefresh) onRefresh();
    } catch { /* non-fatal */ }
    finally { setIsProcessing(false); }
  }

  // ── Determine display mode ──────────────────────────────────────────────────
  let suspectSrc  = '/images/detection-placeholder.jpg';
  let capturedSrc = '/images/detection-placeholder.jpg';
  let accuracy    = '--';
  let location    = '--';
  let timeLabel   = null;
  let statusBadge = { cls: 'criminal-badge-normal', text: 'No Detections' };

  if (hasDetections && det) {
    suspectSrc  = det.criminal?.profile_image || '/images/detection-placeholder.jpg';
    capturedSrc = det.captured_image          || '/images/detection-placeholder.jpg';
    accuracy    = det.accuracy != null ? `${det.accuracy}%` : '--';
    location    = det.zone_name || '--';
    timeLabel   = formatTime(det.captured_at);
    statusBadge = { cls: 'criminal-badge-alert', text: 'Criminal Detected' };
  } else if (rec) {
    suspectSrc  = rec.profile_image || '/images/detection-placeholder.jpg';
    statusBadge = { cls: 'criminal-badge-normal', text: 'Watchlist Active' };
  }

  return (
    <div className="grid-card criminal-card" id="criminal-panel" tabIndex={0}
      onKeyDown={e => {
        if (e.key === 'ArrowLeft'  && unacked.length > 1) { e.preventDefault(); navigate('prev'); }
        if (e.key === 'ArrowRight' && unacked.length > 1) { e.preventDefault(); navigate('next'); }
      }}>
      <h3 className="grid-card-title">Criminal Identification</h3>

      {/* Status header */}
      <div className="criminal-status-header">
        <span className={statusBadge.cls}>{statusBadge.text}</span>
        {hasDetections && timeLabel && (
          <span className="criminal-time-badge">
            <i className="fa-regular fa-clock"></i>{' '}
            <span>{timeLabel}</span>
          </span>
        )}
      </div>

      {/* Feed container */}
      <div className="criminal-feed-container">
        {/* Empty state */}
        {isEmpty && (
          <div className="criminal-empty-fallback">
            <i className="fa-solid fa-user-shield"></i>
            <p>No records or active detections found</p>
          </div>
        )}

        {/* Images */}
        {!isEmpty && (
          <div className={`criminal-images-wrapper${hasDetections ? ' active-alert' : ''}`}>
            <img
              id="criminal-suspect-image"
              src={suspectSrc}
              alt="Suspect Watchlist Profile"
              className="criminal-feed-img suspect-img"
              onError={e => { e.target.src = '/images/detection-placeholder.jpg'; }}
            />

            <div className="captured-image-container">
              <img
                id="criminal-captured-image"
                src={capturedSrc}
                alt="AI CCTV Capture"
                className="criminal-feed-img captured-img cursor-pointer"
                style={{ cursor: 'pointer' }}
                onClick={() => setLightboxSrc(capturedSrc)}
                onError={e => { e.target.src = '/images/detection-placeholder.jpg'; }}
              />

              {/* Scanning HUD overlay (shown when no active detection) */}
              {!hasDetections && (
                <div id="criminal-scan-overlay" className="criminal-scan-overlay">
                  <div className="scanner-hud">
                    <div className="scanner-line"></div>
                    <div className="scanner-text">
                      <i className="fa-solid fa-expand fa-beat"></i> CCTV FEED SCANNING
                    </div>
                  </div>
                </div>
              )}

              {/* Prev / Next navigation buttons */}
              {unacked.length > 1 && (
                <>
                  <button type="button" className="criminal-nav-btn prev-btn"
                    onClick={e => { e.stopPropagation(); navigate('prev'); }}
                    aria-label="Previous detection">
                    <i className="fa-solid fa-chevron-left"></i>
                  </button>
                  <button type="button" className="criminal-nav-btn next-btn"
                    onClick={e => { e.stopPropagation(); navigate('next'); }}
                    aria-label="Next detection">
                    <i className="fa-solid fa-chevron-right"></i>
                  </button>
                </>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Detail grid */}
      <div className="criminal-details-grid">
        <div className="criminal-detail-item">
          <span className="detail-label">Accuracy:</span>
          <span className="detail-value">{accuracy}</span>
        </div>
        <div className="criminal-detail-item text-right">
          <span className="detail-label">Location:</span>
          <span className="detail-value">{location}</span>
        </div>
      </div>

      {/* Acknowledge button */}
      {hasDetections && det && (
        <div className="criminal-action-wrapper">
          <button
            type="button"
            className="btn-acknowledge"
            onClick={handleAcknowledge}
            disabled={isProcessing}
          >
            {isProcessing ? <><i className="fa-solid fa-spinner fa-spin"></i> Processing...</> : 'Acknowledge'}
          </button>
        </div>
      )}

      {/* Lightbox */}
      {lightboxSrc && (
        <div
          className="lightbox-modal"
          style={{ display: 'flex' }}
          onClick={() => setLightboxSrc(null)}
        >
          <span className="lightbox-close" onClick={() => setLightboxSrc(null)}>&times;</span>
          <img className="lightbox-content" src={lightboxSrc} alt="Fullscreen preview" />
          <div className="lightbox-caption">CCTV Captured Suspect Match</div>
        </div>
      )}
    </div>
  );
}
