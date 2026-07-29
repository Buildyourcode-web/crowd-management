@props(['id', 'name', 'count', 'capacity', 'occupancy', 'status', 'type' => 'line'])

@php
    $occupancy = (float) $occupancy;
    $statusClass = 'zone-green';
    $labelText = 'Normal';
    
    if ($occupancy >= 100) {
        $statusClass = 'zone-red pulse-critical';
        $labelText = 'Zone Full';
    } elseif ($occupancy >= 90) {
        $statusClass = 'zone-red pulse-warning';
        $labelText = 'Near Capacity';
    } elseif ($occupancy >= 80) {
        $statusClass = 'zone-orange';
        $labelText = 'Near Capacity';
    } elseif ($occupancy >= 60) {
        $statusClass = 'zone-yellow';
        $labelText = 'Warning';
    }
@endphp

<div class="zone-card {{ $type === 'wave' ? 'waves-type zone-card-horizontal' : '' }} {{ $statusClass }}" id="card-{{ $id }}">
    @if($type === 'wave')
        <!-- Horizontal layout with live wavy sparkline trend -->
        
        <!-- Left Section: Details -->
        <div class="card-left-section">
            <span class="zone-card-name">{{ $name }}</span>
            <span class="zone-card-count font-numeric" data-val="{{ $count }}">{{ number_format($count) }}</span>
            <span class="zone-capacity-sub"><i class="fa-solid fa-users-viewfinder"></i> Cap: <span class="font-numeric">{{ number_format($capacity) }}</span></span>
        </div>
        
        <!-- Middle Section: Sparkline Chart -->
        <div class="card-chart-section">
            <div class="sparkline-container">
                <!-- Ticks on the left side of chart -->
                <div class="sparkline-y-ticks">
                    <span class="tick-label y-max">800</span>
                    <span class="tick-label y-mid-high">600</span>
                    <span class="tick-label y-mid">400</span>
                    <span class="tick-label y-mid-low">200</span>
                    <span class="tick-label y-min">0</span>
                </div>
                
                <div class="sparkline-svg-wrapper">
                    <svg class="sparkline-svg" viewBox="0 0 400 100" preserveAspectRatio="none">
                        <defs>
                            <!-- Gradients for filled area -->
                            <linearGradient id="area-grad-green" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="0%" stop-color="#10b981" stop-opacity="0.25"/>
                                <stop offset="100%" stop-color="#10b981" stop-opacity="0"/>
                            </linearGradient>
                            <linearGradient id="area-grad-yellow" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="0%" stop-color="#f59e0b" stop-opacity="0.25"/>
                                <stop offset="100%" stop-color="#f59e0b" stop-opacity="0"/>
                            </linearGradient>
                            <linearGradient id="area-grad-orange" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="0%" stop-color="#f97316" stop-opacity="0.25"/>
                                <stop offset="100%" stop-color="#f97316" stop-opacity="0"/>
                            </linearGradient>
                            <linearGradient id="area-grad-red" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="0%" stop-color="#ef4444" stop-opacity="0.25"/>
                                <stop offset="100%" stop-color="#ef4444" stop-opacity="0"/>
                            </linearGradient>
                        </defs>
                        
                        <!-- Dotted grid lines -->
                        <line class="grid-line" x1="0" y1="0" x2="400" y2="0" />
                        <line class="grid-line" x1="0" y1="25" x2="400" y2="25" />
                        <line class="grid-line" x1="0" y1="50" x2="400" y2="50" />
                        <line class="grid-line" x1="0" y1="75" x2="400" y2="75" />
                        <line class="grid-line" x1="0" y1="100" x2="400" y2="100" />
                        
                        <!-- Graph Paths -->
                        <path class="sparkline-area-path" d="" />
                        <path class="sparkline-line-path" d="" />
                        
                        <!-- Last point glowing dot -->
                        <circle class="sparkline-last-dot" cx="-10" cy="-10" r="4.5" />
                        <circle class="sparkline-last-dot-glow" cx="-10" cy="-10" r="9" />
                    </svg>
                </div>
            </div>
        </div>
        
        <!-- Right Section: Status & Percentage -->
        <div class="card-right-section">
            <span class="zone-card-label">{{ $labelText }}</span>
            <span class="zone-percentage font-numeric">{{ $occupancy }}%</span>
            <span class="capacity-subtext">of capacity</span>
        </div>
        
    @else
        <!-- Original vertical progress layout for the Overview page -->
        <div class="zone-card-header">
            <span class="zone-card-name">{{ $name }}</span>
            <span class="zone-card-label">{{ $labelText }}</span>
        </div>
        <div class="zone-card-body">
            <span class="zone-card-count font-numeric" data-val="{{ $count }}">{{ number_format($count) }}</span>
        </div>
        <div class="zone-card-footer">
            <div class="zone-progress-bg">
                <div class="zone-progress-bar" style="width: {{ min(100, $occupancy) }}%"></div>
            </div>
            <div class="zone-meta">
                <span class="zone-capacity">Cap: <span class="font-numeric">{{ number_format($capacity) }}</span></span>
                <span class="zone-percentage font-numeric">{{ $occupancy }}%</span>
            </div>
        </div>
    @endif
</div>
