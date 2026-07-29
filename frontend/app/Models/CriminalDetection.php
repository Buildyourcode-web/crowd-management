<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\Builder;

class CriminalDetection extends Model
{
    use HasFactory;

    protected $table = 'criminal_detections';

    protected $fillable = [
        'criminal_record_id',
        'camera_id',
        'zone_name',
        'captured_image',
        'accuracy',
        'captured_at',
        'status',
        'acknowledged_at',
    ];

    protected $casts = [
        'captured_at' => 'datetime',
        'acknowledged_at' => 'datetime',
        'accuracy' => 'integer',
    ];

    /**
     * Get the criminal record associated with the detection.
     */
    public function criminalRecord(): BelongsTo
    {
        return $this->belongsTo(CriminalRecord::class, 'criminal_record_id');
    }

    /**
     * Scope a query to only include active (unacknowledged) detections.
     */
    public function scopeActive(Builder $query): Builder
    {
        return $query->where('status', 'detected');
    }
}
