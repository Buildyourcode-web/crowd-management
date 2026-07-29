<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Models\AlertNotification;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

class NotificationController extends Controller
{
    /**
     * Retrieve a list of notifications, sorted latest first.
     *
     * @param Request $request
     * @return JsonResponse
     */
    public function index(Request $request): JsonResponse
    {
        $query = AlertNotification::query()->orderBy('created_at', 'desc');

        // Optional severity filtering
        if ($request->has('severity') && in_array($request->query('severity'), ['critical', 'warning', 'info', 'success'])) {
            $query->severity($request->query('severity'));
        }

        $notifications = $query->get()->map(function ($notif) {
            return [
                'id' => $notif->id,
                'type' => $notif->type,
                'severity' => $notif->severity,
                'title' => $notif->title,
                'message' => $notif->message,
                'location' => $notif->location,
                'image_url' => $notif->image_url,
                'suspect_image_url' => $notif->suspect_image_url,
                'is_read' => $notif->is_read,
                'acknowledged_at' => $notif->acknowledged_at ? $notif->acknowledged_at->toIso8601String() : null,
                'created_at' => $notif->created_at->toIso8601String(),
                'relative_time' => $notif->created_at->diffForHumans(),
            ];
        });

        $unreadCount = AlertNotification::unread()->count();

        return response()->json([
            'success' => true,
            'unread_count' => $unreadCount,
            'notifications' => $notifications,
        ]);
    }

    /**
     * Mark a specific notification as read / acknowledged.
     *
     * @param int $id
     * @return JsonResponse
     */
    public function read(int $id): JsonResponse
    {
        $notification = AlertNotification::find($id);

        if (!$notification) {
            return response()->json([
                'success' => false,
                'message' => 'Notification not found.',
            ], 404);
        }

        $notification->update([
            'is_read' => true,
            'acknowledged_at' => now(),
        ]);

        return response()->json([
            'success' => true,
            'message' => 'Notification marked as read.',
            'unread_count' => AlertNotification::unread()->count(),
        ]);
    }

    /**
     * Mark all notifications as read.
     *
     * @return JsonResponse
     */
    public function readAll(): JsonResponse
    {
        AlertNotification::unread()->update([
            'is_read' => true,
            'acknowledged_at' => now(),
        ]);

        return response()->json([
            'success' => true,
            'message' => 'All notifications marked as read.',
            'unread_count' => 0,
        ]);
    }
}
