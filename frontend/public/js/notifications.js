/**
 * Notifications Management Module
 */

class NotificationManager {
    constructor() {
        this.drawer = document.getElementById('notification-drawer');
        this.overlay = document.getElementById('drawer-overlay');
        this.listContainer = document.getElementById('notification-list');
        this.unreadBadge = document.getElementById('header-unread-badge');
        this.alertsBarCount = document.getElementById('alerts-bar-count-badge');
        this.alertsBar = document.getElementById('alerts-bar');
        this.drawerUnreadCount = document.getElementById('drawer-unread-count');
        this.filterTabs = document.querySelectorAll('.filter-tab');
        
        this.currentFilter = 'all';
        this.seenNotifications = new Set();
        this.isOpen = false;
        this.audioNeedsPlayOnInteraction = false;
        
        this.initEventListeners();
    }

    initEventListeners() {
        // Tab Filters click
        this.filterTabs.forEach(tab => {
            tab.addEventListener('click', (e) => {
                this.filterTabs.forEach(t => t.classList.remove('active'));
                tab.classList.add('active');
                this.currentFilter = tab.getAttribute('data-filter');
                this.reloadNotifications();
            });
        });

        // Accessibility Esc key to close drawer
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.isOpen) {
                this.toggleDrawer(false);
            }
        });

        // Warm up and unlock HTML5 Audio on first user interaction (click/keypress)
        const unlockAudio = () => {
            console.log("[Audio Debug] User interaction detected. Unlocking audio channel. Pending sound:", this.audioNeedsPlayOnInteraction);
            if (this.audioNeedsPlayOnInteraction) {
                const type = this.audioNeedsPlayOnInteraction;
                this.audioNeedsPlayOnInteraction = false;
                this.playNotificationSound(type);
            } else {
                // Play a brief silent click to warm up the browser's audio channel
                try {
                    const soundUrl = window.alertSoundUrls && window.alertSoundUrls.standard 
                        ? window.alertSoundUrls.standard 
                        : '/audio/alert-notification.mp3';
                    const audio = new Audio(soundUrl);
                    audio.volume = 0.001; // virtually silent
                    audio.play().then(() => {
                        console.log("[Audio Debug] Audio channel successfully warmed up and unlocked.");
                    }).catch((err) => {
                        console.warn("[Audio Debug] Silent warm up failed:", err);
                    });
                } catch (e) {
                    console.log("[Audio Debug] Audio unlock failed:", e);
                }
            }
            document.removeEventListener('click', unlockAudio);
            document.removeEventListener('keydown', unlockAudio);
        };
        document.addEventListener('click', unlockAudio);
        document.addEventListener('keydown', unlockAudio);
    }

    /**
     * Open or close the drawer
     */
    toggleDrawer(open) {
        this.isOpen = open;
        if (open) {
            this.drawer.classList.add('open');
            this.overlay.classList.add('open');
            this.reloadNotifications();
            
            // Set focus inside the drawer for accessibility
            const closeBtn = this.drawer.querySelector('.btn-close-drawer');
            if (closeBtn) closeBtn.focus();
        } else {
            this.drawer.classList.remove('open');
            this.overlay.classList.remove('open');
        }
    }

    /**
     * Fetch from API and render
     */
    async reloadNotifications() {
        try {
            const data = await window.apiService.fetchNotifications(this.currentFilter);
            this.renderNotificationsList(data.notifications || []);
            this.updateBadgeCounts(data.unread_count || 0, data.notifications || []);
        } catch (error) {
            console.error('Failed to reload notifications:', error);
        }
    }

    /**
     * Update header and alerts bar badges
     */
    updateBadgeCounts(unreadCount, list) {
        // Update header bell badge
        if (unreadCount > 0) {
            this.unreadBadge.textContent = unreadCount;
            this.unreadBadge.classList.remove('hidden');
            
            this.alertsBarCount.textContent = unreadCount;
            this.alertsBarCount.classList.remove('hidden');
            this.alertsBar.classList.add('alerts-bar-glow');
        } else {
            this.unreadBadge.classList.add('hidden');
            this.alertsBarCount.classList.add('hidden');
            this.alertsBar.classList.remove('alerts-bar-glow');
        }

        this.drawerUnreadCount.textContent = unreadCount;

        // Check for new critical/warning notifications to play chime
        let playStandardSound = false;
        
        list.forEach(notif => {
            if (!notif.is_read) {
                if (!this.seenNotifications.has(notif.id)) {
                    // Skip sounds for types that dashboard.js already plays sirens for (criminal, zone capacity)
                    if (notif.type !== 'criminal_detected' && notif.type !== 'zone_full' && notif.type !== 'zone_capacity') {
                        if (notif.severity === 'critical' || notif.severity === 'warning' || notif.type === 'face_scan_cleared') {
                            playStandardSound = true;
                        }
                    }
                    this.seenNotifications.add(notif.id);
                }
            }
        });

        if (playStandardSound) {
            this.playNotificationSound('standard');
        }
    }

    /**
     * Render the items in DOM
     */
    renderNotificationsList(notifications) {
        this.listContainer.innerHTML = '';

        if (notifications.length === 0) {
            this.listContainer.innerHTML = `
                <div class="empty-notifications">
                    <i class="fa-regular fa-bell-slash"></i>
                    <p>No notifications</p>
                </div>`;
            return;
        }

        notifications.forEach(notif => {
            const isCritical = notif.severity === 'critical';
            const actionText = isCritical ? 'Acknowledge' : 'Mark as Read';
            const severityClass = `severity-${notif.severity}`;
            const unreadClass = notif.is_read ? 'read' : 'unread';
            
            let icon = 'fa-circle-info';
            if (notif.severity === 'critical') icon = 'fa-circle-exclamation';
            else if (notif.severity === 'warning') icon = 'fa-triangle-exclamation';
            else if (notif.severity === 'success') icon = 'fa-circle-check';

            let evidenceImgHTML = '';
            if (notif.type === 'criminal_detected' && notif.suspect_image_url && notif.image_url) {
                evidenceImgHTML = `
                    <div class="notification-item-evidence-split" style="display: flex; gap: 8px; margin-top: 10px; border: 1px solid var(--border-color); border-radius: var(--border-radius-sm); overflow: hidden; height: 75px;">
                        <img src="${this.escapeHTML(notif.suspect_image_url)}?v=${Date.now()}" alt="Suspect Profile" style="width: 50%; height: 100%; object-fit: cover; border-right: 1px solid var(--border-color);" onerror="this.src='/images/detection-placeholder.jpg'">
                        <img src="${this.escapeHTML(notif.image_url)}?v=${Date.now()}" alt="CCTV Capture" style="width: 50%; height: 100%; object-fit: cover;" onerror="this.src='/images/detection-placeholder.jpg'">
                    </div>`;
            } else if (notif.image_url) {
                evidenceImgHTML = `
                    <div class="notification-item-evidence" style="margin-top: 10px;">
                        <img src="${this.escapeHTML(notif.image_url)}?v=${Date.now()}" alt="Snapshot evidence" class="notification-item-img" style="width: 100%; height: 100px; object-fit: cover; border-radius: var(--border-radius-sm);" onerror="this.src='/images/detection-placeholder.jpg'">
                    </div>`;
            }

            let actionButtonHTML = '';
            if (!notif.is_read) {
                actionButtonHTML = `
                    <div class="notification-item-actions">
                        <button type="button" class="btn-acknowledge" onclick="acknowledgeAlert(${notif.id})">
                            ${actionText}
                        </button>
                    </div>`;
            }

            let locationHTML = '';
            if (notif.location) {
                locationHTML = `
                    <div class="notification-item-location">
                        <i class="fa-solid fa-location-dot"></i> ${this.escapeHTML(notif.location)}
                    </div>`;
            }

            const item = document.createElement('div');
            item.className = `notification-item ${unreadClass} ${severityClass}`;
            item.setAttribute('data-id', notif.id);
            item.innerHTML = `
                <div class="notification-item-icon">
                    <i class="fa-solid ${icon}"></i>
                </div>
                <div class="notification-item-details">
                    <div class="notification-item-meta">
                        <span class="notification-item-title">${this.escapeHTML(notif.title)}</span>
                        <span class="notification-item-time">${this.formatRelativeTime(notif.created_at)}</span>
                    </div>
                    <p class="notification-item-msg">${this.escapeHTML(notif.message)}</p>
                    ${locationHTML}
                    ${evidenceImgHTML}
                    ${actionButtonHTML}
                </div>`;
            
            this.listContainer.appendChild(item);
        });
    }

    /**
     * Programmatic chime synthesizer using Web Audio API.
     * Generates a pleasant high-quality double chime.
     */
    /**
     * Programmatic chime synthesizer using Web Audio API.
     * Generates a pleasant high-quality double chime.
     */
    playNotificationSound(type = 'standard') {
        try {
            const defaultSound = type === 'danger' ? 'Danger-alert.mp3' : 'alert-notification.mp3';
            const soundUrl = window.alertSoundUrls && window.alertSoundUrls[type] 
                ? window.alertSoundUrls[type] 
                : `/audio/${defaultSound}`;

            console.log(`[Audio Debug] Attempting to play ${type} alert sound from URL:`, soundUrl);

            // Stop any currently playing audio of the same type to avoid overlapping chimes
            this.stopNotificationSound(type);

            const audio = new Audio(soundUrl);
            audio.volume = (type === 'danger' || type === 'red_zone') ? 0.70 : 0.55;
            
            if (!this.activeAudios) {
                this.activeAudios = {};
            }
            this.activeAudios[type] = audio;

            audio.play().then(() => {
                console.log(`[Audio Debug] Successfully played ${type} alert sound.`);
                this.audioNeedsPlayOnInteraction = false;
            }).catch(error => {
                console.warn(`[Audio Debug] Playback deferred by browser autoplay policies for ${type}:`, error);
                this.audioNeedsPlayOnInteraction = type;
            });
        } catch (error) {
            console.error("[Audio Debug] Exception occurred inside playNotificationSound:", error);
        }
    }

    /**
     * Stop and reset an actively playing notification sound.
     */
    stopNotificationSound(type) {
        try {
            if (this.activeAudios && this.activeAudios[type]) {
                console.log(`[Audio Debug] Stopping active sound: ${type}`);
                this.activeAudios[type].pause();
                this.activeAudios[type].currentTime = 0;
                delete this.activeAudios[type];
            }
        } catch (error) {
            console.error(`[Audio Debug] Failed to stop sound: ${type}`, error);
        }
    }

    /**
     * Format times relatively
     */
    formatRelativeTime(dateString) {
        const date = new Date(dateString);
        const now = new Date();
        const seconds = Math.floor((now - date) / 1000);
        
        if (seconds < 5) return 'Just now';
        if (seconds < 60) return `${seconds}s ago`;
        
        const minutes = Math.floor(seconds / 60);
        if (minutes < 60) return `${minutes}m ago`;
        
        const hours = Math.floor(minutes / 60);
        if (hours < 24) return `${hours}h ago`;
        
        const days = Math.floor(hours / 24);
        return `${days}d ago`;
    }

    /**
     * Escape strings for HTML output to prevent XSS injection
     */
    escapeHTML(str) {
        if (!str) return '';
        return str.toString()
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }
}

// Initialize on window
window.addEventListener('DOMContentLoaded', () => {
    window.notificationManager = new NotificationManager();
});

// Global functions for inline onclick triggers
window.toggleDrawer = (open) => {
    if (window.notificationManager) {
        window.notificationManager.toggleDrawer(open);
    }
};

window.acknowledgeAlert = async (id) => {
    try {
        await window.apiService.markAsRead(id);
        
        // Reload notifications list and main dashboard states
        if (window.notificationManager) {
            window.notificationManager.reloadNotifications();
        }
        if (window.dashboardApp) {
            window.dashboardApp.updateDashboardData();
        }
    } catch (e) {
        console.error('Failed to acknowledge alert:', e);
    }
};

window.markAllNotificationsAsRead = async () => {
    try {
        await window.apiService.markAllAsRead();
        if (window.notificationManager) {
            window.notificationManager.reloadNotifications();
        }
        if (window.dashboardApp) {
            window.dashboardApp.updateDashboardData();
        }
    } catch (e) {
        console.error('Failed to mark all as read:', e);
    }
};
