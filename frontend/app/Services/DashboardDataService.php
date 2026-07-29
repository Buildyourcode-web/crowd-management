<?php

namespace App\Services;

use App\Models\AlertNotification;
use App\Data\DashboardData;
use Illuminate\Support\Facades\Cache;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Log;

class DashboardDataService
{
    protected AiCrowdService $aiService;
    protected const CACHE_KEY_LAST_VALID_DATA = 'last_valid_dashboard_data';

    public function __construct(AiCrowdService $aiService)
    {
        $this->aiService = $aiService;
    }

    /**
     * Get the consolidated and normalized dashboard data.
     *
     * @return array
     */
    public function getDashboardData(): array
    {
        $aiConnected = true;
        $staleData = false;

        try {
            $rawPayload = $this->aiService->fetchCrowdData();
            
            // Check if it's the external API returning an error structure (if any)
            if (empty($rawPayload)) {
                throw new \Exception("Empty payload received from AI service.");
            }

            // Save successfully fetched data as last valid data
            Cache::put(self::CACHE_KEY_LAST_VALID_DATA, $rawPayload, 3600);
            
            // If we were previously marked as offline, we can trigger a restored alert
            $this->handleSystemRestorationAlerts();
            
        } catch (\Exception $e) {
            $aiConnected = false;
            $staleData = true;
            
            // Fallback to last valid cached data
            $rawPayload = Cache::get(self::CACHE_KEY_LAST_VALID_DATA);
            
            if (!$rawPayload) {
                // Return baseline empty schema if no cache exists
                $rawPayload = $this->getBaselineSchema();
            }

            $rawPayload['system']['ai_connected'] = false;
            $rawPayload['system']['stale_data'] = true;

            $this->handleSystemDisconnectionAlerts($e->getMessage());
        }

        // Normalize payload
        $dto = new DashboardData($rawPayload);
        $normalizedData = $dto->toArray();
        $normalizedData['system']['ai_connected'] = $aiConnected;
        $normalizedData['system']['stale_data'] = $staleData;

        // Process business rules and generate notifications in transactions
        $this->processBusinessRules($normalizedData);

        return $normalizedData;
    }

    /**
     * Process pushed AI crowd data (push model).
     *
     * @param array $data
     * @return array
     */
    public function processPushedData(array $data): array
    {
        // Add default status and settings
        $data['success'] = true;
        $data['generated_at'] = now()->toIso8601String();
        $data['system'] = [
            'status' => 'live',
            'ai_connected' => true,
            'camera_connected' => $data['system']['camera_connected'] ?? true,
            'last_heartbeat_at' => now()->toIso8601String(),
            'stale_data' => false,
            'mock_mode' => false,
        ];

        // Save pushed data as last valid data
        Cache::put(self::CACHE_KEY_LAST_VALID_DATA, $data, 3600);
        
        $this->handleSystemRestorationAlerts();

        // Normalize
        $dto = new DashboardData($data);
        $normalized = $dto->toArray();

        // Evaluate notifications
        $this->processBusinessRules($normalized);

        return $normalized;
    }

    /**
     * Process business rules and create alert notifications if thresholds are violated.
     */
    protected function processBusinessRules(array $data): void
    {
        DB::transaction(function () use ($data) {
            $now = now();
            
            // 1. Process Zone Occupancies
            foreach ($data['zones'] as $zone) {
                $occupancy = $zone['occupancy_percentage'];
                $zoneName = $zone['name'];
                $zoneId = $zone['id'];

                // 100% capacity check: Zone Full
                if ($occupancy >= 100) {
                    $eventId = 'ZONE_FULL_' . $zoneId . '_' . $now->format('Y-m-d_H:i'); // Unique within the current minute
                    $this->createAlertNotification([
                        'external_event_id' => $eventId,
                        'type' => 'zone_full',
                        'severity' => 'critical',
                        'title' => "{$zoneName} is FULL!",
                        'message' => "{$zoneName} has reached 100% capacity with {$zone['current_count']} people present.",
                        'location' => $zoneName,
                    ]);
                } 
                // 90% Near Capacity check
                elseif ($occupancy >= config('crowd-management.zone_critical_percentage', 90)) {
                    $eventId = 'ZONE_NEAR_CAPACITY_' . $zoneId . '_' . $now->format('Y-m-d_H:i');
                    $this->createAlertNotification([
                        'external_event_id' => $eventId,
                        'type' => 'zone_capacity',
                        'severity' => 'critical',
                        'title' => "{$zoneName} Near Capacity",
                        'message' => "{$zoneName} has reached {$occupancy}% occupancy ({$zone['current_count']}/{$zone['capacity']}).",
                        'location' => $zoneName,
                    ]);
                }
            }

            // 2. Process Queue Waiting Times and stopped movement
            $warningLimit = config('crowd-management.queue_warning_minutes', 10);
            foreach ($data['queues'] as $queue) {
                $qNum = $queue['queue_number'];
                $wait = $queue['wait_minutes'];
                $movement = $queue['movement'];

                if ($wait >= $warningLimit) {
                    $eventId = "QUEUE_WAIT_EXCESSIVE_{$qNum}_" . $now->format('Y-m-d_H:i');
                    $this->createAlertNotification([
                        'external_event_id' => $eventId,
                        'type' => 'queue_wait_time',
                        'severity' => 'warning',
                        'title' => "Long Queue Wait Time - Queue {$qNum}",
                        'message' => "Queue {$qNum} waiting time is {$wait} minutes, exceeding the limit of {$warningLimit} minutes.",
                        'location' => "Queue {$qNum}",
                    ]);
                }

                if ($movement === 'stopped') {
                    // Check if it was stopped in consecutive updates
                    $cacheKey = "queue_{$qNum}_stopped_state";
                    $wasStopped = Cache::get($cacheKey, false);
                    
                    if ($wasStopped) {
                        // Consecutive stopped state alert
                        $eventId = "QUEUE_CONSECUTIVE_STOPPED_{$qNum}_" . $now->format('Y-m-d_H'); // Unique per hour to avoid spamming
                        $this->createAlertNotification([
                            'external_event_id' => $eventId,
                            'type' => 'queue_stopped',
                            'severity' => 'critical',
                            'title' => "Queue {$qNum} Stopped Repeatedly",
                            'message' => "Queue {$qNum} remains completely stopped in consecutive updates. Visual inspection required.",
                            'location' => "Queue {$qNum}",
                        ]);
                    } else {
                        // Single stopped alert
                        $eventId = "QUEUE_STOPPED_{$qNum}_" . $now->format('Y-m-d_H:i');
                        $this->createAlertNotification([
                            'external_event_id' => $eventId,
                            'type' => 'queue_stopped',
                            'severity' => 'warning',
                            'title' => "Queue {$qNum} Stopped",
                            'message' => "Queue {$qNum} has stopped moving.",
                            'location' => "Queue {$qNum}",
                        ]);
                    }

                    Cache::put($cacheKey, true, 300);
                } else {
                    Cache::forget("queue_{$qNum}_stopped_state");
                }
            }

            // 3. Process Criminal Detections
            if (!empty($data['criminal_detection']) && !empty($data['criminal_detection']['detected'])) {
                $det = $data['criminal_detection'];
                $detId = $det['detection_id'];
                
                $eventId = $detId; // Use detection_id directly as unique event ID

                // Create alert notification log
                $this->createAlertNotification([
                    'external_event_id' => $eventId,
                    'type' => 'criminal_detected',
                    'severity' => 'critical',
                    'title' => 'Criminal Detected!',
                    'message' => "Match found for Watchlist Person: confidence {$det['confidence']}%. Location: {$det['camera_name']} at {$det['gate_name']} ({$det['zone_name']}).",
                    'location' => "{$det['zone_name']} - {$det['gate_name']}",
                    'image_url' => $det['image_url'],
                    'suspect_image_url' => $det['suspect_image_url'] ?? null,
                    'metadata' => [
                        'detection_id' => $detId,
                        'confidence' => $det['confidence'],
                        'camera_name' => $det['camera_name'],
                        'gate_name' => $det['gate_name'],
                        'zone_name' => $det['zone_name'],
                        'detected_at' => $det['detected_at'],
                    ]
                ]);

                // Register inside criminal_detections table
                $code = $det['person_reference'] ?? null;
                $record = $code ? \App\Models\CriminalRecord::where('criminal_code', $code)->first() : null;


                if ($record) {
                    $detExists = \App\Models\CriminalDetection::where('captured_image', $det['image_url'])
                        ->where('status', 'detected')
                        ->exists();
                    if (!$detExists) {
                        \App\Models\CriminalDetection::create([
                            'criminal_record_id' => $record->id,
                            'camera_id' => $det['camera_name'] ?? 'CAM-04',
                            'zone_name' => $det['zone_name'] ?? 'Zone A',
                            'captured_image' => $det['image_url'],
                            'accuracy' => (int)($det['confidence'] ?? 95),
                            'captured_at' => $det['detected_at'] ? \Carbon\Carbon::parse($det['detected_at']) : now(),
                            'status' => 'detected',
                        ]);
                    }
                }
            }

            // 3b. Process Face Scan Cleared (No Match) Alerts for Mock Testing
            if (!empty($data['face_scan_result']) && $data['face_scan_result']['status'] === 'cleared') {
                $scan = $data['face_scan_result'];
                $this->createAlertNotification([
                    'external_event_id' => $scan['scan_id'],
                    'type' => 'face_scan_cleared',
                    'severity' => 'info',
                    'title' => 'Face Scan: Cleared',
                    'message' => "CCTV processed face scan: citizen cleared. No watchlist matches found on {$scan['camera_name']}.",
                    'location' => $scan['camera_name'],
                ]);
            }

            // 4. Process Gate Blocks
            foreach ($data['gates'] as $gate) {
                if ($gate['status'] === 'blocked') {
                    $gNum = $gate['gate_number'];
                    $eventId = "GATE_BLOCKED_{$gNum}_" . $now->format('Y-m-d_H:i');
                    $this->createAlertNotification([
                        'external_event_id' => $eventId,
                        'type' => 'gate_blocked',
                        'severity' => 'critical',
                        'title' => "Gate {$gNum} Blocked",
                        'message' => "AI/ML service reports Gate {$gNum} is currently blocked.",
                        'location' => "Gate {$gNum}",
                    ]);
                }
            }
        });
    }

    /**
     * Create an alert notification if it doesn't already exist.
     */
    protected function createAlertNotification(array $attributes): void
    {
        if (!empty($attributes['external_event_id'])) {
            $exists = AlertNotification::where('external_event_id', $attributes['external_event_id'])->exists();
            if ($exists) {
                return;
            }
        }

        AlertNotification::create($attributes);
    }

    /**
     * Handle notifications when AI Service disconnects.
     */
    protected function handleSystemDisconnectionAlerts(string $errorMsg): void
    {
        DB::transaction(function () use ($errorMsg) {
            // Check if active AI disconnection notice already exists in the last hour
            $eventId = 'AI_SERVICE_DISCONNECTED_' . now()->format('Y-m-d_H');
            
            $exists = AlertNotification::where('external_event_id', $eventId)->exists();
            if (!$exists) {
                AlertNotification::create([
                    'external_event_id' => $eventId,
                    'type' => 'ai_disconnected',
                    'severity' => 'critical',
                    'title' => 'AI Service Disconnected',
                    'message' => "The dashboard was unable to fetch fresh data from the AI server. Status is set to offline. Error: {$errorMsg}",
                    'location' => 'AI Core Server',
                ]);
            }
        });
    }

    /**
     * Handle notifications when AI Service is restored.
     */
    protected function handleSystemRestorationAlerts(): void
    {
        DB::transaction(function () {
            // Check if there's a recent AI disconnection notification that is unread
            // If so, mark it as read and create a restored alert
            $unreadDisconnection = AlertNotification::where('type', 'ai_disconnected')
                ->where('is_read', false)
                ->first();

            if ($unreadDisconnection) {
                // Mark disconnection alert as read
                $unreadDisconnection->update(['is_read' => true]);

                // Create system restored alert
                $eventId = 'AI_SERVICE_RESTORED_' . now()->getTimestamp();
                AlertNotification::create([
                    'external_event_id' => $eventId,
                    'type' => 'ai_restored',
                    'severity' => 'success',
                    'title' => 'AI Service Restored',
                    'message' => 'Connection to the AI Core Server has been successfully re-established.',
                    'location' => 'AI Core Server',
                ]);
            }
        });
    }

    /**
     * Returns standard baseline schema for the application dashboard.
     */
    protected function getBaselineSchema(): array
    {
        return [
            'success' => false,
            'generated_at' => now()->toIso8601String(),
            'system' => [
                'status' => 'offline',
                'ai_connected' => false,
                'camera_connected' => false,
                'last_heartbeat_at' => now()->toIso8601String(),
                'stale_data' => true,
            ],
            'summary' => [
                'total_visits' => 0,
                'people_present' => 0,
                'total_entries' => 0,
                'total_exits' => 0,
            ],
            'zones' => [
                ['id' => 'zone-a', 'name' => 'Zone A', 'current_count' => 0, 'capacity' => 1000],
                ['id' => 'zone-b', 'name' => 'Zone B', 'current_count' => 0, 'capacity' => 900],
                ['id' => 'zone-c', 'name' => 'Zone C', 'current_count' => 0, 'capacity' => 800],
                ['id' => 'zone-d', 'name' => 'Zone D', 'current_count' => 0, 'capacity' => 850],
            ],
            'gates' => [],
            'queues' => [],
            'criminal_detection' => null,
            'hourly_trend' => [],
        ];
    }
}
