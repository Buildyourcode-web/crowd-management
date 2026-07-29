<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Http\Requests\AiCrowdDataRequest;
use App\Services\DashboardDataService;
use Illuminate\Http\JsonResponse;
use Illuminate\Support\Facades\Log;

class DashboardApiController extends Controller
{
    protected DashboardDataService $dataService;

    public function __construct(DashboardDataService $dataService)
    {
        $this->dataService = $dataService;
    }

    /**
     * Get consolidated crowd management data.
     *
     * @return JsonResponse
     */
    public function index(): JsonResponse
    {
        try {
            $data = $this->dataService->getDashboardData();
            return response()->json($data);
        } catch (\Exception $e) {
            Log::error("Dashboard API error: " . $e->getMessage());
            return response()->json([
                'success' => false,
                'message' => 'Internal server error occurred while fetching dashboard data.',
            ], 500);
        }
    }

    /**
     * Receive pushed crowd data from AI/ML services.
     *
     * @param AiCrowdDataRequest $request
     * @return JsonResponse
     */
    public function receiveCrowdData(AiCrowdDataRequest $request): JsonResponse
    {
        try {
            $validated = $request->validated();
            
            // Log incoming AI pushed data
            Log::info("Received crowd data push from AI service", [
                'event_id' => $validated['event_id'] ?? 'N/A',
                'timestamp' => $validated['timestamp'] ?? 'N/A',
            ]);

            // If an event_id is provided, check if it was already processed to avoid reprocessing
            if (!empty($validated['event_id'])) {
                // We can use a cache key to track processed event IDs
                $cacheKey = 'processed_event_' . $validated['event_id'];
                if (cache()->has($cacheKey)) {
                    Log::warning("Duplicate event push detected: " . $validated['event_id']);
                    return response()->json([
                        'success' => true,
                        'message' => 'Event already processed.',
                        'duplicate' => true,
                    ]);
                }
                cache()->put($cacheKey, true, 600); // cache for 10 minutes
            }

            $data = $this->dataService->processPushedData($validated);

            return response()->json([
                'success' => true,
                'message' => 'Crowd data successfully updated.',
                'data' => $data,
            ]);
        } catch (\Exception $e) {
            Log::error("Failed to process pushed AI crowd data: " . $e->getMessage());
            return response()->json([
                'success' => false,
                'message' => 'Internal server error occurred while processing pushed data.',
            ], 500);
        }
    }
}
