<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\View\View;

class DashboardController extends Controller
{
    /**
     * Display the dashboard view.
     *
     * @return View
     */
    public function index(Request $request): View
    {
        // Simply return the dashboard index view
        return view('dashboard.index');
    }

    /**
     * Display the detailed attendance metrics view.
     */
    public function metrics(Request $request): View
    {
        return view('dashboard.metrics');
    }

    /**
     * Display the detailed zone crowd heatmap view.
     */
    public function zones(Request $request): View
    {
        return view('dashboard.zones');
    }

    /**
     * Display the gate entry/exit and queue traffic view.
     */
    public function traffic(Request $request): View
    {
        return view('dashboard.traffic');
    }

    /**
     * Display the live CCTV cameras grid view.
     */
    public function cameras(Request $request): View
    {
        return view('dashboard.cameras');
    }
}
