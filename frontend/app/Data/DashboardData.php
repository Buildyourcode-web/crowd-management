<?php

namespace App\Data;

class DashboardData
{
    public bool $success;
    public string $generatedAt;
    public array $system;
    public array $summary;
    public array $zones;
    public array $gates;
    public array $queues;
    public ?array $criminalDetection;
    public array $hourlyTrend;

    public function __construct(array $data)
    {
        $this->success = $data['success'] ?? true;
        $this->generatedAt = $data['generated_at'] ?? now()->toIso8601String();
        
        $this->system = [
            'status' => $data['system']['status'] ?? 'live',
            'ai_connected' => (bool) ($data['system']['ai_connected'] ?? true),
            'camera_connected' => (bool) ($data['system']['camera_connected'] ?? true),
            'last_heartbeat_at' => $data['system']['last_heartbeat_at'] ?? now()->toIso8601String(),
            'stale_data' => (bool) ($data['system']['stale_data'] ?? false),
            'mock_mode' => (bool) ($data['system']['mock_mode'] ?? false),
        ];

        // Retrieve entries/exits
        $entries = (int) ($data['summary']['total_entries'] ?? 0);
        $exits = (int) ($data['summary']['total_exits'] ?? 0);
        
        // Dynamically calculate people present: entries - exits
        $peoplePresent = max(0, $entries - $exits);
        
        // Total visits can be explicitly provided or fallback to total_entries
        $totalVisits = (int) ($data['summary']['total_visits'] ?? $entries);

        $this->summary = [
            'total_visits' => $totalVisits,
            'people_present' => $peoplePresent,
            'total_entries' => $entries,
            'total_exits' => $exits,
        ];

        $this->zones = array_map(function ($zone) {
            $count = (int) ($zone['current_count'] ?? 0);
            $capacity = (int) ($zone['capacity'] ?? 1);
            $occupancy = round(($count / $capacity) * 100, 1);
            
            // Re-evaluate status based on occupancy
            $status = 'normal';
            if ($occupancy >= config('crowd-management.zone_critical_percentage', 90)) {
                $status = 'critical';
            } elseif ($occupancy >= config('crowd-management.zone_warning_percentage', 80)) {
                $status = 'warning';
            }

            return [
                'id' => $zone['id'] ?? '',
                'name' => $zone['name'] ?? '',
                'current_count' => $count,
                'capacity' => $capacity,
                'occupancy_percentage' => $occupancy,
                'status' => $status,
            ];
        }, $data['zones'] ?? []);

        $this->gates = array_map(function ($gate) {
            return [
                'gate_number' => $gate['gate_number'] ?? '',
                'entries' => (int) ($gate['entries'] ?? 0),
                'exits' => (int) ($gate['exits'] ?? 0),
                'status' => $gate['status'] ?? 'normal',
            ];
        }, $data['gates'] ?? []);

        $this->queues = array_map(function ($queue) {
            return [
                'queue_number' => $queue['queue_number'] ?? '',
                'wait_minutes' => (int) ($queue['wait_minutes'] ?? 0),
                'movement' => $queue['movement'] ?? 'moving',
            ];
        }, $data['queues'] ?? []);

        if (!empty($data['criminal_detection']) && !empty($data['criminal_detection']['detected'])) {
            $this->criminalDetection = [
                'detected' => true,
                'detection_id' => $data['criminal_detection']['detection_id'] ?? '',
                'person_reference' => $data['criminal_detection']['person_reference'] ?? 'Watchlist Match',
                'confidence' => (float) ($data['criminal_detection']['confidence'] ?? 0.0),
                'image_url' => $data['criminal_detection']['image_url'] ?? '',
                'suspect_image_url' => $data['criminal_detection']['suspect_image_url'] ?? '',
                'camera_name' => $data['criminal_detection']['camera_name'] ?? 'Unknown Camera',
                'gate_name' => $data['criminal_detection']['gate_name'] ?? 'Unknown Gate',
                'zone_name' => $data['criminal_detection']['zone_name'] ?? 'Unknown Zone',
                'detected_at' => $data['criminal_detection']['detected_at'] ?? now()->toIso8601String(),
            ];
        } else {
            $this->criminalDetection = null;
        }

        $this->hourlyTrend = array_map(function ($trend) {
            return [
                'time' => $trend['time'] ?? '',
                'count' => (int) ($trend['count'] ?? 0),
            ];
        }, $data['hourly_trend'] ?? []);
    }

    /**
     * Convert the normalized data to an array.
     */
    public function toArray(): array
    {
        return [
            'success' => $this->success,
            'generated_at' => $this->generatedAt,
            'system' => $this->system,
            'summary' => $this->summary,
            'zones' => $this->zones,
            'gates' => $this->gates,
            'queues' => $this->queues,
            'criminal_detection' => $this->criminalDetection,
            'hourly_trend' => $this->hourlyTrend,
        ];
    }
}
