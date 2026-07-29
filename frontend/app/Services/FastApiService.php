<?php

namespace App\Services;

use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Log;

class FastApiService
{
    protected string $baseUrl;
    protected int $timeout;

    public function __construct()
    {
        $this->baseUrl = rtrim(env('FASTAPI_BASE_URL', 'http://127.0.0.1:8000/api/v1'), '/');
        $this->timeout = (int) env('AI_CROWD_TIMEOUT', 10);
    }

    // -------------------------------------------------------------------------
    // Helpers
    // -------------------------------------------------------------------------

    protected function get(string $path): array
    {
        try {
            $response = Http::timeout($this->timeout)
                ->acceptJson()
                ->get($this->baseUrl . $path);

            if ($response->successful()) {
                return $response->json() ?? [];
            }

            Log::warning("FastApiService GET {$path} returned {$response->status()}");
            return [];
        } catch (\Throwable $e) {
            Log::error("FastApiService GET {$path} failed: " . $e->getMessage());
            return [];
        }
    }

    protected function post(string $path, array $body = []): array
    {
        try {
            $response = Http::timeout($this->timeout)
                ->acceptJson()
                ->post($this->baseUrl . $path, $body);

            if ($response->successful()) {
                return $response->json() ?? [];
            }

            Log::warning("FastApiService POST {$path} returned {$response->status()}");
            return [];
        } catch (\Throwable $e) {
            Log::error("FastApiService POST {$path} failed: " . $e->getMessage());
            return [];
        }
    }

    protected function delete(string $path): array
    {
        try {
            $response = Http::timeout($this->timeout)
                ->acceptJson()
                ->delete($this->baseUrl . $path);

            if ($response->successful()) {
                return $response->json() ?? [];
            }

            Log::warning("FastApiService DELETE {$path} returned {$response->status()}");
            return [];
        } catch (\Throwable $e) {
            Log::error("FastApiService DELETE {$path} failed: " . $e->getMessage());
            return [];
        }
    }

    // -------------------------------------------------------------------------
    // Camera Endpoints
    // -------------------------------------------------------------------------

    /**
     * GET /cameras — List all cameras
     */
    public function getCameras(): array
    {
        return $this->get('/cameras');
    }

    /**
     * POST /cameras — Create a new camera
     */
    public function createCamera(array $data): array
    {
        return $this->post('/cameras', $data);
    }

    /**
     * POST /cameras/{id}/activate — Activate a camera
     */
    public function activateCamera(string $cameraId): array
    {
        return $this->post("/cameras/{$cameraId}/activate");
    }

    // -------------------------------------------------------------------------
    // AI Status
    // -------------------------------------------------------------------------

    /**
     * GET /ai/status — AI model status
     */
    public function getAiStatus(): array
    {
        return $this->get('/ai/status');
    }

    // -------------------------------------------------------------------------
    // Person Counter Endpoints
    // -------------------------------------------------------------------------

    /**
     * GET /person-counter/status — All cameras person counter status
     */
    public function getAllPersonCounterStatus(): array
    {
        $result = $this->get('/person-counter/status');
        // FastAPI may return a list directly or wrapped
        return is_array($result) ? $result : [];
    }

    /**
     * GET /person-counter/status/{camera_id}
     */
    public function getPersonCounterStatus(string $cameraId): array
    {
        return $this->get("/person-counter/status/{$cameraId}");
    }

    /**
     * POST /person-counter/start/{camera_id}
     */
    public function startPersonCounter(string $cameraId, array $body = []): array
    {
        return $this->post("/person-counter/start/{$cameraId}", $body);
    }

    /**
     * POST /person-counter/stop/{camera_id}
     */
    public function stopPersonCounter(string $cameraId): array
    {
        return $this->post("/person-counter/stop/{$cameraId}");
    }

    // -------------------------------------------------------------------------
    // Queue Management Endpoints
    // -------------------------------------------------------------------------

    /**
     * GET /queue/status — All cameras queue status
     */
    public function getAllQueueStatus(): array
    {
        $result = $this->get('/queue/status');
        return is_array($result) ? $result : [];
    }

    /**
     * GET /queue/status/{camera_id}
     */
    public function getQueueStatus(string $cameraId): array
    {
        return $this->get("/queue/status/{$cameraId}");
    }

    /**
     * POST /queue/start/{camera_id}
     */
    public function startQueue(string $cameraId, array $body = []): array
    {
        return $this->post("/queue/start/{$cameraId}", $body);
    }

    /**
     * POST /queue/stop/{camera_id}
     */
    public function stopQueue(string $cameraId): array
    {
        return $this->post("/queue/stop/{$cameraId}");
    }

    // -------------------------------------------------------------------------
    // Zone Monitoring Endpoints
    // -------------------------------------------------------------------------

    /**
     * GET /zone/status — All cameras zone status
     */
    public function getAllZoneStatus(): array
    {
        $result = $this->get('/zone/status');
        return is_array($result) ? $result : [];
    }

    /**
     * GET /zone/status/{camera_id}
     */
    public function getZoneStatus(string $cameraId): array
    {
        return $this->get("/zone/status/{$cameraId}");
    }

    /**
     * POST /zone/start/{camera_id}
     * Body: { zones: [{zone_id, zone_name, x1, y1, x2, y2}] }
     */
    public function startZone(string $cameraId, array $body = []): array
    {
        return $this->post("/zone/start/{$cameraId}", $body);
    }

    /**
     * POST /zone/stop/{camera_id}
     */
    public function stopZone(string $cameraId): array
    {
        return $this->post("/zone/stop/{$cameraId}");
    }

    // -------------------------------------------------------------------------
    // Face Recognition Endpoints
    // -------------------------------------------------------------------------

    /**
     * GET /face/persons — List all registered persons
     */
    public function getFacePersons(): array
    {
        return $this->get('/face/persons');
    }

    /**
     * GET /face/status/{camera_id}
     */
    public function getFaceStatus(string $cameraId): array
    {
        return $this->get("/face/status/{$cameraId}");
    }

    /**
     * POST /face/start/{camera_id}
     */
    public function startFace(string $cameraId): array
    {
        return $this->post("/face/start/{$cameraId}");
    }

    /**
     * POST /face/stop/{camera_id}
     */
    public function stopFace(string $cameraId): array
    {
        return $this->post("/face/stop/{$cameraId}");
    }

    /**
     * POST /face/register — Register a person with image (multipart)
     */
    public function registerFace(array $data, string $imagePath, string $imageName): array
    {
        try {
            $response = Http::timeout($this->timeout)
                ->acceptJson()
                ->attach('image', file_get_contents($imagePath), $imageName)
                ->post($this->baseUrl . '/face/register', [
                    'person_id' => $data['person_id'] ?? '',
                    'name'      => $data['name'] ?? '',
                ]);

            if ($response->successful()) {
                return $response->json() ?? [];
            }

            Log::warning("FastApiService POST /face/register returned {$response->status()}: " . $response->body());
            return ['error' => $response->json()['detail'] ?? 'Registration failed'];
        } catch (\Throwable $e) {
            Log::error("FastApiService POST /face/register failed: " . $e->getMessage());
            return ['error' => $e->getMessage()];
        }
    }

    /**
     * DELETE /face/{person_id}
     */
    public function deletePerson(string $personId): array
    {
        return $this->delete("/face/{$personId}");
    }

    /**
     * POST /face/reload — Reload embedding cache
     */
    public function reloadFace(): array
    {
        return $this->post('/face/reload');
    }
}
