<?php

use App\Http\Controllers\Api\DashboardApiController;
use App\Http\Controllers\Api\NotificationController;
use App\Http\Controllers\Api\CriminalApiController;
use Illuminate\Support\Facades\Route;

/*
|--------------------------------------------------------------------------
| API Routes
|--------------------------------------------------------------------------
*/

// Dashboard data endpoint
Route::get('/dashboard', [DashboardApiController::class, 'index']);

// Notification management endpoints
Route::prefix('dashboard/notifications')->group(function () {
    Route::get('/', [NotificationController::class, 'index']);
    Route::post('/{notification}/read', [NotificationController::class, 'read']);
    Route::post('/read-all', [NotificationController::class, 'readAll']);
});

// Criminal Detections REST endpoints
Route::get('/criminal-records', [CriminalApiController::class, 'indexRecords']);
Route::get('/criminal-detections', [CriminalApiController::class, 'indexDetections']);
Route::patch('/criminal-detections/{id}/acknowledge', [CriminalApiController::class, 'acknowledgeDetection']);

// Secure AI/ML data push receiver endpoint
Route::post('/ai/crowd-data', [DashboardApiController::class, 'receiveCrowdData'])
    ->middleware(['ai.api.key', 'throttle:60,1']);
