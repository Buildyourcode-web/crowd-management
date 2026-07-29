<?php

return [
    'api_url' => env('AI_CROWD_API_URL', 'http://127.0.0.1:8001'),
    'api_key' => env('AI_CROWD_API_KEY'),
    'timeout' => (int) env('AI_CROWD_TIMEOUT', 5),
    'refresh_seconds' => (int) env('DASHBOARD_REFRESH_SECONDS', 5),
    'zone_warning_percentage' => (int) env('ZONE_WARNING_PERCENTAGE', 80),
    'zone_critical_percentage' => (int) env('ZONE_CRITICAL_PERCENTAGE', 90),
    'queue_warning_minutes' => (int) env('QUEUE_WARNING_MINUTES', 10),
    'heartbeat_timeout_seconds' => (int) env('AI_HEARTBEAT_TIMEOUT_SECONDS', 20),
    'mock_mode' => (bool) env('AI_CROWD_MOCK_MODE', false),
];
