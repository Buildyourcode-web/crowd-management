import React, { useMemo } from 'react';
import ZoneSparkline from './ZoneSparkline';

/** Compute status class + label from occupancy % – mirrors zone-card.blade.php logic */
function getZoneStatus(occupancy) {
  if (occupancy >= 100) return { cls: 'zone-red pulse-critical', label: 'Zone Full' };
  if (occupancy >= 90)  return { cls: 'zone-red pulse-warning',  label: 'Near Capacity' };
  if (occupancy >= 80)  return { cls: 'zone-orange',             label: 'Near Capacity' };
  if (occupancy >= 60)  return { cls: 'zone-yellow',             label: 'Warning' };
  return { cls: 'zone-green', label: 'Normal' };
}

/** Sparkline status colour from occupancy */
function sparkColour(occupancy) {
  if (occupancy >= 90) return 'red';
  if (occupancy >= 80) return 'orange';
  if (occupancy >= 60) return 'yellow';
  return 'green';
}

/**
 * Zone card – replicates x-zone-card Blade component with both variants:
 *   type="line"  → vertical progress bar layout (Overview page)
 *   type="wave"  → horizontal sparkline layout (Zones page)
 *
 * Props: id, name, count, capacity, occupancy, type, history, getZoneHistory
 */
export default function ZoneCard({ id, name, count = 0, capacity = 1000, occupancy = 0, type = 'line', getZoneHistory }) {
  const occ    = parseFloat(occupancy) || 0;
  const { cls, label } = getZoneStatus(occ);
  const colour = sparkColour(occ);

  const history = useMemo(() => {
    if (type !== 'wave' || !getZoneHistory) return [];
    return getZoneHistory(id, count, capacity);
  }, [id, count, capacity, type, getZoneHistory]); // eslint-disable-line react-hooks/exhaustive-deps

  if (type === 'wave') {
    return (
      <div className={`zone-card waves-type zone-card-horizontal ${cls}`} id={`card-${id}`}>
        {/* Left: counts */}
        <div className="card-left-section">
          <span className="zone-card-name">{name}</span>
          <span className="zone-card-count font-numeric">{count.toLocaleString()}</span>
          <span className="zone-capacity-sub">
            <i className="fa-solid fa-users-viewfinder"></i> Cap:{' '}
            <span className="font-numeric">{capacity.toLocaleString()}</span>
          </span>
        </div>

        {/* Middle: sparkline */}
        <div className="card-chart-section">
          <ZoneSparkline history={history} capacity={capacity} statusClass={colour} />
        </div>

        {/* Right: status + percentage */}
        <div className="card-right-section">
          <span className="zone-card-label">{label}</span>
          <span className="zone-percentage font-numeric">{occ}%</span>
          <span className="capacity-subtext">of capacity</span>
        </div>
      </div>
    );
  }

  // Default: vertical line layout (Overview)
  return (
    <div className={`zone-card ${cls}`} id={`card-${id}`}>
      <div className="zone-card-header">
        <span className="zone-card-name">{name}</span>
        <span className="zone-card-label">{label}</span>
      </div>
      <div className="zone-card-body">
        <span className="zone-card-count font-numeric">{count.toLocaleString()}</span>
      </div>
      <div className="zone-card-footer">
        <div className="zone-progress-bg">
          <div className="zone-progress-bar" style={{ width: `${Math.min(100, occ)}%` }}></div>
        </div>
        <div className="zone-meta">
          <span className="zone-capacity">
            Cap: <span className="font-numeric">{capacity.toLocaleString()}</span>
          </span>
          <span className="zone-percentage font-numeric">{occ}%</span>
        </div>
      </div>
    </div>
  );
}
