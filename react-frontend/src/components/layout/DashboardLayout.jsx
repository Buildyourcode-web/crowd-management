import React from 'react';
import DashboardHeader from './DashboardHeader';
import DashboardNav from './DashboardNav';
import AlertsBar from './AlertsBar';
import NotificationDrawer from './NotificationDrawer';
import { useNotifications } from '../../hooks/useNotifications';
import { warmUpAudio } from '../../services/audioService';

/**
 * Shell that wraps every dashboard page.
 * Owns the notification drawer state shared across all pages.
 */
export default function DashboardLayout({ children, pageTitle }) {
  const notif = useNotifications();

  // Warm up audio channel on first render
  React.useEffect(() => {
    const handler = () => { warmUpAudio(); };
    document.addEventListener('click', handler, { once: true });
    document.addEventListener('keydown', handler, { once: true });
    return () => {
      document.removeEventListener('click', handler);
      document.removeEventListener('keydown', handler);
    };
  }, []);

  // Periodically refresh badge counts even when drawer is closed
  React.useEffect(() => {
    notif.reload(notif.activeFilter);
    const t = setInterval(() => notif.reload(notif.activeFilter), 5000);
    return () => clearInterval(t);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  function handleOpenDrawer() {
    notif.openDrawer();
  }

  return (
    <div id="app" className="dashboard-wrapper">
      <DashboardHeader
        title={pageTitle}
        onBellClick={handleOpenDrawer}
        unreadCount={notif.unreadCount}
      />

      <DashboardNav />

      <AlertsBar
        unreadCount={notif.unreadCount}
        onOpen={handleOpenDrawer}
        title="AI Alerts"
      />

      {/* Page-specific content */}
      {children}

      <NotificationDrawer
        isOpen={notif.isOpen}
        onClose={notif.closeDrawer}
        notifications={notif.notifications}
        unreadCount={notif.unreadCount}
        activeFilter={notif.activeFilter}
        onFilterChange={notif.changeFilter}
        onAcknowledge={notif.acknowledge}
        onMarkAllRead={notif.markAllRead}
      />
    </div>
  );
}
