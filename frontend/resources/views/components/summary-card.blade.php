@props(['title', 'value', 'icon', 'colorClass', 'id'])

<div class="summary-card" id="{{ $id }}">
    <div class="summary-card-icon-container {{ $colorClass }}">
        <i class="{{ $icon }}"></i>
    </div>
    <div class="summary-card-info">
        <span class="summary-card-title">{{ $title }}</span>
        <span class="summary-card-value font-numeric" data-target-value="{{ $value }}">
            {{ number_format($value) }}
        </span>
    </div>
</div>
