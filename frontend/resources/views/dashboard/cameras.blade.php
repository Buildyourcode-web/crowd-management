@extends('layouts.dashboard')

@section('title', 'CCTV Video Wall - AI Crowd Management')

@section('content')
<style>
    /* CCTV Grid & Card custom overrides */
    .cctv-wall-section {
        padding: 0 24px;
        margin-top: 20px;
    }

    .cameras-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr) !important;
        gap: 20px;
        margin-bottom: 24px;
    }

    @media (max-width: 1200px) {
        .cameras-grid {
            grid-template-columns: repeat(2, 1fr) !important;
        }
    }

    @media (max-width: 600px) {
        .cameras-grid {
            grid-template-columns: 1fr !important;
        }
    }

    .camera-card {
        background-color: #0b0f19;
        border-radius: var(--border-radius-lg);
        border: 1px solid rgba(51, 65, 85, 0.45) !important;
        border-left: 1px solid rgba(51, 65, 85, 0.45) !important; /* No left colored status border */
        overflow: hidden;
        position: relative;
        cursor: pointer;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.25) !important;
        transition: transform 0.25s cubic-bezier(0.4, 0, 0.2, 1), border-color 0.25s !important;
    }

    .camera-card:hover {
        transform: scale(1.025);
        border-color: rgba(34, 197, 94, 0.5) !important; /* Highlight border on hover */
    }

    /* Video feed container */
    .camera-video-container {
        width: 100%;
        height: 200px; /* Taller feeds since bottom stats are removed */
        background-color: #000000;
        position: relative;
        overflow: hidden;
    }

    .camera-video-placeholder {
        width: 100%;
        height: 100%;
        object-fit: cover;
        opacity: 1;
        transition: opacity 0.3s;
    }

    .camera-card:hover .camera-video-placeholder {
        opacity: 1;
    }

    /* Scanner scanlines overlay - Hidden for clean view */
    .camera-scanner-overlay {
        display: none;
    }

    .camera-scanline {
        display: none;
    }

    /* Overlay texts */
    .camera-telemetry {
        position: absolute;
        top: 12px;
        left: 12px;
        right: 12px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        color: #22c55e; /* Static green/cyan terminal look */
        font-family: monospace;
        font-size: 10px;
        text-shadow: 1px 1px 2px #000000;
        font-weight: bold;
        z-index: 4;
    }

    .camera-rec-dot {
        display: flex;
        align-items: center;
        gap: 6px;
        text-transform: uppercase;
    }

    .rec-dot {
        width: 7px;
        height: 7px;
        border-radius: 50%;
        background-color: #ef4444;
        display: inline-block;
        animation: cctv-blink 1s infinite alternate;
    }

    @keyframes cctv-blink {
        0% { opacity: 0.2; }
        100% { opacity: 1.0; }
    }

    .camera-name-overlay {
        position: absolute;
        bottom: 12px;
        left: 12px;
        color: #22c55e;
        font-family: monospace;
        font-size: 11px;
        font-weight: bold;
        text-shadow: 1px 1px 2px #000000;
        z-index: 4;
        letter-spacing: 0.5px;
    }

    /* True 100% Fullscreen CCTV Zoom Modal */
    .cctv-zoom-modal {
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        background-color: #000000;
        z-index: 99999;
        display: none;
        justify-content: center;
        align-items: center;
        opacity: 0;
        transition: opacity 0.2s ease-in-out;
    }

    .cctv-zoom-modal.active {
        display: flex;
        opacity: 1;
    }

    .zoom-content-wrapper {
        position: relative;
        width: 100vw; /* 100% viewport width */
        height: 100vh; /* 100% viewport height */
        background-color: #000000;
        border: none !important;
        border-radius: 0 !important;
        box-shadow: none !important;
        overflow: hidden;
        transform: scale(0.98);
        transition: transform 0.2s ease-out;
    }

    .cctv-zoom-modal.active .zoom-content-wrapper {
        transform: scale(1);
    }

    .zoomed-camera-img {
        width: 100%;
        height: 100%;
        object-fit: cover;
        opacity: 1;
    }

    .btn-close-zoom {
        position: absolute;
        top: 24px;
        right: 32px;
        background: rgba(15, 23, 42, 0.7);
        border: 1px solid rgba(255, 255, 255, 0.2);
        border-radius: 50%;
        width: 48px;
        height: 48px;
        color: #ffffff;
        font-size: 28px;
        display: flex;
        justify-content: center;
        align-items: center;
        cursor: pointer;
        z-index: 100000;
        transition: background-color 0.2s, color 0.2s;
    }

    .btn-close-zoom:hover {
        background-color: #ef4444;
        color: #ffffff;
    }

    .zoomed-camera-name {
        font-family: monospace;
        font-weight: bold;
        font-size: 14px;
        letter-spacing: 0.5px;
        color: #22c55e;
        text-shadow: 1px 1px 2px #000000;
    }
</style>

<!-- Header Section -->
<header class="dashboard-header">
    <div class="header-left">
        <img src="{{ asset('images/police-logo.png') }}" alt="Police Logo" class="logo-image">
        <!-- <img src="{{ asset('images/white-TG.png') }}" alt="State Logo" class="logo-image"> -->
    </div>
    
    <div class="header-center">
        <h1 class="main-title">AI Crowd Management Dashboard</h1>
        <p class="subtitle">Powered by <img src="{{ asset('images/LOGO_Bold.png') }}" alt="BYC AI Logo" class="byc-logo"></p>
    </div>
    
    <div class="header-right">
        <div class="time-block">
            <span id="current-date" class="header-date">-- --- ----</span>
            <span class="divider">|</span>
            <span id="current-time" class="header-time">00:00:00 AM</span>
        </div>
        
        <div id="live-badge-container">
            <span class="badge badge-live">
                Live <span class="live-dot pulse-green"></span>
            </span>
        </div>
        
        <button type="button" class="btn-icon-bell" onclick="toggleDrawer(true)" aria-label="Open notifications drawer">
            <i class="fa-regular fa-bell"></i>
            <span id="header-unread-badge" class="badge-count hidden">0</span>
        </button>
    </div>
</header>

<!-- Navigation Tabs Bar -->
<nav class="dashboard-nav">
    <a href="{{ route('dashboard') }}" class="nav-link">
        <i class="fa-solid fa-chart-pie"></i> Overview
    </a>
    <a href="{{ route('dashboard.metrics') }}" class="nav-link">
        <i class="fa-solid fa-users-viewfinder"></i> Metrics Detail
    </a>
    <a href="{{ route('dashboard.zones') }}" class="nav-link">
        <i class="fa-solid fa-map-location-dot"></i> Zone Heatmap
    </a>
    <a href="{{ route('dashboard.traffic') }}" class="nav-link">
        <i class="fa-solid fa-arrows-spin"></i> Gates & Queues
    </a>
    <a href="{{ route('dashboard.cameras') }}" class="nav-link active">
        <i class="fa-solid fa-video"></i> CCTV Grid
    </a>
</nav>

<!-- Alerts Bar -->
<section class="alerts-bar-section">
    <div id="alerts-bar" class="alerts-bar cursor-pointer" onclick="toggleDrawer(true)" tabindex="0" role="button" aria-label="View notifications">
        <span class="alerts-bar-title">Alerts</span>
        <span id="alerts-bar-count-badge" class="badge-alerts-count hidden">0</span>
    </div>
</section>

<!-- CCTV Cameras Grid Layout -->
<section class="cctv-wall-section">
    <h2 class="section-title" style="margin-bottom: 20px;">
        <i class="fa-solid fa-shield-halved"></i> Live CCTV Video Wall (<span id="cctv-count-label">Loading...</span>)
    </h2>
    
    <div class="cameras-grid" id="cameras-grid-container">
        <div style="grid-column: 1/-1; text-align: center; color: #94a3b8; padding: 40px;">
            <i class="fa-solid fa-spinner fa-spin" style="font-size: 32px; margin-bottom: 12px; color: #3b82f6;"></i>
            <p style="font-size: 14px; font-weight: 500;">Connecting to FastAPI AI Engine and loading live camera streams...</p>
        </div>
    </div>
</section>

<!-- Fullscreen CCTV Zoom Modal -->
<div id="cctv-zoom-modal" class="cctv-zoom-modal" onclick="closeCameraZoom()">
    <button type="button" class="btn-close-zoom" onclick="closeCameraZoom()">&times;</button>
    <div class="zoom-content-wrapper" onclick="event.stopPropagation()">
        <img id="zoomed-camera-img" src="" alt="CCTV Zoomed Feed" class="zoomed-camera-img">
        <div class="camera-scanner-overlay"></div>
        <div class="camera-scanline" style="animation-duration: 8s;"></div>
        
        <div class="camera-telemetry" style="top: 16px; left: 16px; right: 16px;">
            <span class="camera-rec-dot" style="font-size: 13px;">
                <span class="rec-dot" style="width: 9px; height: 9px;"></span> LIVE CCTV FEED
            </span>
            <span id="zoomed-camera-name" class="zoomed-camera-name">CAM-NAME</span>
            <span id="zoomed-camera-time" class="camera-timestamp font-numeric" style="font-size: 13px;">REC // 00:00:00 AM</span>
        </div>
    </div>
</div>

<!-- Dynamic Script to Fetch Live Cameras from FastAPI / Database -->
<script>
    document.addEventListener('DOMContentLoaded', () => {
        loadLiveCameras();

        // Keep telemetry timestamps moving
        setInterval(() => {
            const now = new Date();
            const timeStr = now.toLocaleTimeString();
            document.querySelectorAll('.camera-timestamp').forEach((el) => {
                el.textContent = `REC // ${timeStr}`;
            });
        }, 1000);
    });

    async function loadLiveCameras() {
        const container = document.getElementById('cameras-grid-container');
        const countLabel = document.getElementById('cctv-count-label');
        if (!container) return;

        const fastApiUrl = "http://127.0.0.1:8001";

        try {
            const response = await fetch(`${fastApiUrl}/api/v1/cameras`, {
                headers: {
                    'X-User-ID': 'admin',
                    'X-User-Name': 'admin'
                }
            });
            const data = await response.json();
            
            const cameras = (data && data.data) ? data.data : (Array.isArray(data) ? data : []);

            if (countLabel) {
                countLabel.textContent = `${cameras.length} ${cameras.length === 1 ? 'Feed' : 'Feeds'}`;
            }

            if (cameras.length === 0) {
                container.innerHTML = `
                    <div style="grid-column: 1/-1; text-align: center; color: #94a3b8; padding: 48px; background: #0b0f19; border-radius: 12px; border: 1px solid #1e293b;">
                        <i class="fa-solid fa-video-slash" style="font-size: 42px; margin-bottom: 12px; color: #64748b;"></i>
                        <h3 style="font-size: 16px; color: #f8fafc; font-weight: 700; margin-bottom: 6px;">No Active Live Cameras Found</h3>
                        <p style="font-size: 13px; color: #64748b;">Connect an RTSP camera stream or register a CCTV camera in Supabase to stream live AI detections.</p>
                    </div>
                `;
                return;
            }

            container.innerHTML = cameras.map(cam => {
                const streamSrc = cam.stream_url || `${fastApiUrl}/api/v1/cameras/${cam.id || cam.camera_id}/stream`;
                const camName = cam.name || cam.camera_name || `Camera ${cam.id || ''}`;
                const zoneName = cam.zone_name || cam.zone || 'Main Zone';

                return `
                    <div class="camera-card" id="camera-card-${cam.id || '1'}" onclick="openCameraZoom('${camName}', '${streamSrc}')">
                        <div class="camera-video-container">
                            <img src="${streamSrc}" 
                                 onerror="this.onerror=null; this.src='/images/detection-placeholder.jpg';" 
                                 alt="${camName}" 
                                 class="camera-video-placeholder" 
                                 style="opacity: 0.9; filter: none;">
                            
                            <div class="camera-scanner-overlay"></div>
                            <div class="camera-scanline"></div>
                            
                            <div class="camera-telemetry">
                                <span class="camera-rec-dot">
                                    <span class="rec-dot"></span> LIVE
                                </span>
                                <span class="camera-timestamp font-numeric">REC // ${new Date().toLocaleTimeString()}</span>
                            </div>

                            <div class="camera-name-overlay">${camName} [${zoneName}]</div>
                        </div>
                    </div>
                `;
            }).join('');

        } catch (err) {
            console.error("Failed to load cameras:", err);
            container.innerHTML = `
                <div style="grid-column: 1/-1; text-align: center; color: #ef4444; padding: 36px; background: #0b0f19; border-radius: 12px; border: 1px solid #7f1d1d;">
                    <i class="fa-solid fa-triangle-exclamation" style="font-size: 36px; margin-bottom: 10px;"></i>
                    <p style="font-size: 14px; font-weight: 600;">Unable to load camera feeds from AI backend.</p>
                </div>
            `;
        }
    }

    // Open zoomed full-screen camera view
    function openCameraZoom(cameraName, imgSrc) {
        const modal = document.getElementById('cctv-zoom-modal');
        const zoomImg = document.getElementById('zoomed-camera-img');
        const zoomName = document.getElementById('zoomed-camera-name');
        
        if (modal && zoomImg && zoomName) {
            zoomImg.src = imgSrc;
            zoomName.textContent = cameraName;
            
            modal.style.display = 'flex';
            // Trigger animation frame for CSS transitions
            requestAnimationFrame(() => {
                modal.classList.add('active');
            });
        }
    }

    // Close zoomed full-screen camera view
    function closeCameraZoom() {
        const modal = document.getElementById('cctv-zoom-modal');
        if (modal) {
            modal.classList.remove('active');
            // Wait for transitions to finish before setting display none
            setTimeout(() => {
                modal.style.display = 'none';
            }, 250);
        }
    }
</script>

<!-- Notification Drawer -->
<div id="notification-drawer" class="notification-drawer">
    <div class="drawer-header">
        <div class="drawer-title-wrapper">
            <h2 class="drawer-title">Alert Logs</h2>
            <span id="drawer-unread-count" class="drawer-badge">0</span>
        </div>
        <button type="button" class="btn-close-drawer" onclick="toggleDrawer(false)" aria-label="Close drawer">
            <i class="fa-solid fa-xmark"></i>
        </button>
    </div>
    
    <div class="drawer-filters">
        <button type="button" class="filter-tab active" data-filter="all">All</button>
        <button type="button" class="filter-tab" data-filter="critical">Critical</button>
        <button type="button" class="filter-tab" data-filter="warning">Warning</button>
        <button type="button" class="filter-tab" data-filter="info">Info</button>
    </div>
    
    <div class="drawer-actions">
        <button type="button" class="btn-text" onclick="markAllNotificationsAsRead()">
            <i class="fa-solid fa-check-double"></i> Mark all as read
        </button>
    </div>

    <!-- Notification List -->
    <div id="notification-list" class="notification-list">
        <div class="empty-notifications">
            <i class="fa-regular fa-bell-slash"></i>
            <p>No notifications</p>
        </div>
    </div>
</div>

<!-- Drawer Overlay backdrop -->
<div id="drawer-overlay" class="drawer-overlay" onclick="toggleDrawer(false)"></div>
@endsection
