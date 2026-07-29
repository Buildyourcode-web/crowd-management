<?php

use App\Http\Controllers\DashboardController;
use Illuminate\Support\Facades\Route;

Route::get('/', function () {
    return redirect()->route('dashboard');
});

Route::get('/dashboard', [DashboardController::class, 'index'])->name('dashboard');
Route::get('/metrics', [DashboardController::class, 'metrics'])->name('dashboard.metrics');
Route::get('/zones', [DashboardController::class, 'zones'])->name('dashboard.zones');
Route::get('/traffic', [DashboardController::class, 'traffic'])->name('dashboard.traffic');
Route::get('/cameras', [DashboardController::class, 'cameras'])->name('dashboard.cameras');
