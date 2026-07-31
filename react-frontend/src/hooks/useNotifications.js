import { useState, useCallback, useRef } from 'react';
import { fetchNotifications, markNotificationRead, markAllNotificationsRead } from '../services/api';
import { playSound } from '../services/audioService';

/**
 * Notification management hook – mirrors NotificationManager from notifications.js
 */
export function useNotifications() {
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount]     = useState(0);
  const [isOpen, setIsOpen]               = useState(false);
  const [activeFilter, setActiveFilter]   = useState('all');
  const seenIds = useRef(new Set());

  const reload = useCallback(async (filter = 'all') => {
    try {
      const data = await fetchNotifications(filter);
      const list = data.notifications || [];
      setNotifications(list);
      setUnreadCount(data.unread_count || 0);

      // Play sound for new unread non-criminal notifications
      let playStandard = false;
      list.forEach(n => {
        if (!n.is_read && !seenIds.current.has(n.id)) {
          if (n.type !== 'criminal_detected' && n.type !== 'zone_full' && n.type !== 'zone_capacity') {
            if (n.severity === 'critical' || n.severity === 'warning' || n.type === 'face_scan_cleared') {
              playStandard = true;
            }
          }
          seenIds.current.add(n.id);
        }
      });
      if (playStandard) playSound('standard');
    } catch { /* non-fatal */ }
  }, []);

  const openDrawer = useCallback(() => {
    setIsOpen(true);
    reload(activeFilter);
  }, [reload, activeFilter]);

  const closeDrawer = useCallback(() => setIsOpen(false), []);

  const changeFilter = useCallback((filter) => {
    setActiveFilter(filter);
    reload(filter);
  }, [reload]);

  const acknowledge = useCallback(async (id) => {
    try {
      await markNotificationRead(id);
      await reload(activeFilter);
    } catch { /* non-fatal */ }
  }, [reload, activeFilter]);

  const markAllRead = useCallback(async () => {
    try {
      await markAllNotificationsRead();
      await reload(activeFilter);
    } catch { /* non-fatal */ }
  }, [reload, activeFilter]);

  return {
    notifications, unreadCount,
    isOpen, openDrawer, closeDrawer,
    activeFilter, changeFilter,
    acknowledge, markAllRead,
    reload,
  };
}
