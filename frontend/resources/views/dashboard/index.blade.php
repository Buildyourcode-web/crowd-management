@extends('layouts.dashboard')

@section('title', 'AI Crowd Management Dashboard - Powered by BYC AI')

@section('content')
<!-- Header Section -->
<header class="dashboard-header">
    <div class="header-left">
        <img src="{{ asset('images/police-logo.png') }}" alt="Police Logo" class="logo-image">
        <!-- <img src="{{ asset('images/white-TG.png') }}" alt="State Logo" class="logo-image"> -->
        <!-- <img src="{{ asset('images/BYC_AI_ICON.png') }}" alt="BYC AI Logo" class="BYC-AI-image"> -->

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
    <a href="{{ route('dashboard') }}" class="nav-link active">
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
    <a href="{{ route('dashboard.cameras') }}" class="nav-link">
        <i class="fa-solid fa-video"></i> CCTV Grid
    </a>
</nav>

<!-- Alerts Bar -->
<section class="alerts-bar-section">
    <div id="alerts-bar" class="alerts-bar cursor-pointer" onclick="toggleDrawer(true)" tabindex="0" role="button" aria-label="View notifications">
        <span class="alerts-bar-title">AI Alerts</span>
        <span id="alerts-bar-count-badge" class="badge-alerts-count hidden">0</span>
    </div>
</section>

<!-- Summary Cards Row -->
<section class="summary-cards-section">
    <x-summary-card id="visits-card" title="Total Visits" value="0" icon="fa-solid fa-users" colorClass="bg-blue" />
    <x-summary-card id="present-card" title="People Present" value="0" icon="fa-solid fa-user" colorClass="bg-orange" />
    <x-summary-card id="entries-card" title="Total Entries" value="0" icon="fa-solid fa-right-to-bracket" colorClass="bg-green" />
    <x-summary-card id="exits-card" title="Total Exits" value="0" icon="fa-solid fa-right-from-bracket" colorClass="bg-blue-light" />
</section>

<!-- Zone Crowd Heat Map -->
<section class="zone-heatmap-section">
    <h2 class="section-title">Zone Crowd Heat Map</h2>
    <div class="zone-cards-grid">
        <x-zone-card id="zone-a" name="Zone A" count="0" capacity="1000" occupancy="0" status="normal" />
        <x-zone-card id="zone-b" name="Zone B" count="0" capacity="900" occupancy="0" status="normal" />
        <x-zone-card id="zone-c" name="Zone C" count="0" capacity="800" occupancy="0" status="normal" />
        <x-zone-card id="zone-d" name="Zone D" count="0" capacity="850" occupancy="0" status="normal" />
    </div>
</section>

<!-- Middle Grid Layout -->
<section class="middle-grid-section">
    <!-- Gate wise Entry/Exit -->
    <div class="grid-card gates-card">
        <h3 class="grid-card-title">Gate wise Entry/ Exit</h3>
        <div class="table-responsive">
            <table class="grid-table" id="gates-table">
                <thead>
                    <tr>
                        <th scope="col">Gate no.</th>
                        <th scope="col">Entries</th>
                        <th scope="col">Exits</th>
                        <th scope="col">Status</th>
                    </tr>
                </thead>
                <tbody>
                    <!-- Populated dynamically via JS -->
                </tbody>
            </table>
        </div>
    </div>

    <!-- Queue Movement -->
    <div class="grid-card queues-card">
        <h3 class="grid-card-title">Queue Movement</h3>
        <div class="table-responsive">
            <table class="grid-table" id="queues-table">
                <thead>
                    <tr>
                        <th scope="col">Queue no.</th>
                        <th scope="col">Wait time</th>
                        <th scope="col">Movement</th>
                    </tr>
                </thead>
                <tbody>
                    <!-- Populated dynamically via JS -->
                </tbody>
            </table>
        </div>
    </div>

    <!-- Criminal Identification Panel -->
    <div class="grid-card criminal-card" id="criminal-panel">
        <h3 class="grid-card-title">Criminal Identification</h3>
        
        <div class="criminal-status-header">
            <span id="criminal-status-badge" class="criminal-badge-normal">No Detections</span>
            <span id="criminal-time" class="criminal-time-badge hidden">
                <i class="fa-regular fa-clock"></i> <span id="criminal-time-text">00:00 AM</span>
            </span>
        </div>
        
        <div class="criminal-feed-container" id="criminal-feed-container">
            <!-- Loading Skeleton Overlay -->
            <div id="criminal-skeleton" class="criminal-skeleton-overlay hidden">
                <div class="skeleton-side"></div>
                <div class="skeleton-side border-left"></div>
            </div>

            <!-- Empty State Fallback -->
            <div id="criminal-empty" class="criminal-empty-fallback hidden">
                <i class="fa-solid fa-user-shield"></i>
                <p>No records or active detections found</p>
            </div>

            <!-- Main Images Grid Wrapper -->
            <div class="criminal-images-wrapper" id="criminal-images-wrapper">
                <img id="criminal-suspect-image" src="{{ asset('images/detection-placeholder.jpg') }}" alt="Suspect Watchlist Profile" class="criminal-feed-img suspect-img">
                
                <div class="captured-image-container">
                    <img id="criminal-captured-image" src="{{ asset('images/detection-placeholder.jpg') }}" alt="AI CCTV Capture" class="criminal-feed-img captured-img cursor-pointer" onclick="openImageLightbox(this.src, 'CCTV Captured Suspect Match')" style="cursor: pointer;">
                    
                    <!-- Dynamic Scanning HUD Overlay -->
                    <div id="criminal-scan-overlay" class="criminal-scan-overlay">
                        <div class="scanner-hud">
                            <div class="scanner-line"></div>
                            <div class="scanner-text"><i class="fa-solid fa-expand fa-beat"></i> CCTV FEED SCANNING</div>
                        </div>
                    </div>
                    
                    <!-- Centered Left and Right Arrow Navigation Buttons -->
                    <button type="button" class="criminal-nav-btn prev-btn hidden" id="criminal-prev-btn" aria-label="Previous detection">
                        <i class="fa-solid fa-chevron-left"></i>
                    </button>
                    <button type="button" class="criminal-nav-btn next-btn hidden" id="criminal-next-btn" aria-label="Next detection">
                        <i class="fa-solid fa-chevron-right"></i>
                    </button>
                </div>
            </div>
        </div>
        
        <div class="criminal-details-grid">
            <div class="criminal-detail-item">
                <span class="detail-label">Accuracy:</span>
                <span id="criminal-accuracy" class="detail-value">--</span>
            </div>
            <div class="criminal-detail-item text-right">
                <span class="detail-label">Location:</span>
                <span id="criminal-location" class="detail-value">--</span>
            </div>
        </div>
        
        <div id="criminal-action-container" class="criminal-action-wrapper hidden">
            <!-- Populated with Acknowledge button when alert active -->
        </div>
    </div>
</section>

<!-- Hourly Crowd Trend -->
<section class="hourly-trend-section">
    <div class="chart-card">
        <div class="chart-header">
            <h3 class="chart-title">Hourly Crowd Trend</h3>
            <div class="chart-actions">
                <select id="day-select" class="dropdown-select" aria-label="Select day for hourly trend">
                    <option value="day1" selected>Day 01</option>
                    <option value="day2">Day 02</option>
                    <option value="day3">Day 03</option>
                </select>
            </div>
        </div>
        <div class="chart-container">
            <canvas id="crowd-trend-chart"></canvas>
        </div>
    </div>
</section>

<!-- Notification Sliding Drawer -->
<div id="notification-drawer" class="notification-drawer">
    <div class="drawer-header">
        <div class="drawer-header-title-block">
            <h3>Notifications</h3>
            <span id="drawer-unread-count" class="drawer-count-badge">0</span>
        </div>
        <button type="button" class="btn-close-drawer" onclick="toggleDrawer(false)" aria-label="Close drawer">
            <i class="fa-solid fa-xmark"></i>
        </button>
    </div>
    
    <!-- Drawer Filters -->
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
        <!-- Loaded dynamically via JS -->
        <div class="empty-notifications">
            <i class="fa-regular fa-bell-slash"></i>
            <p>No notifications</p>
        </div>
    </div>
</div>

<!-- Drawer Overlay backdrop -->
<div id="drawer-overlay" class="drawer-overlay" onclick="toggleDrawer(false)"></div>

<!-- Image Lightbox Modal -->
<div id="image-lightbox-modal" class="lightbox-modal hidden" onclick="closeImageLightbox()">
    <span class="lightbox-close" onclick="closeImageLightbox()">&times;</span>
    <img class="lightbox-content" id="lightbox-image" alt="Fullscreen preview">
    <div id="lightbox-caption" class="lightbox-caption"></div>
</div>
@endsection
