/**
 * Main Dashboard Controller
 */
class DashboardApp {
    constructor() {
        this.refreshInterval = 2000; // default 2 seconds
        this.pollingTimer = null;
        this.clockTimer = null;
        this.isTabActive = true;
        this.currentDay = 'day1';
        this.historicalMockTrends = {};
        
        // Cache DOM elements
        this.dateEl = document.getElementById('current-date');
        this.timeEl = document.getElementById('current-time');
        this.liveBadgeContainer = document.getElementById('live-badge-container');
        
        // Summary DOMs
        this.visitsVal = document.querySelector('#visits-card .summary-card-value') || document.getElementById('visits-val');
        this.presentVal = document.querySelector('#present-card .summary-card-value') || document.getElementById('present-val');
        this.entriesVal = document.querySelector('#entries-card .summary-card-value') || document.getElementById('entries-val');
        this.exitsVal = document.querySelector('#exits-card .summary-card-value') || document.getElementById('exits-val');
        this.avgEntryRateVal = document.getElementById('avg-entry-rate-val');
        this.avgExitRateVal = document.getElementById('avg-exit-rate-val');

        // Criminal Panel DOMs
        this.criminalPanel = document.getElementById('criminal-panel');
        this.criminalStatusBadge = document.getElementById('criminal-status-badge');
        this.criminalTimeBadge = document.getElementById('criminal-time');
        this.criminalTimeText = document.getElementById('criminal-time-text');
        this.criminalImagesWrapper = document.getElementById('criminal-images-wrapper');
        this.criminalSuspectImage = document.getElementById('criminal-suspect-image');
        this.criminalCapturedImage = document.getElementById('criminal-captured-image');
        this.criminalScanOverlay = document.getElementById('criminal-scan-overlay');
        this.criminalPrevBtn = document.getElementById('criminal-prev-btn');
        this.criminalNextBtn = document.getElementById('criminal-next-btn');
        this.criminalSkeleton = document.getElementById('criminal-skeleton');
        this.criminalEmpty = document.getElementById('criminal-empty');
        this.criminalAccuracy = document.getElementById('criminal-accuracy');
        this.criminalLocation = document.getElementById('criminal-location');
        this.criminalActionContainer = document.getElementById('criminal-action-container');

        // State variables for Criminal Panel
        this.criminalRecords = [];
        this.activeDetections = [];
        this.currentRecordIndex = 0;
        this.currentDetectionIndex = 0;
        this.criminalRotationTimer = null;
        this.isCriminalCardHovered = false;
        this.isAcknowledgeProcessing = false;
        this.autoAcknowledgedIds = new Set();
        this.zoneCharts = {};
        this.lastZoneStates = {};

        this.init();
    }

    init() {
        // Start date and time ticker
        this.startClock();

        // Perform initial fetch
        this.updateDashboardData();

        // Start polling loop
        this.startPolling();

        // Initialize Chart.js sparklines for each zone card
        this.initZoneCharts();

        // Handle page visibility change (pause polling on background tab)
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                this.isTabActive = false;
                this.stopPolling();
                console.log('Tab hidden: Polling paused.');
            } else {
                this.isTabActive = true;
                this.startPolling();
                this.updateDashboardData();
                console.log('Tab active: Polling resumed.');
            }
        });

        // Day select chart switch event
        const daySelect = document.getElementById('day-select');
        if (daySelect) {
            daySelect.addEventListener('change', (e) => {
                this.currentDay = e.target.value;
                this.refreshTrendChart();
            });
        }

        // Listen for API Offline state modifications
        window.apiService.onStateChange((isOffline, reason) => {
            this.handleSystemOfflineState(isOffline, reason);
        });

        // Initialize Criminal Card variables & fetch API records
        this.loadCriminalData();

        // 1. Hover Listener (Pause rotation on hover)
        if (this.criminalPanel) {
            this.criminalPanel.addEventListener('mouseenter', () => {
                this.isCriminalCardHovered = true;
            });
            this.criminalPanel.addEventListener('mouseleave', () => {
                this.isCriminalCardHovered = false;
            });

            // Make card focusable and trigger arrow actions with Left/Right keys
            this.criminalPanel.setAttribute('tabindex', '0');
            this.criminalPanel.addEventListener('keydown', (e) => {
                if (e.key === 'ArrowLeft' && this.activeDetections.length > 1) {
                    e.preventDefault();
                    this.navigateCriminalDetection('prev');
                } else if (e.key === 'ArrowRight' && this.activeDetections.length > 1) {
                    e.preventDefault();
                    this.navigateCriminalDetection('next');
                }
            });
        }

        // 2. Click Listeners on circular arrow buttons
        if (this.criminalPrevBtn) {
            this.criminalPrevBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.navigateCriminalDetection('prev');
            });
        }
        if (this.criminalNextBtn) {
            this.criminalNextBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.navigateCriminalDetection('next');
            });
        }
    }

    /**
     * Start the clock ticking every second.
     */
    startClock() {
        const updateTime = () => {
            const now = new Date();
            
            // Format: 03 Aug 2026
            const day = String(now.getDate()).padStart(2, '0');
            const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
            const month = months[now.getMonth()];
            const year = now.getFullYear();
            
            // Format: 06:30:00 PM
            let hours = now.getHours();
            const ampm = hours >= 12 ? 'PM' : 'AM';
            hours = hours % 12;
            hours = hours ? hours : 12; // 0 should be 12
            const minutes = String(now.getMinutes()).padStart(2, '0');
            const seconds = String(now.getSeconds()).padStart(2, '0');
            const formattedHours = String(hours).padStart(2, '0');

            if (this.dateEl) this.dateEl.textContent = `${day} ${month} ${year}`;
            if (this.timeEl) this.timeEl.textContent = `${formattedHours}:${minutes}:${seconds} ${ampm}`;
        };

        updateTime();
        this.clockTimer = setInterval(updateTime, 1000);
    }

    /**
     * Start the interval polling loop.
     */
    startPolling() {
        this.stopPolling();
        this.pollingTimer = setInterval(() => {
            if (this.isTabActive) {
                this.updateDashboardData();
            }
        }, this.refreshInterval);
    }

    /**
     * Stop the interval polling loop.
     */
    stopPolling() {
        if (this.pollingTimer) {
            clearInterval(this.pollingTimer);
            this.pollingTimer = null;
        }
    }

    /**
     * Perform GET API call and update UI panels.
     */
    async updateDashboardData() {
        try {
            const data = await window.apiService.fetchDashboardData();
            
            // 1. Update summary statistics
            this.updateSummaryCards(data.summary || {});

            // 2. Update Zone heatmap cards
            this.updateZones(data.zones || []);

            // 3. Update Gates Table
            this.updateGatesTable(data.gates || []);

            // 4. Update Queues Table
            this.updateQueuesTable(data.queues || []);

            // 5. Update active detections list
            try {
                const detectionsResponse = await window.apiService.fetchCriminalDetections();
                if (detectionsResponse.success) {
                    const oldDetections = this.activeDetections;
                    this.activeDetections = detectionsResponse.detections || [];
                    
                    const hasNewDetection = this.activeDetections.length > 0 && 
                        (!oldDetections || oldDetections.length === 0 || this.activeDetections[0].id !== oldDetections[0].id);

                    if (hasNewDetection || this.activeDetections.length !== (oldDetections ? oldDetections.length : 0)) {
                        this.currentDetectionIndex = 0;
                        this.updateCriminalDisplay();
                        this.startCriminalRotation();
                    }
                }
            } catch (err) {
                console.error("Failed to poll criminal detections:", err);
            }

            // 6. Cache and update Hourly trend graph dataset
            this.hourlyTrendData = data.hourly_trend || [];
            this.refreshTrendChart();

            // 6b. Update CCTV Cameras Grid
            if (data.cameras) {
                this.updateCameras(data.cameras);
            }

            // 7. Refresh notification list in background if drawer is open, or update counts
            if (window.notificationManager) {
                if (window.notificationManager.isOpen) {
                    window.notificationManager.reloadNotifications();
                } else {
                    // Just reload notifications to get badge counts
                    const notifData = await window.apiService.fetchNotifications();
                    window.notificationManager.updateBadgeCounts(notifData.unread_count || 0, notifData.notifications || []);
                }
            }

        } catch (error) {
            console.error('Failed to update dashboard data:', error);
        }
    }

    /**
     * Update Summary Statistics with smooth counter increment animations.
     */
    updateSummaryCards(summary) {
        const visits = summary.total_visits || 0;
        const present = summary.people_present || 0;
        const entries = summary.total_entries || 0;
        const exits = summary.total_exits || 0;

        this.animateValue(this.visitsVal, visits);
        this.animateValue(this.presentVal, present);
        this.animateValue(this.entriesVal, entries);
        this.animateValue(this.exitsVal, exits);

        // Calculate dynamic hourly rates based on total entries/exits divided by hours since 6 AM (default to 8 hours for stability)
        const currentHour = new Date().getHours();
        const hoursElapsed = currentHour >= 6 ? Math.max(1, currentHour - 6) : 8;
        const avgEntryRate = Math.round(entries / hoursElapsed);
        const avgExitRate = Math.round(exits / hoursElapsed);

        if (this.avgEntryRateVal) {
            this.avgEntryRateVal.textContent = `${avgEntryRate} / hour`;
        }
        if (this.avgExitRateVal) {
            this.avgExitRateVal.textContent = `${avgExitRate} / hour`;
        }
    }

    /**
     * Smooth value counting animation.
     */
    animateValue(element, endVal) {
        if (!element) return;
        
        const currentVal = parseInt(element.getAttribute('data-target-value') || '0', 10);
        if (currentVal === endVal) {
            element.textContent = endVal.toLocaleString();
            return;
        }

        element.setAttribute('data-target-value', endVal);

        const duration = 800; // ms
        const startTimestamp = performance.now();
        
        const step = (timestamp) => {
            const progress = Math.min((timestamp - startTimestamp) / duration, 1);
            const value = Math.floor(progress * (endVal - currentVal) + currentVal);
            element.textContent = value.toLocaleString();
            
            if (progress < 1) {
                window.requestAnimationFrame(step);
            } else {
                element.textContent = endVal.toLocaleString();
            }
        };
        
        window.requestAnimationFrame(step);
    }

    /**
     * Update Zone heatmap cards.
     */
    updateZones(zones) {
        zones.forEach(zone => {
            const card = document.getElementById(`card-${zone.id}`);
            if (!card) return;

            // Reset classes
            const isWave = card.classList.contains('waves-type');
            card.className = isWave ? 'zone-card waves-type zone-card-horizontal' : 'zone-card';
            
            let labelText = 'Normal';
            const occupancy = zone.occupancy_percentage;

            if (occupancy >= 100) {
                card.classList.add('zone-red', 'pulse-critical');
                labelText = 'Zone Full';
            } else if (occupancy >= 90) {
                card.classList.add('zone-red', 'pulse-warning');
                labelText = 'Near Capacity';
            } else if (occupancy >= 80) {
                card.classList.add('zone-orange');
                labelText = 'Near Capacity';
            } else if (occupancy >= 60) {
                card.classList.add('zone-yellow');
                labelText = 'Warning';
            } else {
                card.classList.add('zone-green');
            }

            // Update Label text
            const labelEl = card.querySelector('.zone-card-label');
            if (labelEl) labelEl.textContent = labelText;

            // Update occupancy counts
            const countEl = card.querySelector('.zone-card-count');
            if (countEl) countEl.textContent = zone.current_count.toLocaleString();

            // Update percentage text
            const percentEl = card.querySelector('.zone-percentage');
            if (percentEl) percentEl.textContent = `${occupancy}%`;

            // Update capacity subtext dynamically to match API capacity
            const capacityEl = card.querySelector('.zone-capacity-sub span') || card.querySelector('.zone-capacity span');
            if (capacityEl) capacityEl.textContent = zone.capacity.toLocaleString();

            // Update SVG sparkline if it exists
            const sparklineContainer = card.querySelector('.sparkline-container');
            if (sparklineContainer) {
                let sparkStatus = 'green';
                if (occupancy >= 90) {
                    sparkStatus = 'red';
                } else if (occupancy >= 80) {
                    sparkStatus = 'orange';
                } else if (occupancy >= 60) {
                    sparkStatus = 'yellow';
                }
                this.updateZoneSparkline(zone.id, zone.current_count, zone.capacity, card, sparkStatus);
            }

            // Sound Alarm Thresholds logic
            const currentCount = zone.current_count;
            const lastState = this.lastZoneStates[zone.id] || { breached300: false, breached500: false };
            
            const breached500 = currentCount >= 500;
            const breached300 = currentCount >= 300;

            if (breached500 && !lastState.breached500) {
                console.log(`[Audio Alert] Zone ${zone.id} breached 500 critical threshold (count: ${currentCount}). Playing red zone alert.`);
                if (window.notificationManager) {
                    window.notificationManager.playNotificationSound('red_zone');
                }
            } else if (breached300 && !lastState.breached300 && !breached500) {
                console.log(`[Audio Alert] Zone ${zone.id} breached 300 warning threshold (count: ${currentCount}). Playing orange alert.`);
                if (window.notificationManager) {
                    window.notificationManager.playNotificationSound('orange');
                }
            }

            // Update state
            this.lastZoneStates[zone.id] = { breached300, breached500 };

            // Also update 2D floor map block if it exists on the Zones page
            const mapBlock = document.getElementById(`map-block-${zone.id}`);
            if (mapBlock) {
                let mapStatusClass = 'zone-normal';
                if (occupancy >= 90) {
                    mapStatusClass = 'zone-critical';
                } else if (occupancy >= 60) {
                    mapStatusClass = 'zone-warning';
                }
                
                mapBlock.className = `map-zone-block ${mapStatusClass}`;
                
                const mapCount = mapBlock.querySelector('.map-zone-count');
                const mapPct = mapBlock.querySelector('.map-zone-percentage');
                
                if (mapCount) mapCount.textContent = zone.current_count.toLocaleString();
                if (mapPct) mapPct.textContent = `${occupancy}% Occupancy`;
            }
        });

        // Stop sound alerts dynamically when counts drop below thresholds
        let anyZoneCritical = false;
        let anyZoneWarning = false;
        zones.forEach(z => {
            if (z.current_count >= 500) {
                anyZoneCritical = true;
            }
            if (z.current_count >= 300 && z.current_count < 500) {
                anyZoneWarning = true;
            }
        });

        if (window.notificationManager) {
            if (!anyZoneCritical) {
                window.notificationManager.stopNotificationSound('red_zone');
            }
            if (!anyZoneWarning) {
                window.notificationManager.stopNotificationSound('orange');
            }
        }
    }

    /**
     * Update CCTV Cameras Grid elements dynamically.
     */
    /**
     * Update CCTV Cameras Grid elements dynamically.
     */
    updateCameras(cameras) {
        // Stats and colors removed as per user request
    }

    /**
     * Update sparkline line graph inside horizontal zone cards.
     */
    updateZoneSparkline(zoneId, currentCount, capacity, card, statusClass) {
        if (!this.zoneHistory) {
            this.zoneHistory = {};
        }
        
        if (!this.zoneHistory[zoneId]) {
            // Generate realistic initial random historical counts for sparkline
            const history = [];
            const steps = 18;
            for (let i = 0; i < steps; i++) {
                // Generate a wavy history trend fluctuating around 40-95%
                const phase = (i / (steps - 1)) * Math.PI * 1.8;
                const ratio = 0.5 + Math.sin(phase) * 0.2 + (Math.random() - 0.5) * 0.12;
                const val = Math.round(capacity * Math.min(0.98, Math.max(0.15, ratio)));
                history.push(val);
            }
            // Make sure the last value is exactly the current count
            history[history.length - 1] = currentCount;
            this.zoneHistory[zoneId] = history;
        } else {
            // Push current count and shift history
            this.zoneHistory[zoneId].push(currentCount);
            if (this.zoneHistory[zoneId].length > 18) {
                this.zoneHistory[zoneId].shift();
            }
        }
        
        const history = this.zoneHistory[zoneId];
        const svg = card.querySelector('.sparkline-svg');
        if (!svg) return;
        
        // Dynamically adjust Y ticks on the left side based on capacity
        const yTicks = card.querySelector('.sparkline-y-ticks');
        if (yTicks) {
            yTicks.innerHTML = `
                <span class="tick-label y-max">${Math.round(capacity * 0.9).toLocaleString()}</span>
                <span class="tick-label y-mid-high">${Math.round(capacity * 0.68).toLocaleString()}</span>
                <span class="tick-label y-mid">${Math.round(capacity * 0.45).toLocaleString()}</span>
                <span class="tick-label y-mid-low">${Math.round(capacity * 0.22).toLocaleString()}</span>
                <span class="tick-label y-min">0</span>
            `;
        }
        
        // Render spline path in SVG
        const width = 400;
        const height = 100;
        const padding = 5;
        const chartHeight = height - padding * 2;
        
        // Find max in history to scale
        const maxVal = capacity; 
        
        const points = history.map((val, index) => {
            const x = (index / (history.length - 1)) * width;
            const y = height - padding - (val / maxVal) * chartHeight;
            return { x, y };
        });
        
        // Build spline cubic curve path
        let pathD = '';
        if (points.length > 0) {
            pathD = `M ${points[0].x.toFixed(1)},${points[0].y.toFixed(1)}`;
            for (let i = 0; i < points.length - 1; i++) {
                const p0 = points[i];
                const p1 = points[i + 1];
                const cpX1 = p0.x + (p1.x - p0.x) / 2;
                const cpY1 = p0.y;
                const cpX2 = p0.x + (p1.x - p0.x) / 2;
                const cpY2 = p1.y;
                pathD += ` C ${cpX1.toFixed(1)},${cpY1.toFixed(1)} ${cpX2.toFixed(1)},${cpY2.toFixed(1)} ${p1.x.toFixed(1)},${p1.y.toFixed(1)}`;
            }
        }
        
        // Set paths
        const linePath = svg.querySelector('.sparkline-line-path');
        if (linePath) {
            linePath.setAttribute('d', pathD);
            linePath.className.baseVal = `sparkline-line-path stroke-${statusClass}`;
        }
        
        const areaPath = svg.querySelector('.sparkline-area-path');
        if (areaPath) {
            let areaD = pathD;
            if (points.length > 0) {
                areaD += ` L ${points[points.length - 1].x.toFixed(1)},${height} L ${points[0].x.toFixed(1)},${height} Z`;
            }
            areaPath.setAttribute('d', areaD);
            areaPath.setAttribute('fill', `url(#area-grad-${statusClass})`);
        }
        
        // Set dots
        const lastPoint = points[points.length - 1];
        const lastDot = svg.querySelector('.sparkline-last-dot');
        const lastDotGlow = svg.querySelector('.sparkline-last-dot-glow');
        
        if (lastDot && lastPoint) {
            lastDot.setAttribute('cx', lastPoint.x.toFixed(1));
            lastDot.setAttribute('cy', lastPoint.y.toFixed(1));
            lastDot.className.baseVal = `sparkline-last-dot fill-${statusClass}`;
        }
        if (lastDotGlow && lastPoint) {
            lastDotGlow.setAttribute('cx', lastPoint.x.toFixed(1));
            lastDotGlow.setAttribute('cy', lastPoint.y.toFixed(1));
            lastDotGlow.className.baseVal = `sparkline-last-dot-glow fill-${statusClass}`;
        }
    }

    /**
     * Update Gates Entry/Exit Table dynamically.
     */
    updateGatesTable(gates) {
        const tbody = document.querySelector('#gates-table tbody');
        if (!tbody) return;

        tbody.innerHTML = '';

        gates.forEach(gate => {
            const tr = document.createElement('tr');
            
            // Reusable status dot rendering
            const statusLower = gate.status.toLowerCase();
            const dotClass = statusLower === 'normal' ? 'dot-green' : (statusLower === 'warning' ? 'dot-yellow' : 'dot-red');
            const labelText = statusLower === 'normal' ? 'Normal' : (statusLower === 'warning' ? 'Warning' : 'Blocked');
            
            tr.innerHTML = `
                <td>${this.escapeHTML(gate.gate_number)}</td>
                <td class="font-numeric">${gate.entries.toLocaleString()}</td>
                <td class="font-numeric">${gate.exits.toLocaleString()}</td>
                <td>
                    <div class="status-indicator-wrapper" title="${labelText}">
                        <span class="status-dot ${dotClass}" aria-hidden="true"></span>
                        <span class="status-label">${labelText}</span>
                    </div>
                </td>
            `;
            tbody.appendChild(tr);
        });
    }

    /**
     * Update Queue Movement Table.
     */
    updateQueuesTable(queues) {
        const tbody = document.querySelector('#queues-table tbody');
        if (!tbody) return;

        tbody.innerHTML = '';

        queues.forEach(queue => {
            const tr = document.createElement('tr');
            const mLower = queue.movement.toLowerCase();
            
            const dotClass = mLower === 'moving' ? 'dot-green' : (mLower === 'slow' ? 'dot-yellow' : 'dot-red');
            const labelText = mLower === 'moving' ? 'Moving' : (mLower === 'slow' ? 'Slow' : 'Stopped');
            
            tr.innerHTML = `
                <td>${this.escapeHTML(queue.queue_number)}</td>
                <td class="font-numeric">${queue.wait_minutes} mins</td>
                <td>
                    <div class="status-indicator-wrapper" title="${labelText}">
                        <span class="status-dot ${dotClass}" aria-hidden="true"></span>
                        <span class="status-label">${labelText}</span>
                    </div>
                </td>
            `;
            tbody.appendChild(tr);
        });
    }

    /**
     * Fetch criminal records and active detections from the database APIs.
     */
    async loadCriminalData() {
        this.showCriminalSkeleton(true);
        this.showCriminalEmptyState(false);
        try {
            const [recordsResponse, detectionsResponse] = await Promise.all([
                window.apiService.fetchCriminalRecords(),
                window.apiService.fetchCriminalDetections()
            ]);

            if (recordsResponse.success) {
                this.criminalRecords = recordsResponse.records || [];
            }

            if (detectionsResponse.success) {
                this.activeDetections = detectionsResponse.detections || [];
            }

            this.showCriminalSkeleton(false);

            if (this.criminalRecords.length === 0 && this.activeDetections.length === 0) {
                this.showCriminalEmptyState(true);
                return;
            }

            this.currentRecordIndex = 0;
            this.currentDetectionIndex = 0;

            this.updateCriminalDisplay();
            this.startCriminalRotation();

        } catch (error) {
            console.error("Failed to load criminal card data:", error);
            this.showCriminalSkeleton(false);
            this.showCriminalEmptyState(true);
        }
    }

    /**
     * Show or hide loading skeleton UI.
     */
    showCriminalSkeleton(show) {
        if (!this.criminalSkeleton) return;
        if (show) {
            this.criminalSkeleton.classList.remove('hidden');
        } else {
            this.criminalSkeleton.classList.add('hidden');
        }
    }

    /**
     * Show or hide empty state fallback placeholder.
     */
    showCriminalEmptyState(show) {
        if (!this.criminalEmpty) return;
        if (show) {
            this.criminalEmpty.classList.remove('hidden');
            if (this.criminalImagesWrapper) this.criminalImagesWrapper.classList.add('hidden');
            if (this.criminalActionContainer) this.criminalActionContainer.classList.add('hidden');
        } else {
            this.criminalEmpty.classList.add('hidden');
            if (this.criminalImagesWrapper) this.criminalImagesWrapper.classList.remove('hidden');
        }
    }

    /**
     * Start the 5-second automatic carousel ticker.
     */
    startCriminalRotation() {
        if (this.criminalRotationTimer) {
            clearInterval(this.criminalRotationTimer);
        }

        this.criminalRotationTimer = setInterval(() => {
            // Pause rotation on mouse hover, tab inactive, or button processing
            if (this.isCriminalCardHovered || !this.isTabActive || this.isAcknowledgeProcessing) {
                return;
            }

            const unacknowledgedDetections = this.activeDetections.filter(d => d.status === 'detected');
            if (unacknowledgedDetections.length > 0) {
                this.currentDetectionIndex = (this.currentDetectionIndex + 1) % unacknowledgedDetections.length;
            } else if (this.criminalRecords.length > 0) {
                this.currentRecordIndex = (this.currentRecordIndex + 1) % this.criminalRecords.length;
            }

            this.updateCriminalDisplay();
        }, 5000);
    }

    /**
     * Render the active suspect profile / CCTV frame details inside the card.
     */
    updateCriminalDisplay() {
        const unacknowledgedDetections = this.activeDetections.filter(d => d.status === 'detected');

        // Mode A: Active live (unacknowledged) detections
        if (unacknowledgedDetections && unacknowledgedDetections.length > 0) {
            this.showCriminalEmptyState(false);
            if (this.criminalScanOverlay) this.criminalScanOverlay.classList.add('hidden');
            const det = unacknowledgedDetections[this.currentDetectionIndex % unacknowledgedDetections.length];
            if (!det) return;

            // Update Badge Title
            if (this.criminalStatusBadge) {
                this.criminalStatusBadge.className = 'criminal-badge-alert';
                this.criminalStatusBadge.textContent = 'Criminal Detected';
            }

            // Update Captured Clock Time
            if (this.criminalTimeBadge && this.criminalTimeText && det.captured_at) {
                const date = new Date(det.captured_at);
                let hours = date.getHours();
                const ampm = hours >= 12 ? 'PM' : 'AM';
                hours = hours % 12;
                hours = hours ? hours : 12;
                const minutes = String(date.getMinutes()).padStart(2, '0');
                this.criminalTimeText.textContent = `${String(hours).padStart(2, '0')}:${minutes} ${ampm}`;
                this.criminalTimeBadge.classList.remove('hidden');
            }

            // Red border outline
            if (this.criminalImagesWrapper) {
                this.criminalImagesWrapper.classList.add('active-alert');
            }

            // Database Profile Photo
            if (this.criminalSuspectImage) {
                const imgUrl = det.criminal ? det.criminal.profile_image : '/images/detection-placeholder.jpg';
                this.criminalSuspectImage.src = imgUrl.includes('?') ? imgUrl : `${imgUrl}?v=${Date.now()}`;
                this.criminalSuspectImage.classList.remove('hidden');
            }

            // Live Camera Photo
            if (this.criminalCapturedImage) {
                const imgUrl = det.captured_image || '/images/detection-placeholder.jpg';
                this.criminalCapturedImage.src = imgUrl.includes('?') ? imgUrl : `${imgUrl}?v=${Date.now()}`;
            }

            // Circular Arrows (only show if unacknowledged count > 1)
            if (unacknowledgedDetections.length > 1) {
                if (this.criminalPrevBtn) this.criminalPrevBtn.classList.remove('hidden');
                if (this.criminalNextBtn) this.criminalNextBtn.classList.remove('hidden');
            } else {
                if (this.criminalPrevBtn) this.criminalPrevBtn.classList.add('hidden');
                if (this.criminalNextBtn) this.criminalNextBtn.classList.add('hidden');
            }

            // Detail fields
            if (this.criminalAccuracy) this.criminalAccuracy.textContent = `${det.accuracy}%`;
            if (this.criminalLocation) this.criminalLocation.textContent = det.zone_name || '--';

            // Play danger sound and auto-acknowledge after 6 seconds (no manual action needed)
            if (det.status === 'detected' && !this.autoAcknowledgedIds.has(det.id)) {
                this.autoAcknowledgedIds.add(det.id);
                if (window.notificationManager) {
                    window.notificationManager.playNotificationSound('danger');
                }
                
                // Show slide-in toast notification
                const name = det.criminal ? det.criminal.name : 'Ramesh Kumar';
                const code = det.criminal ? det.criminal.criminal_code : 'CRM-001';
                this.showToastNotification(
                    'CRITICAL ALERT',
                    `WATCHLIST MATCH FOUND: ${name} (${code}) detected at ${det.zone_name || 'Zone B'}!`
                );

                // Auto-clear after 6 seconds
                setTimeout(async () => {
                    try {
                        const response = await window.apiService.acknowledgeCriminalDetection(det.id);
                        if (response.success) {
                            this.activeDetections = this.activeDetections.map(d => {
                                if (d.id === response.detection_id) {
                                    d.status = 'acknowledged';
                                }
                                return d;
                            });
                            this.updateCriminalDisplay();
                        }
                    } catch (e) {
                        console.error("Auto-acknowledgement failed:", e);
                    }
                }, 6000);
            }

            // Hide action container (no manual button needed)
            if (this.criminalActionContainer) {
                this.criminalActionContainer.innerHTML = '';
                this.criminalActionContainer.classList.add('hidden');
            }
        }
        // Mode B: Fallback reference rotation through the database suspects list
        else if (this.criminalRecords && this.criminalRecords.length > 0) {
            this.showCriminalEmptyState(false);
            if (this.criminalScanOverlay) this.criminalScanOverlay.classList.remove('hidden');
            const rec = this.criminalRecords[this.currentRecordIndex % this.criminalRecords.length];
            if (!rec) return;

            // Update Badge Title
            if (this.criminalStatusBadge) {
                this.criminalStatusBadge.className = 'criminal-badge-normal';
                this.criminalStatusBadge.textContent = `Watchlist Profile - ${rec.criminal_code}`;
            }

            // Hide clock
            if (this.criminalTimeBadge) {
                this.criminalTimeBadge.classList.add('hidden');
            }

            // Remove red alert outlines
            if (this.criminalImagesWrapper) {
                this.criminalImagesWrapper.classList.remove('active-alert');
            }

            // Database Profile Photo
            if (this.criminalSuspectImage) {
                const imgUrl = rec.profile_image || '/images/detection-placeholder.jpg';
                this.criminalSuspectImage.src = imgUrl.includes('?') ? imgUrl : `${imgUrl}?v=${Date.now()}`;
                this.criminalSuspectImage.classList.remove('hidden');
            }

            // Live camera Lobby Placeholder or matching mock DET image
            if (this.criminalCapturedImage) {
                let imgUrl = '/images/detection-placeholder.jpg';
                if (rec.criminal_code === 'CRM-001') {
                    imgUrl = '/storage/detections/DET-mock-1.jpg';
                } else if (rec.criminal_code === 'CRM-002') {
                    imgUrl = '/storage/detections/DET-mock-2.jpg';
                } else if (rec.criminal_code === 'CRM-003') {
                    imgUrl = '/storage/detections/DET-mock-3.jpg';
                } else if (rec.criminal_code === 'CRM-004') {
                    imgUrl = '/storage/detections/DET-mock-2.jpg';
                } else if (rec.criminal_code === 'CRM-005') {
                    imgUrl = '/storage/detections/DET-mock-1.jpg';
                } else if (rec.criminal_code === 'CRM-006') {
                    imgUrl = '/storage/detections/DET-mock-3.jpg';
                } else if (rec.criminal_code === 'CRM-007') {
                    imgUrl = '/storage/detections/DET-mock-2.jpg';
                } else if (rec.criminal_code === 'CRM-008') {
                    imgUrl = '/storage/detections/DET-mock-1.jpg';
                } else if (rec.criminal_code === 'CRM-009') {
                    imgUrl = '/storage/detections/DET-mock-3.jpg';
                } else if (rec.criminal_code === 'CRM-010') {
                    imgUrl = '/storage/detections/DET-mock-2.jpg';
                }
                this.criminalCapturedImage.src = imgUrl.includes('?') ? imgUrl : `${imgUrl}?v=${Date.now()}`;
            }

            // Show manual circular buttons if there are multiple database suspects
            if (this.criminalRecords && this.criminalRecords.length > 1) {
                if (this.criminalPrevBtn) this.criminalPrevBtn.classList.remove('hidden');
                if (this.criminalNextBtn) this.criminalNextBtn.classList.remove('hidden');
            } else {
                if (this.criminalPrevBtn) this.criminalPrevBtn.classList.add('hidden');
                if (this.criminalNextBtn) this.criminalNextBtn.classList.add('hidden');
            }

            // Reset accuracy and location values with stable mock data based on record ID
            if (this.criminalAccuracy) {
                const mockAccuracy = 90 + (rec.id % 9);
                this.criminalAccuracy.textContent = `${mockAccuracy}%`;
            }
            if (this.criminalLocation) {
                const locations = ['CAM-01', 'CAM-02', 'CAM-03', 'CAM-04', 'CAM-05', 'CAM-06', 'CAM-07', 'CAM-08'];
                const mockLoc = locations[rec.id % locations.length];
                this.criminalLocation.textContent = mockLoc;
            }

            // Hide action button
            if (this.criminalActionContainer) {
                this.criminalActionContainer.innerHTML = '';
                this.criminalActionContainer.classList.add('hidden');
            }
        } else {
            this.showCriminalEmptyState(true);
        }
    }

    /**
     * Cycle manually with Left / Right buttons.
     */
    navigateCriminalDetection(direction) {
        const unacknowledgedDetections = this.activeDetections.filter(d => d.status === 'detected');

        // Mode A: Navigate active live (unacknowledged) detections
        if (unacknowledgedDetections && unacknowledgedDetections.length > 0) {
            if (unacknowledgedDetections.length <= 1) return;

            if (this.criminalPrevBtn) this.criminalPrevBtn.classList.add('disabled');
            if (this.criminalNextBtn) this.criminalNextBtn.classList.add('disabled');

            if (direction === 'next') {
                this.currentDetectionIndex = (this.currentDetectionIndex + 1) % unacknowledgedDetections.length;
            } else {
                this.currentDetectionIndex = (this.currentDetectionIndex - 1 + unacknowledgedDetections.length) % unacknowledgedDetections.length;
            }
        }
        // Mode B: Navigate fallback watchlist records
        else if (this.criminalRecords && this.criminalRecords.length > 0) {
            if (this.criminalRecords.length <= 1) return;

            if (this.criminalPrevBtn) this.criminalPrevBtn.classList.add('disabled');
            if (this.criminalNextBtn) this.criminalNextBtn.classList.add('disabled');

            if (direction === 'next') {
                this.currentRecordIndex = (this.currentRecordIndex + 1) % this.criminalRecords.length;
            } else {
                this.currentRecordIndex = (this.currentRecordIndex - 1 + this.criminalRecords.length) % this.criminalRecords.length;
            }
        } else {
            return;
        }

        // Apply smooth transition opacity fade animation
        if (this.criminalImagesWrapper) {
            this.criminalImagesWrapper.style.opacity = '0.3';
            setTimeout(() => {
                this.updateCriminalDisplay();
                this.criminalImagesWrapper.style.opacity = '1';

                // Release debounce after transition finishes (300ms)
                if (this.criminalPrevBtn) this.criminalPrevBtn.classList.remove('disabled');
                if (this.criminalNextBtn) this.criminalNextBtn.classList.remove('disabled');
            }, 300);
        } else {
            this.updateCriminalDisplay();
            if (this.criminalPrevBtn) this.criminalPrevBtn.classList.remove('disabled');
            if (this.criminalNextBtn) this.criminalNextBtn.classList.remove('disabled');
        }

        // Reset automatic clock rotation on manual arrow click
        this.startCriminalRotation();
    }

    /**
     * Triggers PATCH to acknowledge a specific detection.
     */
    async acknowledgeDetection(detectionId) {
        if (this.isAcknowledgeProcessing) return;

        this.isAcknowledgeProcessing = true;

        const btn = document.getElementById('btn-acknowledge-det');
        if (btn) {
            btn.disabled = true;
            btn.textContent = 'Acknowledging...';
        }

        try {
            const response = await window.apiService.acknowledgeCriminalDetection(detectionId);

            if (response.success) {
                // Slide-in toast notification
                this.showToastNotification('Success', 'Detection has been successfully acknowledged.');

                // Update local status in array instead of removing it
                this.activeDetections = this.activeDetections.map(d => {
                    if (d.id === response.detection_id) {
                        d.status = 'acknowledged';
                    }
                    return d;
                });

                // Update UI state
                this.updateCriminalDisplay();

                // Instantly play the critical danger alarm chime
                if (window.notificationManager) {
                    window.notificationManager.playNotificationSound('danger');
                    window.notificationManager.reloadNotifications();
                }
            } else {
                this.showToastNotification('Error', response.message || 'Failed to acknowledge.');
                if (btn) {
                    btn.disabled = false;
                    btn.textContent = 'Acknowledge Detection';
                }
            }
        } catch (error) {
            console.error('Failed to acknowledge detection:', error);
            this.showToastNotification('Error', 'Connection error occurred during acknowledgment.');
            if (btn) {
                btn.disabled = false;
                btn.textContent = 'Acknowledge Detection';
            }
        } finally {
            this.isAcknowledgeProcessing = false;
            this.startCriminalRotation();
        }
    }

    /**
     * Inject dynamic sliding toast alerts.
     */
    showToastNotification(type, message) {
        const container = document.getElementById('toast-container') || (() => {
            const el = document.createElement('div');
            el.id = 'toast-container';
            document.body.appendChild(el);
            return el;
        })();

        const toast = document.createElement('div');
        toast.className = `toast-notif ${type.toLowerCase()}`;

        const iconClass = type.toLowerCase() === 'success' ? 'fa-solid fa-circle-check' : 'fa-solid fa-circle-exclamation';

        toast.innerHTML = `
            <i class="${iconClass}"></i>
            <div class="toast-content">
                <strong>${type}</strong>
                <span>${message}</span>
            </div>
        `;

        container.appendChild(toast);

        // Slide in
        setTimeout(() => toast.classList.add('show'), 20);

        // Slide out and remove after 20 seconds
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 400);
        }, 20000);
    }

    /**
     * Refreshes the Hourly Trend Chart based on day selection.
     */
    refreshTrendChart() {
        if (!window.crowdChart) return;

        let labels = [];
        let counts = [];

        if (this.currentDay === 'day1') {
            // Use live API hourly trend
            const trend = this.hourlyTrendData || [];
            labels = trend.map(t => t.time);
            counts = trend.map(t => t.count);
        } else {
            // Generate or fetch static historical values for Day 02/03
            const key = this.currentDay;
            if (!this.historicalMockTrends[key]) {
                this.historicalMockTrends[key] = this.generateHistoricalTrendData(key);
            }
            labels = this.historicalMockTrends[key].labels;
            counts = this.historicalMockTrends[key].counts;
        }

        window.crowdChart.updateData(labels, counts);
    }

    /**
     * Generate static datasets for Day 02 and Day 03
     */
    generateHistoricalTrendData(dayKey) {
        const labels = [
            '6:00 Am', '7:00 Am', '8:00 Am', '9:00 Am', '10:00 Am', '11:00 Am',
            '12:00 Pm', '1:00 Pm', '2:00 Pm', '3:00 Pm', '4:00 Pm', '5:00 Pm', '6:00 Pm'
        ];
        
        let counts = [];
        if (dayKey === 'day2') {
            counts = [480, 520, 650, 590, 710, 680, 740, 780, 810, 720, 700, 690, 680];
        } else {
            counts = [510, 580, 680, 630, 730, 710, 790, 840, 850, 740, 750, 720, 710];
        }

        return { labels, counts };
    }

    /**
     * Updates UI when system transitions online/offline.
     */
    handleSystemOfflineState(isOffline, reason) {
        if (isOffline) {
            this.liveBadgeContainer.innerHTML = `
                <span class="badge badge-offline">
                    Offline <span class="live-dot pulse-red"></span>
                </span>
            `;
            console.warn('Dashboard App running in OFFLINE mode. Reason:', reason);
        } else {
            this.liveBadgeContainer.innerHTML = `
                <span class="badge badge-live">
                    Live <span class="live-dot pulse-green"></span>
                </span>
            `;
        }
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

    /**
     * Initialize Chart.js line charts (sparklines) inside each Zone card.
     */
    initZoneCharts() {
        console.log("[Sparkline Debug] Starting initZoneCharts...");
        try {
            const canvasElements = document.querySelectorAll('.zone-sparkline-canvas');
            console.log("[Sparkline Debug] Found canvas elements:", canvasElements.length);
            
            canvasElements.forEach(canvas => {
                const zoneId = canvas.dataset.zoneId;
                // Clean any formatted commas from the strings before parsing to avoid single-digit truncation
                const capacityRaw = (canvas.dataset.capacity || '1000').toString().replace(/,/g, '');
                const initialCountRaw = (canvas.dataset.initialCount || '0').toString().replace(/,/g, '');
                const capacity = parseFloat(capacityRaw);
                const initialCount = parseFloat(initialCountRaw);
                const occupancy = parseFloat(canvas.dataset.initialOccupancy || 0);
                console.log(`[Sparkline Debug] Init ${zoneId}: cap=${capacity}, cnt=${initialCount}, occ=${occupancy}`);
                
                // Build a base history of 15 points leading up to the current count value
                const historyPoints = 15;
                const data = [];
                for (let i = 0; i < historyPoints; i++) {
                    const progressRatio = i / (historyPoints - 1);
                    const baseline = initialCount * progressRatio;
                    const fluctuation = Math.random() * (capacity * 0.05) - (capacity * 0.02);
                    data.push(Math.max(0, Math.min(capacity, baseline + fluctuation)));
                }

                // Determine border and fill colors based on occupancy level
                let color = '#22c55e'; // green
                let fill = 'rgba(34, 197, 94, 0.06)';
                if (occupancy >= 100) {
                    color = '#7f1d1d';
                    fill = 'rgba(127, 29, 29, 0.06)';
                } else if (occupancy >= 90) {
                    color = '#ef4444';
                    fill = 'rgba(239, 68, 68, 0.06)';
                } else if (occupancy >= 80) {
                    color = '#f97316';
                    fill = 'rgba(249, 115, 22, 0.06)';
                } else if (occupancy >= 60) {
                    color = '#eab308';
                    fill = 'rgba(234, 179, 8, 0.06)';
                }

                // Destroy existing chart on this canvas if any exists to avoid canvas reuse error
                try {
                    const existingChart = Chart.getChart(canvas);
                    if (existingChart) {
                        existingChart.destroy();
                    }
                } catch (err) {
                    console.warn("[Sparkline Debug] Error checking/destroying chart instance:", err);
                }

                // Create Chart.js instance
                this.zoneCharts[zoneId] = new Chart(canvas, {
                    type: 'line',
                    data: {
                        labels: Array(historyPoints).fill(''),
                        datasets: [{
                            data: data,
                            borderColor: color,
                            backgroundColor: fill,
                            fill: 'start',
                            tension: 0.4,
                            borderWidth: 2,
                            pointRadius: (context) => {
                                const index = context.dataIndex;
                                const count = context.dataset.data.length;
                                return index === count - 1 ? 5.5 : 3.5;
                            },
                            pointHoverRadius: 0,
                            pointBackgroundColor: '#ffffff',
                            pointBorderColor: color,
                            pointBorderWidth: 2
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        animation: {
                            duration: 400
                        },
                        plugins: {
                            legend: { display: false },
                            tooltip: { enabled: false }
                        },
                        scales: {
                            x: {
                                display: true,
                                grid: {
                                    color: 'rgba(0, 0, 0, 0.04)',
                                    borderDash: [2, 2],
                                    drawTicks: false,
                                    drawOnChartArea: true
                                },
                                ticks: {
                                    display: false
                                }
                            },
                            y: {
                                display: true,
                                position: 'left',
                                min: 0,
                                max: Math.ceil(capacity * 1.05),
                                grid: {
                                    color: 'rgba(0, 0, 0, 0.04)',
                                    borderDash: [2, 2],
                                    drawTicks: false,
                                    drawOnChartArea: true
                                },
                                ticks: {
                                    font: {
                                        family: 'Outfit',
                                        size: 9,
                                        weight: '600'
                                    },
                                    color: color,
                                    stepSize: Math.round(capacity / 4),
                                    callback: (value) => Math.round(value)
                                }
                            }
                        },
                        layout: {
                            padding: {
                                top: 4,
                                bottom: 4,
                                left: 0,
                                right: 8
                            }
                        }
                    }
                });
                console.log(`[Sparkline Debug] Successfully built chart for ${zoneId}`);
            });
        } catch (e) {
            console.error("[Sparkline Debug] Failed in initZoneCharts:", e);
        }
    }
}

// Instantiate App
window.addEventListener('DOMContentLoaded', () => {
    window.dashboardApp = new DashboardApp();
});

// Acknowledge criminal watchlist detection from panel
window.acknowledgeCriminalDetection = async (detectionId) => {
    if (window.dashboardApp) {
        await window.dashboardApp.acknowledgeDetection(detectionId);
    }
};

// Lightbox Modal Functions
window.openImageLightbox = (src, caption) => {
    const modal = document.getElementById('image-lightbox-modal');
    const img = document.getElementById('lightbox-image');
    const cap = document.getElementById('lightbox-caption');
    if (modal && img) {
        img.src = src;
        if (cap) cap.textContent = caption || 'Image Preview';
        modal.classList.remove('hidden');
        // Trigger reflow for transition animation
        setTimeout(() => modal.classList.add('show'), 10);
    }
};

window.closeImageLightbox = () => {
    const modal = document.getElementById('image-lightbox-modal');
    if (modal) {
        modal.classList.remove('show');
        setTimeout(() => modal.classList.add('hidden'), 300);
    }
};

// Esc key to close lightbox modal
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        window.closeImageLightbox();
    }
});
