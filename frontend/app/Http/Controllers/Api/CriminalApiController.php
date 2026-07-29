<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Models\CriminalRecord;
use App\Models\CriminalDetection;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Log;

class CriminalApiController extends Controller
{
    /**
     * Get list of all active criminal records from database.
     *
     * @return JsonResponse
     */
    public function indexRecords(): JsonResponse
    {
        try {
            $records = CriminalRecord::where('status', 'active')->get();
            
            // Query active records directly from database without seeding fallbacks

            return response()->json([
                'success' => true,
                'records' => $records,
            ]);
        } catch (\Exception $e) {
            Log::error("Failed to fetch criminal records: " . $e->getMessage());
            return response()->json([
                'success' => false,
                'message' => 'Internal server error while fetching criminal records.',
            ], 500); 
        }
    }

    /**
     * Get list of all unacknowledged CCTV criminal detections.
     *
     * @return JsonResponse
     */
    public function indexDetections(): JsonResponse
    {
        try {
            $rawDetections = CriminalDetection::with('criminalRecord')
                ->orderBy('created_at', 'desc')
                ->take(10)
                ->get();

            // Returns database records only

            $detections = $rawDetections->map(function ($det) {
                return [
                    'id' => $det->id,
                    'criminal_record_id' => $det->criminal_record_id,
                    'camera_id' => $det->camera_id,
                    'zone_name' => $det->zone_name,
                    'captured_image' => $det->captured_image,
                    'accuracy' => $det->accuracy,
                    'captured_at' => $det->captured_at ? $det->captured_at->toIso8601String() : null,
                    'status' => $det->status,
                    'acknowledged_at' => $det->acknowledged_at ? $det->acknowledged_at->toIso8601String() : null,
                    'criminal' => $det->criminalRecord ? [
                        'name' => $det->criminalRecord->name,
                        'criminal_code' => $det->criminalRecord->criminal_code,
                        'profile_image' => $det->criminalRecord->profile_image,
                        'description' => $det->criminalRecord->description,
                    ] : null
                ];
            });

            return response()->json([
                'success' => true,
                'detections' => $detections,
            ]);
        } catch (\Exception $e) {
            Log::error("Failed to fetch criminal detections: " . $e->getMessage());
            return response()->json([
                'success' => false,
                'message' => 'Internal server error while fetching criminal detections.',
            ], 500);
        }
    }

    /**
     * Acknowledge a specific detection.
     *
     * @param int $id
     * @return JsonResponse
     */
    public function acknowledgeDetection(int $id): JsonResponse
    {
        try {
            $result = DB::transaction(function () use ($id) {
                $detection = CriminalDetection::find($id);

                if (!$detection) {
                    return [
                        'status' => 404,
                        'response' => [
                            'success' => false,
                            'message' => 'Criminal detection not found.',
                        ]
                    ];
                }

                if ($detection->status === 'acknowledged') {
                    return [
                        'status' => 400,
                        'response' => [
                            'success' => false,
                            'message' => 'Detection already acknowledged.',
                        ]
                    ];
                }

                // Update detection status
                $detection->update([
                    'status' => 'acknowledged',
                    'acknowledged_at' => now(),
                ]);

                // Also update any related system notification in alert_notifications (if exists)
                // The alert_notifications might hold a copy for the drawer alert logs
                $alertNotification = \App\Models\AlertNotification::where('type', 'criminal_detected')
                    ->where('message', 'like', "%{$detection->camera_id}%")
                    ->where('message', 'like', "%{$detection->accuracy}%")
                    ->where('is_read', false)
                    ->first();

                if ($alertNotification) {
                    $alertNotification->update([
                        'is_read' => true,
                        'acknowledged_at' => now()
                    ]);
                }

                return [
                    'status' => 200,
                    'response' => [
                        'success' => true,
                        'message' => 'Detection Acknowledged.',
                        'detection_id' => $detection->id,
                        'acknowledged_at' => $detection->acknowledged_at ? $detection->acknowledged_at->toIso8601String() : null
                    ]
                ];
            });

            return response()->json($result['response'], $result['status']);

        } catch (\Exception $e) {
            Log::error("Failed to acknowledge criminal detection (ID {$id}): " . $e->getMessage());
            return response()->json([
                'success' => false,
                'message' => 'Internal server error during acknowledgment.',
            ], 500);
        }
    }
}
