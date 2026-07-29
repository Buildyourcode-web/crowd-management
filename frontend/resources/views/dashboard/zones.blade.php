@extends('layouts.dashboard')

@section('title', 'Zone Heat Map - AI Crowd Management')

@section('content')
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
    <a href="{{ route('dashboard.zones') }}" class="nav-link active">
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
        <span class="alerts-bar-title">Alerts</span>
        <span id="alerts-bar-count-badge" class="badge-alerts-count hidden">0</span>
    </div>
</section>

<!-- Zones Detail Layout -->
<section class="zones-detail-layout">
    <!-- Left Column: Zone Cards -->
    <div class="zones-list-wrapper">
        <x-zone-card id="zone-a" name="Zone A" count="0" capacity="1000" occupancy="0" status="normal" type="wave" />
        <x-zone-card id="zone-b" name="Zone B" count="0" capacity="900" occupancy="0" status="normal" type="wave" />
        <x-zone-card id="zone-c" name="Zone C" count="0" capacity="800" occupancy="0" status="normal" type="wave" />
        <x-zone-card id="zone-d" name="Zone D" count="0" capacity="850" occupancy="0" status="normal" type="wave" />
    </div>

    <!-- Right Column: Interactive 2D Heatmap Map -->
    <div class="visualizer-card">
        <h3 class="visualizer-title">
            <i class="fa-solid fa-network-wired"></i> Live 2D Schematic Floor Map
        </h3>
        
        <div class="visualizer-map-container">
            <!-- Grid Background Overlay -->
            <div class="map-grid-overlay"></div>
            
            <!-- Radar Scan Line -->
            <div class="radar-scanline"></div>
            
            <!-- Telemetry HUD -->
            <div class="map-telemetry">
                <span class="telemetry-item"><i class="fa-solid fa-satellite-dish fa-spin-pulse"></i> LIVE SENSORS ACTIVE</span>
                <span class="telemetry-item"><i class="fa-solid fa-microchip"></i> CALIBRATED</span>
            </div>

            <div class="floor-map-grid">
                <!-- Zone A map block -->
                <div class="map-zone-block zone-normal" id="map-block-zone-a">
                    <div class="heat-wave-container">
                        <div class="heat-wave wave-1"></div>
                        <div class="heat-wave wave-2"></div>
                        <div class="heat-wave wave-3"></div>
                        <div class="heat-wave-core"></div>
                    </div>
                    <div class="zone-block-content">
                        <span class="map-zone-name">Zone A (North Concourse)</span>
                        <div class="map-zone-stats">
                            <span class="map-zone-count font-numeric">0</span>
                            <span class="map-zone-percentage">0.0% Occupancy</span>
                        </div>
                    </div>
                </div>

                <!-- Zone B map block -->
                <div class="map-zone-block zone-normal" id="map-block-zone-b">
                    <div class="heat-wave-container">
                        <div class="heat-wave wave-1"></div>
                        <div class="heat-wave wave-2"></div>
                        <div class="heat-wave wave-3"></div>
                        <div class="heat-wave-core"></div>
                    </div>
                    <div class="zone-block-content">
                        <span class="map-zone-name">Zone B (South Promenade)</span>
                        <div class="map-zone-stats">
                            <span class="map-zone-count font-numeric">0</span>
                            <span class="map-zone-percentage">0.0% Occupancy</span>
                        </div>
                    </div>
                </div>

                <!-- Zone C map block -->
                <div class="map-zone-block zone-normal" id="map-block-zone-c">
                    <div class="heat-wave-container">
                        <div class="heat-wave wave-1"></div>
                        <div class="heat-wave wave-2"></div>
                        <div class="heat-wave wave-3"></div>
                        <div class="heat-wave-core"></div>
                    </div>
                    <div class="zone-block-content">
                        <span class="map-zone-name">Zone C (East Entry Hall)</span>
                        <div class="map-zone-stats">
                            <span class="map-zone-count font-numeric">0</span>
                            <span class="map-zone-percentage">0.0% Occupancy</span>
                        </div>
                    </div>
                </div>

                <!-- Zone D map block -->
                <div class="map-zone-block zone-normal" id="map-block-zone-d">
                    <div class="heat-wave-container">
                        <div class="heat-wave wave-1"></div>
                        <div class="heat-wave wave-2"></div>
                        <div class="heat-wave wave-3"></div>
                        <div class="heat-wave-core"></div>
                    </div>
                    <div class="zone-block-content">
                        <span class="map-zone-name">Zone D (Central Plaza)</span>
                        <div class="map-zone-stats">
                            <span class="map-zone-count font-numeric">0</span>
                            <span class="map-zone-percentage">0.0% Occupancy</span>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Map Overlay Legend -->
            <div class="map-overlay-legend">
                <span class="legend-item"><span class="legend-dot status-normal"></span> Normal (&lt;60%)</span>
                <span class="legend-item"><span class="legend-dot status-warning"></span> Warning (60%-90%)</span>
                <span class="legend-item"><span class="legend-dot status-critical"></span> Critical (&gt;90%)</span>
            </div>
        </div>
    </div>
</section>

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
