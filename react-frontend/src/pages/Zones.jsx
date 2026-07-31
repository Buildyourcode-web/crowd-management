import React from 'react';
import DashboardLayout from '../components/layout/DashboardLayout';
import ZoneCard from '../components/ZoneCard';
import FloorMap from '../components/FloorMap';
import { useDashboard } from '../hooks/useDashboard';

const ZONES_CONFIG = [
  { id: 'zone-a', name: 'Zone A', capacity: 1000 },
  { id: 'zone-b', name: 'Zone B', capacity: 900  },
  { id: 'zone-c', name: 'Zone C', capacity: 800  },
  { id: 'zone-d', name: 'Zone D', capacity: 850  },
];

/**
 * Zone Heatmap page – pixel-identical to dashboard/zones.blade.php
 */
export default function Zones() {
  const { zones: liveZones, getZoneHistory } = useDashboard();

  const zones = ZONES_CONFIG.map(cfg => {
    const live = liveZones.find(z => z.id === cfg.id) || {};
    return {
      ...cfg,
      count:     live.current_count        || 0,
      occupancy: live.occupancy_percentage || 0,
      capacity:  live.capacity             || cfg.capacity,
    };
  });

  return (
    <DashboardLayout pageTitle="AI Crowd Management Dashboard">
      <section className="zones-detail-layout">
        {/* Left column: horizontal wave zone cards */}
        <div className="zones-list-wrapper">
          {zones.map(z => (
            <ZoneCard key={z.id} type="wave" {...z} getZoneHistory={getZoneHistory} />
          ))}
        </div>

        {/* Right column: 2D floor map */}
        <FloorMap zones={liveZones} />
      </section>
    </DashboardLayout>
  );
}
