<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="csrf-token" content="{{ csrf_token() }}">
    <title>@yield('title', 'AI Crowd Management Dashboard')</title>
    
    <!-- Google Fonts: Outfit -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    
    <!-- FontAwesome for Premium Icons -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    
    <!-- Custom Style Sheet -->
    <link rel="stylesheet" href="{{ asset('css/dashboard.css') }}?v={{ time() }}">
</head>
<body>
    <div id="app" class="dashboard-wrapper">
        @yield('content')
    </div>

    <script>
        window.alertSoundUrls = {
            standard: "{{ asset('audio/alert-notification.mp3') }}",
            danger: "{{ asset('audio/Danger-alert.mp3') }}",
            red_zone: "{{ asset('audio/red-zone-alert.mp3') }}",
            orange: "{{ asset('audio/Zone-Orange.mp3') }}"
        };
    </script>

    <!-- Chart.js CDN -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    
    <!-- Dashboard Scripts -->
    <script src="{{ asset('js/dashboard-api.js') }}?v={{ time() }}"></script>
    <script src="{{ asset('js/notifications.js') }}?v={{ time() }}"></script>
    <script src="{{ asset('js/crowd-chart.js') }}?v={{ time() }}"></script>
    <script src="{{ asset('js/dashboard.js') }}?v={{ time() }}"></script>
</body>
</html>
