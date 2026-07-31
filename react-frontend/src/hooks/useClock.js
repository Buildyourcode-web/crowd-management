import { useState, useEffect, useRef } from 'react';

/**
 * Live clock hook – mirrors DashboardApp.startClock()
 * Returns { date: "31 Jul 2026", time: "06:30:00 PM" }
 */
export function useClock() {
  const [clock, setClock] = useState({ date: '-- --- ----', time: '00:00:00 AM' });
  const timerRef = useRef(null);

  useEffect(() => {
    function tick() {
      const now = new Date();
      const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
      const day   = String(now.getDate()).padStart(2, '0');
      const month = months[now.getMonth()];
      const year  = now.getFullYear();

      let h = now.getHours();
      const ampm = h >= 12 ? 'PM' : 'AM';
      h = h % 12 || 12;
      const mm = String(now.getMinutes()).padStart(2, '0');
      const ss = String(now.getSeconds()).padStart(2, '0');
      const hh = String(h).padStart(2, '0');

      setClock({ date: `${day} ${month} ${year}`, time: `${hh}:${mm}:${ss} ${ampm}` });
    }

    tick();
    timerRef.current = setInterval(tick, 1000);
    return () => clearInterval(timerRef.current);
  }, []);

  return clock;
}
