@extends('layouts.dashboard')

@section('title', 'Attendance Metrics - AI Crowd Management')

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
    <a href="{{ route('dashboard.metrics') }}" class="nav-link active">
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
        <span class="alerts-bar-title">Alerts</span>
        <span id="alerts-bar-count-badge" class="badge-alerts-count hidden">0</span>
    </div>
</section>

<!-- Attendance Metrics Grid -->
<section class="metrics-detail-grid">
    <!-- Card 1: Total Visits -->
    <div class="metric-expanded-card">
        <div class="metric-card-header">
            <span class="metric-card-title">Total Visits</span>
            <div class="metric-card-icon-wrapper icon-blue">
                <i class="fa-solid fa-users"></i>
            </div>
        </div>
        <div class="metric-card-value font-numeric" id="visits-val">0</div>
        <div class="metric-card-trend-bar">
            <div class="metric-trend-fill icon-blue" style="width: 75%;"></div>
        </div>
        <div class="metric-card-footer">
            <span class="metric-trend-badge trend-up">
                <i class="fa-solid fa-arrow-trend-up"></i> +12.3%
            </span>
            <span>Since yesterday</span>
        </div>
    </div>

    <!-- Card 2: People Present -->
    <div class="metric-expanded-card">
        <div class="metric-card-header">
            <span class="metric-card-title">People Present</span>
            <div class="metric-card-icon-wrapper icon-orange">
                <i class="fa-solid fa-user"></i>
            </div>
        </div>
        <div class="metric-card-value font-numeric" id="present-val">0</div>
        <div class="metric-card-trend-bar">
            <div class="metric-trend-fill icon-orange" style="width: 58%;"></div>
        </div>
        <div class="metric-card-footer">
            <span class="metric-trend-badge trend-neutral">
                <i class="fa-solid fa-minus"></i> Stable
            </span>
            <span>Live check</span>
        </div>
    </div>

    <!-- Card 3: Total Entries -->
    <div class="metric-expanded-card">
        <div class="metric-card-header">
            <span class="metric-card-title">Total Entries</span>
            <div class="metric-card-icon-wrapper icon-green">
                <i class="fa-solid fa-right-to-bracket"></i>
            </div>
        </div>
        <div class="metric-card-value font-numeric" id="entries-val">0</div>
        <div class="metric-card-trend-bar">
            <div class="metric-trend-fill icon-green" style="width: 82%;"></div>
        </div>
        <div class="metric-card-footer">
            <span class="metric-trend-badge trend-up">
                <i class="fa-solid fa-arrow-trend-up"></i> +8.5%
            </span>
            <span>Since 6:00 AM</span>
        </div>
    </div>

    <!-- Card 4: Total Exits -->
    <div class="metric-expanded-card">
        <div class="metric-card-header">
            <span class="metric-card-title">Total Exits</span>
            <div class="metric-card-icon-wrapper icon-teal">
                <i class="fa-solid fa-right-from-bracket"></i>
            </div>
        </div>
        <div class="metric-card-value font-numeric" id="exits-val">0</div>
        <div class="metric-card-trend-bar">
            <div class="metric-trend-fill icon-teal" style="width: 64%;"></div>
        </div>
        <div class="metric-card-footer">
            <span class="metric-trend-badge trend-up">
                <i class="fa-solid fa-arrow-trend-up"></i> +14.2%
            </span>
            <span>Since 6:00 AM</span>
        </div>
    </div>
</section>

<!-- Flow rate indicators card -->
<div class="grid-card" style="margin-bottom: 24px; padding: 24px;">
    <h3 class="grid-card-title" style="margin-bottom: 16px;"><i class="fa-solid fa-chart-line"></i> Flow Analytics</h3>
    <div style="display: flex; gap: 40px; flex-wrap: wrap; margin-top: 10px;">
        <div style="flex: 1; min-width: 250px; background: #fafbfc; border: 1px solid #e2e8f0; border-radius: var(--border-radius-md); padding: 20px; display: flex; align-items: center; gap: 16px;">
            <div style="width: 48px; height: 48px; border-radius: 50%; background: rgba(34, 197, 94, 0.1); color: #22c55e; display: flex; align-items: center; justify-content: center; font-size: 20px;">
                <i class="fa-solid fa-arrow-trend-up"></i>
            </div>
            <div>
                <div style="font-size: 13px; color: var(--text-secondary); font-weight: 500;">Average Entry Rate</div>
                <div style="font-size: 20px; font-weight: 700; color: var(--text-primary); margin-top: 2px;" id="avg-entry-rate-val">-- / hour</div>
            </div>
        </div>
        <div style="flex: 1; min-width: 250px; background: #fafbfc; border: 1px solid #e2e8f0; border-radius: var(--border-radius-md); padding: 20px; display: flex; align-items: center; gap: 16px;">
            <div style="width: 48px; height: 48px; border-radius: 50%; background: rgba(59, 130, 246, 0.1); color: #3b82f6; display: flex; align-items: center; justify-content: center; font-size: 20px;">
                <i class="fa-solid fa-arrow-trend-down"></i>
            </div>
            <div>
                <div style="font-size: 13px; color: var(--text-secondary); font-weight: 500;">Average Exit Rate</div>
                <div style="font-size: 20px; font-weight: 700; color: var(--text-primary); margin-top: 2px;" id="avg-exit-rate-val">-- / hour</div>
            </div>
        </div>
    </div>
</div>

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
