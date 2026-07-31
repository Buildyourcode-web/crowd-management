import React from 'react';
import { useClock } from '../../hooks/useClock';

/**
 * Dashboard header – pixel-identical to every Blade page header section.
 * Props:
 *   title        – page main title string (default "AI Crowd Management Dashboard")
 *   onBellClick  – callback to open notification drawer
 *   unreadCount  – number shown on bell badge
 */
export default function DashboardHeader({ title = 'AI Crowd Management Dashboard', onBellClick, unreadCount = 0 }) {
  const { date, time } = useClock();

  return (
    <header className="dashboard-header">
      {/* Left: Police logo */}
      <div className="header-left">
        <img src="/images/police-logo.png" alt="Police Logo" className="logo-image" />
      </div>

      {/* Center: Title + BYC AI brand */}
      <div className="header-center">
        <h1 className="main-title">{title}</h1>
        <p className="subtitle">
          Powered by <img src="/images/LOGO_Bold.png" alt="BYC AI Logo" className="byc-logo" />
        </p>
      </div>

      {/* Right: Live clock, live badge, bell */}
      <div className="header-right">
        <div className="time-block">
          <span className="header-date">{date}</span>
          <span className="divider">|</span>
          <span className="header-time">{time}</span>
        </div>

        <div id="live-badge-container">
          <span className="badge badge-live">
            Live <span className="live-dot pulse-green"></span>
          </span>
        </div>

        <button
          type="button"
          className="btn-icon-bell"
          onClick={onBellClick}
          aria-label="Open notifications drawer"
        >
          <i className="fa-regular fa-bell"></i>
          <span className={`badge-count${unreadCount > 0 ? '' : ' hidden'}`}>
            {unreadCount}
          </span>
        </button>
      </div>
    </header>
  );
}
