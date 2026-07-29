/**
 * Dashboard API Service Class
 * Handles fetching data, notification endpoints, and offline state logic.
 */
class DashboardApiService {
    constructor() {
        this.consecutiveFailures = 0;
        this.maxFailuresAllowed = 3;
        this.heartbeatTimeoutSeconds = 20; // from config
        this.isOffline = false;
        this.onStateChangeCallback = null;
        
        // Fetch CSRF Token for POST requests
        this.csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
    }

    /**
     * Get dashboard consolidated data.
     */
    async fetchDashboardData() {
        try {
            const response = await fetch('/api/dashboard', {
                method: 'GET',
                headers: {
                    'Accept': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });

            if (!response.ok) {
                throw new Error(`Server returned HTTP ${response.status}`);
            }

            const data = await response.json();
            
            // Successful request - reset counter
            this.consecutiveFailures = 0;
            
            // Evaluate connection state from payload
            this.evaluateSystemHealth(data);

            return data;
        } catch (error) {
            this.consecutiveFailures++;
            console.error('API Fetch Error:', error);
            
            if (this.consecutiveFailures >= this.maxFailuresAllowed) {
                this.setOfflineState(true, 'Connection to Laravel server lost.');
            }
            
            throw error;
        }
    }

    /**
     * Get notifications list from Laravel backend.
     */
    async fetchNotifications(severity = '') {
        try {
            let url = '/api/dashboard/notifications';
            const separator = url.includes('?') ? '&' : '?';
            url += `${separator}t=${Date.now()}`;
            if (severity && severity !== 'all') {
                url += `&severity=${severity}`;
            }

            const response = await fetch(url, {
                method: 'GET',
                headers: {
                    'Accept': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });

            if (!response.ok) throw new Error('Failed to fetch notifications');
            return await response.json();
        } catch (error) {
            console.error('Fetch Notifications Error:', error);
            throw error;
        }
    }

    /**
     * Acknowledge / Read a specific notification.
     */
    async markAsRead(notificationId) {
        try {
            const response = await fetch(`/api/dashboard/notifications/${notificationId}/read`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                    'X-CSRF-TOKEN': this.csrfToken,
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });

            if (!response.ok) throw new Error('Failed to mark notification as read');
            return await response.json();
        } catch (error) {
            console.error('Mark Read Error:', error);
            throw error;
        }
    }

    /**
     * Mark all notifications as read.
     */
    async markAllAsRead() {
        try {
            const response = await fetch('/api/dashboard/notifications/read-all', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                    'X-CSRF-TOKEN': this.csrfToken,
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });

            if (!response.ok) throw new Error('Failed to mark all as read');
            return await response.json();
        } catch (error) {
            console.error('Mark All Read Error:', error);
            throw error;
        }
    }

    /**
     * Get list of criminal records.
     */
    async fetchCriminalRecords() {
        try {
            const response = await fetch('/api/criminal-records?t=' + Date.now(), {
                method: 'GET',
                headers: {
                    'Accept': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });
            if (!response.ok) throw new Error('Failed to fetch criminal records');
            return await response.json();
        } catch (error) {
            console.error('Fetch Criminal Records Error:', error);
            throw error;
        }
    }

    /**
     * Get active detections list.
     */
    async fetchCriminalDetections() {
        try {
            const response = await fetch('/api/criminal-detections?t=' + Date.now(), {
                method: 'GET',
                headers: {
                    'Accept': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });
            if (!response.ok) throw new Error('Failed to fetch criminal detections');
            return await response.json();
        } catch (error) {
            console.error('Fetch Criminal Detections Error:', error);
            throw error;
        }
    }

    /**
     * Acknowledge a criminal detection.
     */
    async acknowledgeCriminalDetection(detectionId) {
        try {
            const response = await fetch(`/api/criminal-detections/${detectionId}/acknowledge`, {
                method: 'PATCH',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                    'X-CSRF-TOKEN': this.csrfToken,
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });
            if (!response.ok) throw new Error('Failed to acknowledge detection');
            return await response.json();
        } catch (error) {
            console.error('Acknowledge Detection Error:', error);
            throw error;
        }
    }

    /**
     * Evaluates AI heartbeat timeouts and connectivity states.
     */
    evaluateSystemHealth(data) {
        if (!data || !data.success) {
            this.setOfflineState(true, 'Invalid API data format.');
            return;
        }

        const system = data.system || {};
        
        // 1. Check if AI service is reporting disconnected
        if (system.ai_connected === false) {
            this.setOfflineState(true, 'AI service disconnected.');
            return;
        }

        // 2. Check if the heartbeat is stale
        if (system.last_heartbeat_at) {
            const lastHeartbeat = new Date(system.last_heartbeat_at);
            const now = new Date();
            const differenceSeconds = Math.abs((now - lastHeartbeat) / 1000);
            
            if (differenceSeconds > this.heartbeatTimeoutSeconds) {
                this.setOfflineState(true, 'AI heartbeat timeout.');
                return;
            }
        }

        // All checks passed -> Online / Live
        this.setOfflineState(false);
    }

    /**
     * Sets the state of the dashboard offline alert and triggers callbacks.
     */
    setOfflineState(offline, reason = '') {
        const stateChanged = this.isOffline !== offline;
        this.isOffline = offline;

        if (stateChanged && this.onStateChangeCallback) {
            this.onStateChangeCallback(this.isOffline, reason);
        }
    }

    /**
     * Subscribe to online/offline state change notifications.
     */
    onStateChange(callback) {
        this.onStateChangeCallback = callback;
    }
}

// Instantiate and expose globally
window.apiService = new DashboardApiService();
