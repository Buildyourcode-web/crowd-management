import React from 'react';

/**
 * Alerts bar – the coloured ticker bar below the nav.
 * Clicking it opens the notification drawer.
 */
export default function AlertsBar({ unreadCount = 0, onOpen, title = 'AI Alerts' }) {
  return (
    <section className="alerts-bar-section">
      <div
        id="alerts-bar"
        className={`alerts-bar cursor-pointer${unreadCount > 0 ? ' alerts-bar-glow' : ''}`}
        onClick={onOpen}
        tabIndex={0}
        role="button"
        aria-label="View notifications"
        onKeyDown={e => e.key === 'Enter' && onOpen && onOpen()}
      >
        <span className="alerts-bar-title">{title}</span>
        <span className={`badge-alerts-count${unreadCount > 0 ? '' : ' hidden'}`}>
          {unreadCount}
        </span>
      </div>
    </section>
  );
}
