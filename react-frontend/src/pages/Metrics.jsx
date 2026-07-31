import React from 'react';
import DashboardLayout from '../components/layout/DashboardLayout';
import { useDashboard } from '../hooks/useDashboard';

/**
 * Metrics Detail page – pixel-identical to dashboard/metrics.blade.php
 */
export default function Metrics() {
  const { summary, avgEntryRate, avgExitRate } = useDashboard();

  const cards = [
    {
      id: 'visits-val',
      title: 'Total Visits',
      value: summary.total_visits  || 0,
      iconClass: 'icon-blue',
      icon: 'fa-solid fa-users',
      barWidth: '75%',
      barClass: 'icon-blue',
      trend: { cls: 'trend-up', icon: 'fa-solid fa-arrow-trend-up', text: '+12.3%' },
      sub: 'Since yesterday',
    },
    {
      id: 'present-val',
      title: 'People Present',
      value: summary.people_present || 0,
      iconClass: 'icon-orange',
      icon: 'fa-solid fa-user',
      barWidth: '58%',
      barClass: 'icon-orange',
      trend: { cls: 'trend-neutral', icon: 'fa-solid fa-minus', text: 'Stable' },
      sub: 'Live check',
    },
    {
      id: 'entries-val',
      title: 'Total Entries',
      value: summary.total_entries  || 0,
      iconClass: 'icon-green',
      icon: 'fa-solid fa-right-to-bracket',
      barWidth: '82%',
      barClass: 'icon-green',
      trend: { cls: 'trend-up', icon: 'fa-solid fa-arrow-trend-up', text: '+8.5%' },
      sub: 'Since 6:00 AM',
    },
    {
      id: 'exits-val',
      title: 'Total Exits',
      value: summary.total_exits    || 0,
      iconClass: 'icon-teal',
      icon: 'fa-solid fa-right-from-bracket',
      barWidth: '64%',
      barClass: 'icon-teal',
      trend: { cls: 'trend-up', icon: 'fa-solid fa-arrow-trend-up', text: '+14.2%' },
      sub: 'Since 6:00 AM',
    },
  ];

  return (
    <DashboardLayout pageTitle="AI Crowd Management Dashboard">

      {/* Metrics Grid */}
      <section className="metrics-detail-grid">
        {cards.map(c => (
          <div key={c.id} className="metric-expanded-card">
            <div className="metric-card-header">
              <span className="metric-card-title">{c.title}</span>
              <div className={`metric-card-icon-wrapper ${c.iconClass}`}>
                <i className={c.icon}></i>
              </div>
            </div>
            <div className="metric-card-value font-numeric" id={c.id}>
              {(c.value).toLocaleString()}
            </div>
            <div className="metric-card-trend-bar">
              <div className={`metric-trend-fill ${c.barClass}`} style={{ width: c.barWidth }}></div>
            </div>
            <div className="metric-card-footer">
              <span className={`metric-trend-badge ${c.trend.cls}`}>
                <i className={c.trend.icon}></i> {c.trend.text}
              </span>
              <span>{c.sub}</span>
            </div>
          </div>
        ))}
      </section>

      {/* Flow Analytics card */}
      <div className="grid-card" style={{ marginBottom: '24px', padding: '24px' }}>
        <h3 className="grid-card-title" style={{ marginBottom: '16px' }}>
          <i className="fa-solid fa-chart-line"></i> Flow Analytics
        </h3>
        <div style={{ display: 'flex', gap: '40px', flexWrap: 'wrap', marginTop: '10px' }}>
          {/* Average Entry Rate */}
          <div style={{ flex: 1, minWidth: '250px', background: '#fafbfc', border: '1px solid #e2e8f0', borderRadius: 'var(--border-radius-md)', padding: '20px', display: 'flex', alignItems: 'center', gap: '16px' }}>
            <div style={{ width: '48px', height: '48px', borderRadius: '50%', background: 'rgba(34,197,94,.1)', color: '#22c55e', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '20px' }}>
              <i className="fa-solid fa-arrow-trend-up"></i>
            </div>
            <div>
              <div style={{ fontSize: '13px', color: 'var(--text-secondary)', fontWeight: 500 }}>Average Entry Rate</div>
              <div style={{ fontSize: '20px', fontWeight: 700, color: 'var(--text-primary)', marginTop: '2px' }} id="avg-entry-rate-val">
                {avgEntryRate} / hour
              </div>
            </div>
          </div>

          {/* Average Exit Rate */}
          <div style={{ flex: 1, minWidth: '250px', background: '#fafbfc', border: '1px solid #e2e8f0', borderRadius: 'var(--border-radius-md)', padding: '20px', display: 'flex', alignItems: 'center', gap: '16px' }}>
            <div style={{ width: '48px', height: '48px', borderRadius: '50%', background: 'rgba(59,130,246,.1)', color: '#3b82f6', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '20px' }}>
              <i className="fa-solid fa-arrow-trend-down"></i>
            </div>
            <div>
              <div style={{ fontSize: '13px', color: 'var(--text-secondary)', fontWeight: 500 }}>Average Exit Rate</div>
              <div style={{ fontSize: '20px', fontWeight: 700, color: 'var(--text-primary)', marginTop: '2px' }} id="avg-exit-rate-val">
                {avgExitRate} / hour
              </div>
            </div>
          </div>
        </div>
      </div>

    </DashboardLayout>
  );
}
