@props(['status'])

@php
    $statusLower = strtolower($status);
    $dotClass = match($statusLower) {
        'normal', 'moving', 'live' => 'dot-green',
        'warning', 'slow' => 'dot-yellow',
        'blocked', 'critical', 'stopped', 'offline' => 'dot-red',
        default => 'dot-grey'
    };
    
    $labelText = match($statusLower) {
        'normal', 'live' => 'Normal',
        'moving' => 'Moving',
        'warning' => 'Warning',
        'slow' => 'Slow',
        'blocked' => 'Blocked',
        'stopped' => 'Stopped',
        'offline' => 'Offline',
        default => ucfirst($status)
    };
@endphp

<div class="status-indicator-wrapper" title="{{ $labelText }}">
    <span class="status-dot {{ $dotClass }}" aria-hidden="true"></span>
    <span class="status-label">{{ $labelText }}</span>
</div>
