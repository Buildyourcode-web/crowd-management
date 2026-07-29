<?php

namespace Tests\Feature;

use App\Models\AlertNotification;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Cache;
use Illuminate\Support\Facades\Http;
use Tests\TestCase;

class DashboardTest extends TestCase
{
    use RefreshDatabase;

    protected function setUp(): void
    {
        parent::setUp();
        
        // Define configuration values for testing environment
        config(['crowd-management.api_key' => 'test_secret_key']);
        config(['crowd-management.api_url' => 'http://test-ai-service.local']);
        config(['crowd-management.mock_mode' => false]);
    }

    /**
     * 1. Test that the dashboard page loads.
     */
    public function test_dashboard_page_loads(): void
    {
        $response = $this->get('/dashboard');

        $response->assertStatus(200);
        $response->assertSee('AI Crowd Management Dashboard');
    }

    /**
     * 2. Test that the dashboard API returns the correct structure.
     */
    public function test_dashboard_api_structure(): void
    {
        // Mock successful AI API call
        Http::fake([
            'http://test-ai-service.local/api/crowd-data' => Http::response($this->getValidAiPayload(), 200)
        ]);

        $response = $this->getJson('/api/dashboard');

        $response->assertStatus(200)
                 ->assertJsonStructure([
                     'success',
                     'generated_at',
                     'system' => ['status', 'ai_connected', 'camera_connected', 'last_heartbeat_at', 'stale_data'],
                     'summary' => ['total_visits', 'people_present', 'total_entries', 'total_exits'],
                     'zones' => [
                         '*' => ['id', 'name', 'current_count', 'capacity', 'occupancy_percentage', 'status']
                     ],
                     'gates',
                     'queues',
                     'criminal_detection',
                     'hourly_trend'
                 ]);
    }

    /**
     * 3. Test that the AI API key validation works.
     */
    public function test_ai_push_requires_api_key(): void
    {
        // Unauthenticated request
        $response = $this->postJson('/api/ai/crowd-data', $this->getValidAiPushPayload());
        $response->assertStatus(401);

        // Request with wrong key
        $response = $this->withHeaders(['X-AI-API-KEY' => 'wrong_key'])
                         ->postJson('/api/ai/crowd-data', $this->getValidAiPushPayload());
        $response->assertStatus(401);

        // Authenticated request
        $response = $this->withHeaders(['X-AI-API-KEY' => 'test_secret_key'])
                         ->postJson('/api/ai/crowd-data', $this->getValidAiPushPayload());
        $response->assertStatus(200);
    }

    /**
     * 4. Test that invalid AI push payloads trigger validation errors.
     */
    public function test_invalid_ai_payload_validation(): void
    {
        $invalidPayload = [
            'summary' => [
                'total_entries' => 'not-an-integer', // should be int
            ]
        ];

        $response = $this->withHeaders(['X-AI-API-KEY' => 'test_secret_key'])
                         ->postJson('/api/ai/crowd-data', $invalidPayload);

        $response->assertStatus(422)
                 ->assertJsonStructure(['success', 'message', 'errors']);
    }

    /**
     * 5. Test that duplicate detection events do not create duplicate notifications.
     */
    public function test_duplicate_events_do_not_create_duplicate_notifications(): void
    {
        $payload = $this->getValidAiPushPayload();
        
        // Add a criminal detection with a specific detection_id
        $payload['criminal_detection'] = [
            'detected' => true,
            'detection_id' => 'DET-TEST-001',
            'person_reference' => 'Suspect A',
            'confidence' => 95.5,
            'image_url' => '/storage/detections/test.jpg',
            'camera_name' => 'Cam 1',
            'gate_name' => 'Gate 1',
            'zone_name' => 'Zone A',
            'detected_at' => now()->toIso8601String()
        ];

        // Push first time
        $response = $this->withHeaders(['X-AI-API-KEY' => 'test_secret_key'])
                         ->postJson('/api/ai/crowd-data', $payload);
        $response->assertStatus(200);

        // Verify notification is created
        $this->assertEquals(1, AlertNotification::where('type', 'criminal_detected')->count());

        // Reset processed cache for testing push itself, but the database should guard it
        cache()->forget('processed_event_EVENT-TEST-1001');

        // Push second time (simulating re-sending same event)
        $response = $this->withHeaders(['X-AI-API-KEY' => 'test_secret_key'])
                         ->postJson('/api/ai/crowd-data', $payload);
        $response->assertStatus(200);

        // Verify there is STILL only 1 notification in the database
        $this->assertEquals(1, AlertNotification::where('type', 'criminal_detected')->count());
    }

    /**
     * 6. Test marking a notification as read and read-all.
     */
    public function test_mark_notifications_as_read(): void
    {
        $notification = AlertNotification::create([
            'type' => 'zone_capacity',
            'severity' => 'warning',
            'title' => 'Zone C Warning',
            'message' => 'Zone C occupancy has exceeded limits',
            'is_read' => false,
        ]);

        $this->assertFalse((bool)$notification->is_read);

        // Mark single notification as read
        $response = $this->postJson("/api/dashboard/notifications/{$notification->id}/read");
        $response->assertStatus(200);
        
        $this->assertTrue($notification->fresh()->is_read);
        $this->assertNotNull($notification->fresh()->acknowledged_at);

        // Add 2 more unread notifications
        AlertNotification::create([
            'type' => 'queue_stopped',
            'severity' => 'warning',
            'title' => 'Queue 1 Stopped',
            'message' => 'Queue 1 stopped',
        ]);
        AlertNotification::create([
            'type' => 'gate_blocked',
            'severity' => 'critical',
            'title' => 'Gate 2 Blocked',
            'message' => 'Gate 2 blocked',
        ]);

        $this->assertEquals(2, AlertNotification::unread()->count());

        // Mark all as read
        $response = $this->postJson("/api/dashboard/notifications/read-all");
        $response->assertStatus(200);

        $this->assertEquals(0, AlertNotification::unread()->count());
    }

    /**
     * 7. Test zone full and near capacity alerts generation.
     */
    public function test_zone_limit_notifications_generation(): void
    {
        $payload = $this->getValidAiPayload();
        
        // Set Zone C to 95% (Near Capacity >= 90%)
        $payload['zones'][2] = [
            'id' => 'zone-c',
            'name' => 'Zone C',
            'current_count' => 760,
            'capacity' => 800,
        ];
        
        // Set Zone D to 100% (Zone Full >= 100%)
        $payload['zones'][3] = [
            'id' => 'zone-d',
            'name' => 'Zone D',
            'current_count' => 850,
            'capacity' => 850,
        ];

        Http::fake([
            'http://test-ai-service.local/api/crowd-data' => Http::response($payload, 200)
        ]);

        $this->getJson('/api/dashboard');

        // Check if alerts were created
        $this->assertTrue(AlertNotification::where('type', 'zone_capacity')->where('location', 'Zone C')->exists());
        $this->assertTrue(AlertNotification::where('type', 'zone_full')->where('location', 'Zone D')->exists());
    }

    /**
     * 8. Test system offline / AI disconnected status handling.
     */
    public function test_ai_disconnected_stale_data_handling(): void
    {
        // 1. Configure Http fake sequence: first call succeeds, second call fails
        Http::fake([
            'http://test-ai-service.local/api/crowd-data' => Http::sequence()
                ->push($this->getValidAiPayload(), 200)
                ->push([], 500)
        ]);

        // First call populates the cache
        $this->getJson('/api/dashboard');

        // Second call triggers failure and serves stale data
        $response = $this->getJson('/api/dashboard');
        
        // Verify response contains stale_data: true and ai_connected: false, but still returns 200 (serving cached stale data)
        $response->assertStatus(200)
                 ->assertJsonPath('system.ai_connected', false)
                 ->assertJsonPath('system.stale_data', true)
                 ->assertJsonPath('summary.total_entries', 9059);

        // Verify a disconnection notification has been created in the database
        $this->assertTrue(AlertNotification::where('type', 'ai_disconnected')->exists());
    }

    // Helper payloads
    protected function getValidAiPayload(): array
    {
        return [
            'success' => true,
            'generated_at' => now()->toIso8601String(),
            'system' => [
                'status' => 'live',
                'ai_connected' => true,
                'camera_connected' => true,
                'last_heartbeat_at' => now()->toIso8601String(),
            ],
            'summary' => [
                'total_visits' => 9059,
                'total_entries' => 9059,
                'total_exits' => 6876,
            ],
            'zones' => [
                ['id' => 'zone-a', 'name' => 'Zone A', 'current_count' => 100, 'capacity' => 1000],
                ['id' => 'zone-b', 'name' => 'Zone B', 'current_count' => 200, 'capacity' => 900],
                ['id' => 'zone-c', 'name' => 'Zone C', 'current_count' => 300, 'capacity' => 800],
                ['id' => 'zone-d', 'name' => 'Zone D', 'current_count' => 400, 'capacity' => 850],
            ],
            'gates' => [
                ['gate_number' => '01', 'entries' => 685, 'exits' => 397, 'status' => 'normal']
            ],
            'queues' => [
                ['queue_number' => '01', 'wait_minutes' => 3, 'movement' => 'moving']
            ],
            'criminal_detection' => null,
            'hourly_trend' => [
                ['time' => '6:00 AM', 'count' => 560]
            ],
        ];
    }

    protected function getValidAiPushPayload(): array
    {
        return [
            'event_id' => 'EVENT-TEST-1001',
            'timestamp' => now()->toIso8601String(),
            'summary' => [
                'total_entries' => 9059,
                'total_exits' => 6876,
            ],
            'zones' => [
                ['id' => 'zone-a', 'name' => 'Zone A', 'current_count' => 100, 'capacity' => 1000],
                ['id' => 'zone-b', 'name' => 'Zone B', 'current_count' => 200, 'capacity' => 900],
                ['id' => 'zone-c', 'name' => 'Zone C', 'current_count' => 300, 'capacity' => 800],
                ['id' => 'zone-d', 'name' => 'Zone D', 'current_count' => 400, 'capacity' => 850],
            ],
            'gates' => [],
            'queues' => [],
            'criminal_detection' => null,
            'hourly_trend' => [],
        ];
    }

    /**
     * 9. Test fetching criminal records from the API.
     */
    public function test_get_criminal_records_api(): void
    {
        // Seed a criminal record
        $record = \App\Models\CriminalRecord::create([
            'name' => 'Test Suspect',
            'criminal_code' => 'CRM-T99',
            'profile_image' => '/storage/detections/test.jpg',
            'description' => 'Test suspect record description',
            'status' => 'active',
        ]);

        $response = $this->getJson('/api/criminal-records');

        $response->assertStatus(200)
                 ->assertJsonPath('success', true)
                 ->assertJsonFragment([
                     'name' => 'Test Suspect',
                     'criminal_code' => 'CRM-T99',
                     'profile_image' => '/storage/detections/test.jpg',
                     'status' => 'active',
                 ]);
    }

    /**
     * 10. Test fetching active criminal detections from the API.
     */
    public function test_get_criminal_detections_api(): void
    {
        // Seed a criminal record
        $record = \App\Models\CriminalRecord::create([
            'name' => 'Test Suspect',
            'criminal_code' => 'CRM-T99',
            'profile_image' => '/storage/detections/test.jpg',
            'status' => 'active',
        ]);

        // Seed an active detection
        $detection = \App\Models\CriminalDetection::create([
            'criminal_record_id' => $record->id,
            'camera_id' => 'CAM-01',
            'zone_name' => 'Zone A',
            'captured_image' => '/storage/detections/cctv.jpg',
            'accuracy' => 97,
            'captured_at' => now(),
            'status' => 'detected',
        ]);

        $response = $this->getJson('/api/criminal-detections');

        $response->assertStatus(200)
                 ->assertJsonPath('success', true)
                 ->assertJsonFragment([
                     'camera_id' => 'CAM-01',
                     'zone_name' => 'Zone A',
                     'captured_image' => '/storage/detections/cctv.jpg',
                     'accuracy' => 97,
                     'status' => 'detected',
                 ]);
    }

    /**
     * 11. Test acknowledging a criminal detection through the API.
     */
    public function test_acknowledge_criminal_detection_api(): void
    {
        // Seed a criminal record
        $record = \App\Models\CriminalRecord::create([
            'name' => 'Test Suspect',
            'criminal_code' => 'CRM-T99',
            'profile_image' => '/storage/detections/test.jpg',
            'status' => 'active',
        ]);

        // Seed an active detection
        $detection = \App\Models\CriminalDetection::create([
            'criminal_record_id' => $record->id,
            'camera_id' => 'CAM-01',
            'zone_name' => 'Zone A',
            'captured_image' => '/storage/detections/cctv.jpg',
            'accuracy' => 97,
            'captured_at' => now(),
            'status' => 'detected',
        ]);

        // Assert unacknowledged in DB initially
        $this->assertEquals('detected', $detection->status);
        $this->assertNull($detection->acknowledged_at);

        // Call Acknowledge Endpoint
        $response = $this->patchJson("/api/criminal-detections/{$detection->id}/acknowledge");

        $response->assertStatus(200)
                 ->assertJsonPath('success', true)
                 ->assertJsonPath('message', 'Detection Acknowledged.');

        // Verify status changed to acknowledged and timestamp is populated in DB
        $freshDet = $detection->fresh();
        $this->assertEquals('acknowledged', $freshDet->status);
        $this->assertNotNull($freshDet->acknowledged_at);
    }

    /**
     * 12. Test that the Metrics page loads successfully.
     */
    public function test_metrics_page_loads(): void
    {
        $response = $this->get('/metrics');
        $response->assertStatus(200);
        $response->assertSee('AI Crowd Management Dashboard');
        $response->assertSee('Total Visits');
    }

    /**
     * 13. Test that the Zones page loads successfully.
     */
    public function test_zones_page_loads(): void
    {
        $response = $this->get('/zones');
        $response->assertStatus(200);
        $response->assertSee('AI Crowd Management Dashboard');
        $response->assertSee('Live 2D Schematic Floor Map');
    }

    /**
     * 14. Test that the Traffic page loads successfully.
     */
    public function test_traffic_page_loads(): void
    {
        $response = $this->get('/traffic');
        $response->assertStatus(200);
        $response->assertSee('AI Crowd Management Dashboard');
        $response->assertSee('Gate wise Entry/ Exit');
    }
}
