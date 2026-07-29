@extends('layouts.dashboard')

@section('title', 'Gates & Queues Flow - AI Crowd Management')

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
    <a href="{{ route('dashboard.zones') }}" class="nav-link">
        <i class="fa-solid fa-map-location-dot"></i> Zone Heatmap
    </a>
    <a href="{{ route('dashboard.traffic') }}" class="nav-link active">
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

<!-- Middle Grid Layout: Gates and Queues side-by-side -->
<section class="middle-grid-section two-columns">
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
</section>

<!-- Hourly Crowd Trend Chart underneath -->
<section class="hourly-trend-section" style="margin-top: 24px;">
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
