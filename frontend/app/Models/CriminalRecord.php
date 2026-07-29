<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\HasMany;

class CriminalRecord extends Model
{
    use HasFactory;

    protected $table = 'criminal_records';

    protected $fillable = [
        'name',
        'criminal_code',
        'profile_image',
        'description',
        'status',
    ];

    /**
     * Get the detections for the criminal record.
     */
    public function detections(): HasMany
    {
        return $this->hasMany(CriminalDetection::class, 'criminal_record_id');
    }
}
