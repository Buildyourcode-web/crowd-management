import React, { memo } from 'react';
import DashboardLayout from '../components/layout/DashboardLayout';
import SummaryCard from '../components/SummaryCard';
import ZoneCard from '../components/ZoneCard';
import GatesTable from '../components/GatesTable';
import QueuesTable from '../components/QueuesTable';
import CriminalPanel from '../components/CriminalPanel';
import CrowdTrendChart from '../components/CrowdTrendChart';
import { useDashboard } from '../hooks/useDashboard';

const ZONES_CONFIG = [
  { id: 'zone-a', name: 'Zone A', capacity: 1000 },
  { id: 'zone-b', name: 'Zone B', capacity: 900  },
  { id: 'zone-c', name: 'Zone C', capacity: 800  },
  { id: 'zone-d', name: 'Zone D', capacity: 850  },
];

export default function Overview() {
  const dash = useDashboard();

  // Merge API zone data with config defaults
  const zones = ZONES_CONFIG.map(cfg => {
    const live = dash.zones.find(z => z.id === cfg.id) || {};
    return {
      ...cfg,
      count:     live.current_count         || 0,
      occupancy: live.occupancy_percentage  || 0,
      capacity:  live.capacity              || cfg.capacity,
    };
  });

  // Filter hourly trend for selected day
  const trendData = Array.isArray(dash.hourlyTrend)
    ? dash.hourlyTrend.filter(d => !d.day || d.day === dash.currentDay)
    : [];

  return (
    <DashboardLayout pageTitle="AI Crowd Management Dashboard">

      {/* Summary Cards */}
      <section className="summary-cards-section">
        <SummaryCard id="visits-card"  title="Total Visits"   value={dash.summary.total_visits   || 0} icon="fa-solid fa-users"              colorClass="bg-blue"       />
        <SummaryCard id="present-card" title="People Present" value={dash.summary.people_present  || 0} icon="fa-solid fa-user"               colorClass="bg-orange"     />
        <SummaryCard id="entries-card" title="Total Entries"  value={dash.summary.total_entries   || 0} icon="fa-solid fa-right-to-bracket"   colorClass="bg-green"      />
        <SummaryCard id="exits-card"   title="Total Exits"    value={dash.summary.total_exits     || 0} icon="fa-solid fa-right-from-bracket" colorClass="bg-blue-light" />
      </section>

      {/* Zone Heat Map */}
      <section className="zone-heatmap-section">
        <h2 className="section-title">Zone Crowd Heat Map</h2>
        <div className="zone-cards-grid">
          {zones.map(z => (
            <ZoneCard key={z.id} type="line" {...z} />
          ))}
        </div>
      </section>

      {/* Middle Grid: Gates + Queues + Criminal */}
      <section className="middle-grid-section">
        <div className="grid-card gates-card">
          <h3 className="grid-card-title">Gate wise Entry/ Exit</h3>
          <GatesTable gates={dash.gates} />
        </div>

        <div className="grid-card queues-card">
          <h3 className="grid-card-title">Queue Movement</h3>
          <QueuesTable queues={dash.queues} />
        </div>

        <CriminalPanel
          criminalRecords={dash.criminalRecords}
          activeDetections={dash.activeDetections}
          currentDetectionIdx={dash.currentDetectionIdx}
          setCurrentDetectionIdx={dash.setCurrentDetectionIdx}
          onRefresh={dash.refetch}
        />
      </section>

      {/* Hourly Trend Chart */}
      <CrowdTrendChart
        trendData={trendData}
        selectedDay={dash.currentDay}
        onDayChange={dash.setCurrentDay}
      />

    </DashboardLayout>
  );
}
