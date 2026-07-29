@props(['id', 'type', 'severity', 'title', 'message', 'location', 'imageUrl', 'isRead', 'time', 'requiresAcknowledgement'])

@php
    $severityClass = match($severity) {
        'critical' => 'severity-critical',
        'warning' => 'severity-warning',
        'success' => 'severity-success',
        default => 'severity-info'
    };
    
    $icon = match($severity) {
        'critical' => 'fa-circle-exclamation',
        'warning' => 'fa-triangle-exclamation',
        'success' => 'fa-circle-check',
        default => 'fa-circle-info'
    };
@endphp

<div class="notification-item {{ $isRead ? 'read' : 'unread' }} {{ $severityClass }}" data-id="{{ $id }}">
    <div class="notification-item-icon">
        <i class="fa-solid {{ $icon }}"></i>
    </div>
    <div class="notification-item-details">
        <div class="notification-item-meta">
            <span class="notification-item-title">{{ $title }}</span>
            <span class="notification-item-time">{{ $time }}</span>
        </div>
        <p class="notification-item-msg">{{ $message }}</p>
        
        @if($location)
            <div class="notification-item-location">
                <i class="fa-solid fa-location-dot"></i> {{ $location }}
            </div>
        @endif

        @if($imageUrl)
            <div class="notification-item-evidence">
                <img src="{{ $imageUrl }}" alt="Detection evidence snapshot" class="notification-item-img">
            </div>
        @endif

        @if(!$isRead)
            <div class="notification-item-actions">
                <button type="button" class="btn btn-acknowledge" onclick="acknowledgeAlert({{ $id }})">
                    @if($severity === 'critical')
                        Acknowledge
                    @else
                        Mark as Read
                    @endif
                </button>
            </div>
        @endif
    </div>
</div>
