import React, { useEffect } from 'react';

const SEVERITY_ICON = {
  critical: 'fa-circle-exclamation',
  warning:  'fa-triangle-exclamation',
  success:  'fa-circle-check',
  info:     'fa-circle-info',
};

function formatRelativeTime(dateString) {
  if (!dateString) return '';
  const seconds = Math.floor((Date.now() - new Date(dateString)) / 1000);
  if (seconds < 5)  return 'Just now';
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24)   return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

function escHTML(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g,'&amp;').replace(/</g,'&lt;')
    .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function NotificationItem({ notif, onAcknowledge }) {
  const icon         = SEVERITY_ICON[notif.severity] || SEVERITY_ICON.info;
  const severityClass = `severity-${notif.severity || 'info'}`;
  const unreadClass   = notif.is_read ? 'read' : 'unread';
  const isCritical    = notif.severity === 'critical';

  return (
    <div className={`notification-item ${unreadClass} ${severityClass}`} data-id={notif.id}>
      <div className="notification-item-icon">
        <i className={`fa-solid ${icon}`}></i>
      </div>
      <div className="notification-item-details">
        <div className="notification-item-meta">
          <span className="notification-item-title">{notif.title}</span>
          <span className="notification-item-time">{formatRelativeTime(notif.created_at)}</span>
        </div>
        <p className="notification-item-msg">{notif.message}</p>

        {notif.location && (
          <div className="notification-item-location">
            <i className="fa-solid fa-location-dot"></i> {notif.location}
          </div>
        )}

        {/* Criminal detection: split suspect + CCTV capture images */}
        {notif.type === 'criminal_detected' && notif.suspect_image_url && notif.image_url ? (
          <div className="notification-item-evidence-split" style={{ display:'flex', gap:'8px', marginTop:'10px', border:'1px solid var(--border-color)', borderRadius:'var(--border-radius-sm)', overflow:'hidden', height:'75px' }}>
            <img src={`${notif.suspect_image_url}?v=${Date.now()}`} alt="Suspect Profile"
              style={{ width:'50%', height:'100%', objectFit:'cover', borderRight:'1px solid var(--border-color)' }}
              onError={e => { e.target.src = '/images/detection-placeholder.jpg'; }} />
            <img src={`${notif.image_url}?v=${Date.now()}`} alt="CCTV Capture"
              style={{ width:'50%', height:'100%', objectFit:'cover' }}
              onError={e => { e.target.src = '/images/detection-placeholder.jpg'; }} />
          </div>
        ) : notif.image_url ? (
          <div className="notification-item-evidence" style={{ marginTop:'10px' }}>
            <img src={`${notif.image_url}?v=${Date.now()}`} alt="Snapshot evidence"
              className="notification-item-img"
              style={{ width:'100%', height:'100px', objectFit:'cover', borderRadius:'var(--border-radius-sm)' }}
              onError={e => { e.target.src = '/images/detection-placeholder.jpg'; }} />
          </div>
        ) : null}

        {!notif.is_read && (
          <div className="notification-item-actions">
            <button type="button" className="btn-acknowledge" onClick={() => onAcknowledge(notif.id)}>
              {isCritical ? 'Acknowledge' : 'Mark as Read'}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * Sliding notification drawer – pixel-identical to the drawer in every Blade page.
 */
export default function NotificationDrawer({
  isOpen, onClose,
  notifications, unreadCount,
  activeFilter, onFilterChange,
  onAcknowledge, onMarkAllRead,
}) {
  // Close on Escape key
  useEffect(() => {
    function handleKey(e) {
      if (e.key === 'Escape' && isOpen) onClose();
    }
    document.addEventListener('keydown', handleKey);
    return () => document.removeEventListener('keydown', handleKey);
  }, [isOpen, onClose]);

  const filters = ['all', 'critical', 'warning', 'info'];

  return (
    <>
      {/* Drawer */}
      <div id="notification-drawer" className={`notification-drawer${isOpen ? ' open' : ''}`}>
        <div className="drawer-header">
          <div className="drawer-header-title-block">
            <h3>Notifications</h3>
            <span className="drawer-count-badge">{unreadCount}</span>
          </div>
          <button type="button" className="btn-close-drawer" onClick={onClose} aria-label="Close drawer">
            <i className="fa-solid fa-xmark"></i>
          </button>
        </div>

        {/* Filters */}
        <div className="drawer-filters">
          {filters.map(f => (
            <button
              key={f}
              type="button"
              className={`filter-tab${activeFilter === f ? ' active' : ''}`}
              data-filter={f}
              onClick={() => onFilterChange(f)}
            >
              {f.charAt(0).toUpperCase() + f.slice(1)}
            </button>
          ))}
        </div>

        <div className="drawer-actions">
          <button type="button" className="btn-text" onClick={onMarkAllRead}>
            <i className="fa-solid fa-check-double"></i> Mark all as read
          </button>
        </div>

        {/* Notification list */}
        <div id="notification-list" className="notification-list">
          {notifications.length === 0 ? (
            <div className="empty-notifications">
              <i className="fa-regular fa-bell-slash"></i>
              <p>No notifications</p>
            </div>
          ) : (
            notifications.map(n => (
              <NotificationItem key={n.id} notif={n} onAcknowledge={onAcknowledge} />
            ))
          )}
        </div>
      </div>

      {/* Backdrop overlay */}
      <div
        id="drawer-overlay"
        className={`drawer-overlay${isOpen ? ' open' : ''}`}
        onClick={onClose}
      ></div>
    </>
  );
}
