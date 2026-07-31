import React from 'react';
import DashboardLayout from '../components/layout/DashboardLayout';
import GatesTable from '../components/GatesTable';
import QueuesTable from '../components/QueuesTable';
import CrowdTrendChart from '../components/CrowdTrendChart';
import { useDashboard } from '../hooks/useDashboard';

/**
 * Gates & Queues Flow page – pixel-identical to dashboard/traffic.blade.php
 */
export default function Traffic() {
  const { gates, queues, hourlyTrend, currentDay, setCurrentDay } = useDashboard();

  const trendData = Array.isArray(hourlyTrend)
    ? hourlyTrend.filter(d => !d.day || d.day === currentDay)
    : [];

  return (
    <DashboardLayout pageTitle="AI Crowd Management Dashboard">

      {/* Gates & Queues side by side */}
      <section className="middle-grid-section two-columns">
        <div className="grid-card gates-card">
          <h3 className="grid-card-title">Gate wise Entry/ Exit</h3>
          <GatesTable gates={gates} />
        </div>

        <div className="grid-card queues-card">
          <h3 className="grid-card-title">Queue Movement</h3>
          <QueuesTable queues={queues} />
        </div>
      </section>

      {/* Hourly Trend Chart */}
      <div style={{ marginTop: '24px' }}>
        <CrowdTrendChart
          trendData={trendData}
          selectedDay={currentDay}
          onDayChange={setCurrentDay}
        />
      </div>

    </DashboardLayout>
  );
}
