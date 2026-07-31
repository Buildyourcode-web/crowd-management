import React, { useEffect, useRef, useMemo } from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';
import { Bar } from 'react-chartjs-2';

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend);

/** Custom plugin: draws values above bars (mirrors CrowdChartController.barLabelsPlugin) */
const barLabelsPlugin = {
  id: 'barLabels',
  afterDatasetsDraw(chart) {
    const { ctx } = chart;
    ctx.save();
    ctx.font        = 'bold 12px "Outfit", sans-serif';
    ctx.fillStyle   = '#475569';
    ctx.textAlign   = 'center';
    ctx.textBaseline = 'bottom';
    chart.data.datasets.forEach((dataset, i) => {
      chart.getDatasetMeta(i).data.forEach((bar, idx) => {
        const v = dataset.data[idx];
        if (v > 0) ctx.fillText(v.toLocaleString(), bar.x, bar.y - 5);
      });
    });
    ctx.restore();
  },
};

/**
 * Hourly Crowd Trend bar chart – mirrors CrowdChartController from crowd-chart.js
 * Props: trendData=[{label, value},...], selectedDay, onDayChange
 */
export default function CrowdTrendChart({ trendData = [], selectedDay = 'day1', onDayChange }) {
  const labels = useMemo(() => trendData.map(d => d.label || d.hour || ''), [trendData]);
  const values = useMemo(() => trendData.map(d => d.value || d.count || 0),  [trendData]);
  const maxVal = Math.max(...values, 100);

  const data = {
    labels,
    datasets: [{
      label: 'Crowd Count',
      data: values,
      backgroundColor:      '#3b82f6',
      hoverBackgroundColor: '#2563eb',
      borderRadius: 8,
      borderSkipped: false,
      barPercentage: 0.5,
      categoryPercentage: 0.8,
    }],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: {
        callbacks: {
          label: ctx => `Count: ${ctx.parsed.y.toLocaleString()}`,
        },
      },
    },
    scales: {
      x: {
        grid: { display: false },
        ticks: { font: { family: 'Outfit', size: 12, weight: '500' }, color: '#64748b' },
      },
      y: {
        beginAtZero: true,
        grid: { color: '#f1f5f9' },
        ticks: {
          font: { family: 'Outfit', size: 12 },
          color: '#94a3b8',
          callback: v => v.toLocaleString(),
        },
        suggestedMax: maxVal * 1.15,
      },
    },
  };

  return (
    <section className="hourly-trend-section">
      <div className="chart-card">
        <div className="chart-header">
          <h3 className="chart-title">Hourly Crowd Trend</h3>
          <div className="chart-actions">
            <select
              id="day-select"
              className="dropdown-select"
              value={selectedDay}
              onChange={e => onDayChange && onDayChange(e.target.value)}
              aria-label="Select day for hourly trend"
            >
              <option value="day1">Day 01</option>
              <option value="day2">Day 02</option>
              <option value="day3">Day 03</option>
            </select>
          </div>
        </div>
        <div className="chart-container">
          <Bar
            id="crowd-trend-chart"
            data={data}
            options={options}
            plugins={[barLabelsPlugin]}
          />
        </div>
      </div>
    </section>
  );
}
