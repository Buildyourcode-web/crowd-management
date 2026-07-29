<?php

namespace App\Services;

use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Log;

class AiCrowdService
{
    protected string $apiUrl;
    protected ?string $apiKey;
    protected int $timeout;

    public function __construct()
    {
        $this->apiUrl = config('crowd-management.api_url', 'http://127.0.0.1:8001');
        $this->apiKey = config('crowd-management.api_key');
        $this->timeout = config('crowd-management.timeout', 5);
    }

    /**
     * Fetch raw crowd management data from the real AI/ML service API.
     *
     * @return array
     * @throws \Exception
     */
    public function fetchCrowdData(): array
    {
        if (config('crowd-management.mock_mode')) {
            return $this->getMockData();
        }

        try {
            $response = Http::withHeaders([
                'X-AI-API-KEY' => $this->apiKey,
                'Accept' => 'application/json',
            ])
            ->timeout($this->timeout)
            ->connectTimeout($this->timeout)
            ->get($this->apiUrl . '/api/crowd-data');

            if ($response->successful()) {
                return $response->json();
            }

            throw new \Exception("AI service returned status code " . $response->status());
        } catch (\Exception $e) {
            // Log the error without leaking the api key secret
            Log::error("Failed to fetch crowd data from AI service: " . $e->getMessage(), [
                'api_url' => $this->apiUrl,
                'exception_class' => get_class($e),
            ]);

            throw $e;
        }
    }

}
