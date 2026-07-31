import React from 'react';
import { NavLink } from 'react-router-dom';

const NAV_ITEMS = [
  { to: '/dashboard',          icon: 'fa-solid fa-chart-pie',          label: 'Overview' },
  { to: '/metrics',            icon: 'fa-solid fa-users-viewfinder',    label: 'Metrics Detail' },
  { to: '/zones',              icon: 'fa-solid fa-map-location-dot',    label: 'Zone Heatmap' },
  { to: '/traffic',            icon: 'fa-solid fa-arrows-spin',         label: 'Gates & Queues' },
  { to: '/cameras',            icon: 'fa-solid fa-video',               label: 'CCTV Grid' },
  { to: '/face-registration',  icon: 'fa-solid fa-face-viewfinder',     label: 'Face Register' },
];

/**
 * Navigation tab bar – pixel-identical to the nav in every Blade page.
 * Uses React Router NavLink so the active class is set automatically.
 */
export default function DashboardNav() {
  return (
    <nav className="dashboard-nav">
      {NAV_ITEMS.map(({ to, icon, label }) => (
        <NavLink
          key={to}
          to={to}
          className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}
        >
          <i className={icon}></i> {label}
        </NavLink>
      ))}
    </nav>
  );
}
