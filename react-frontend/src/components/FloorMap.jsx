import React from 'react';

/**
 * 2D floor map heatmap – pixel-identical to the visualizer-card in zones.blade.php
 * Props: zones=[{id, name, current_count, occupancy_percentage, capacity}]
 */
const ZONE_META = {
  'zone-a': 'Zone A (North Concourse)',
  'zone-b': 'Zone B (South Promenade)',
  'zone-c': 'Zone C (East Entry Hall)',
  'zone-d': 'Zone D (Central Plaza)',
};

function mapStatusClass(occupancy) {
  if (occupancy >= 90) return 'zone-critical';
  if (occupancy >= 60) return 'zone-warning';
  return 'zone-normal';
}

export default function FloorMap({ zones = [] }) {
  // Build a lookup from zone id → data
  const byId = {};
  zones.forEach(z => { byId[z.id] = z; });

  const zoneIds = ['zone-a', 'zone-b', 'zone-c', 'zone-d'];

  return (
    <div className="visualizer-card">
      <h3 className="visualizer-title">
        <i className="fa-solid fa-network-wired"></i> Live 2D Schematic Floor Map
      </h3>

      <div className="visualizer-map-container">
        {/* Grid background */}
        <div className="map-grid-overlay"></div>

        {/* Radar scan line */}
        <div className="radar-scanline"></div>

        {/* Telemetry HUD */}
        <div className="map-telemetry">
          <span className="telemetry-item">
            <i className="fa-solid fa-satellite-dish fa-spin-pulse"></i> LIVE SENSORS ACTIVE
          </span>
          <span className="telemetry-item">
            <i className="fa-solid fa-microchip"></i> CALIBRATED
          </span>
        </div>

        {/* Floor map grid */}
        <div className="floor-map-grid">
          {zoneIds.map(zoneId => {
            const z      = byId[zoneId] || {};
            const occ    = z.occupancy_percentage || 0;
            const count  = z.current_count        || 0;
            const status = mapStatusClass(occ);
            const label  = ZONE_META[zoneId] || zoneId;

            return (
              <div
                key={zoneId}
                className={`map-zone-block ${status}`}
                id={`map-block-${zoneId}`}
              >
                <div className="heat-wave-container">
                  <div className="heat-wave wave-1"></div>
                  <div className="heat-wave wave-2"></div>
                  <div className="heat-wave wave-3"></div>
                  <div className="heat-wave-core"></div>
                </div>
                <div className="zone-block-content">
                  <span className="map-zone-name">{label}</span>
                  <div className="map-zone-stats">
                    <span className="map-zone-count font-numeric">{count.toLocaleString()}</span>
                    <span className="map-zone-percentage">{occ}% Occupancy</span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Legend */}
        <div className="map-overlay-legend">
          <span className="legend-item"><span className="legend-dot status-normal"></span> Normal (&lt;60%)</span>
          <span className="legend-item"><span className="legend-dot status-warning"></span> Warning (60%-90%)</span>
          <span className="legend-item"><span className="legend-dot status-critical"></span> Critical (&gt;90%)</span>
        </div>
      </div>
    </div>
  );
}
