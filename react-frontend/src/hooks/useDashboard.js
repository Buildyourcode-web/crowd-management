import { useState, useEffect, useRef, useCallback } from 'react';
import {
  fetchDashboardData,
  fetchCriminalRecords,
  fetchCriminalDetections,
} from '../services/api';
import { playSound, stopSound } from '../services/audioService';

const REFRESH_MS = Number(import.meta.env.VITE_REFRESH_INTERVAL_MS) || 2000;

/**
 * Central dashboard polling hook.
 * Mirrors DashboardApp from dashboard.js
 */
export function useDashboard() {
  const [summary, setSummary]         = useState({ total_visits:0, people_present:0, total_entries:0, total_exits:0 });
  const [zones, setZones]             = useState([]);
  const [gates, setGates]             = useState([]);
  const [queues, setQueues]           = useState([]);
  const [hourlyTrend, setHourlyTrend] = useState([]);
  const [currentDay, setCurrentDay]   = useState('day1');
  const [isOffline, setIsOffline]     = useState(false);

  // Criminal panel state
  const [criminalRecords, setCriminalRecords]       = useState([]);
  const [activeDetections, setActiveDetections]     = useState([]);
  const [currentDetectionIdx, setCurrentDetectionIdx] = useState(0);
  const [currentRecordIdx, setCurrentRecordIdx]     = useState(0);

  const pollingRef     = useRef(null);
  const isTabActive    = useRef(true);
  const lastZoneStates = useRef({});
  const autoAckIds     = useRef(new Set());
  const prevDetections = useRef([]);
  const zoneHistory    = useRef({});

  // ── fetch and update all dashboard data ───────────────────────────────────
  const fetchAll = useCallback(async () => {
    try {
      const data = await fetchDashboardData();
      if (!data || !data.success) { setIsOffline(true); return; }
      setIsOffline(false);

      setSummary(data.summary || {});
      setGates(data.gates   || []);
      setQueues(data.queues  || []);

      const newZones = data.zones || [];
      setZones(newZones);
      handleZoneSounds(newZones);

      const trend = data.hourly_trend || [];
      setHourlyTrend(trend);

      // ── criminal detections ──────────────────────────────────────────────
      try {
        const detRes = await fetchCriminalDetections();
        if (detRes.success) {
          const newDets = detRes.detections || [];
          const oldDets = prevDetections.current;
          prevDetections.current = newDets;

          const hasNew = newDets.length > 0 && (
            !oldDets || oldDets.length === 0 || newDets[0].id !== oldDets[0]?.id
          );
          if (hasNew || newDets.length !== oldDets.length) {
            setCurrentDetectionIdx(0);
          }
          setActiveDetections(newDets);
        }
      } catch { /* non-fatal */ }

    } catch {
      setIsOffline(true);
    }
  }, []);

  // ── zone sound thresholds ─────────────────────────────────────────────────
  function handleZoneSounds(zones) {
    let anyZoneCritical = false;
    let anyZoneWarning  = false;

    zones.forEach(zone => {
      const count = zone.current_count;
      const last  = lastZoneStates.current[zone.id] || {};
      const b500  = count >= 500;
      const b300  = count >= 300;

      if (b500 && !last.breached500) playSound('red_zone');
      else if (b300 && !last.breached300 && !b500) playSound('orange');

      lastZoneStates.current[zone.id] = { breached300: b300, breached500: b500 };
      if (b500) anyZoneCritical = true;
      if (b300 && !b500) anyZoneWarning = true;
    });

    if (!anyZoneCritical) stopSound('red_zone');
    if (!anyZoneWarning)  stopSound('orange');
  }

  // ── load initial criminal data ─────────────────────────────────────────────
  useEffect(() => {
    async function loadCriminals() {
      try {
        const [recRes, detRes] = await Promise.all([
          fetchCriminalRecords(),
          fetchCriminalDetections(),
        ]);
        if (recRes.success) setCriminalRecords(recRes.records || []);
        if (detRes.success) {
          prevDetections.current = detRes.detections || [];
          setActiveDetections(detRes.detections || []);
        }
      } catch { /* non-fatal */ }
    }
    loadCriminals();
  }, []);

  // ── polling loop ───────────────────────────────────────────────────────────
  useEffect(() => {
    fetchAll();

    const startPolling = () => {
      pollingRef.current = setInterval(() => {
        if (isTabActive.current) fetchAll();
      }, REFRESH_MS);
    };

    startPolling();

    const handleVisibility = () => {
      if (document.hidden) {
        isTabActive.current = false;
        clearInterval(pollingRef.current);
      } else {
        isTabActive.current = true;
        fetchAll();
        startPolling();
      }
    };
    document.addEventListener('visibilitychange', handleVisibility);

    return () => {
      clearInterval(pollingRef.current);
      document.removeEventListener('visibilitychange', handleVisibility);
    };
  }, [fetchAll]);

  // ── criminal panel auto-rotation (5 s) ────────────────────────────────────
  useEffect(() => {
    const unacked = activeDetections.filter(d => d.status === 'detected');
    if (unacked.length === 0 && criminalRecords.length === 0) return;

    const timer = setInterval(() => {
      if (unacked.length > 0) {
        setCurrentDetectionIdx(i => (i + 1) % unacked.length);
      } else if (criminalRecords.length > 0) {
        setCurrentRecordIdx(i => (i + 1) % criminalRecords.length);
      }
    }, 5000);
    return () => clearInterval(timer);
  }, [activeDetections, criminalRecords]);

  // ── auto-play danger sound on new unacked detection ───────────────────────
  useEffect(() => {
    const unacked = activeDetections.filter(d => d.status === 'detected');
    unacked.forEach(det => {
      if (!autoAckIds.current.has(det.id)) {
        autoAckIds.current.add(det.id);
        playSound('danger');
      }
    });
  }, [activeDetections]);

  // ── zone history for sparklines ───────────────────────────────────────────
  function getZoneHistory(zoneId, currentCount, capacity) {
    if (!zoneHistory.current[zoneId]) {
      const steps = 18;
      const history = [];
      for (let i = 0; i < steps; i++) {
        const phase = (i / (steps - 1)) * Math.PI * 1.8;
        const ratio = 0.5 + Math.sin(phase) * 0.2 + (Math.random() - 0.5) * 0.12;
        history.push(Math.round(capacity * Math.min(0.98, Math.max(0.15, ratio))));
      }
      history[history.length - 1] = currentCount;
      zoneHistory.current[zoneId] = history;
    } else {
      zoneHistory.current[zoneId].push(currentCount);
      if (zoneHistory.current[zoneId].length > 18) zoneHistory.current[zoneId].shift();
    }
    return zoneHistory.current[zoneId];
  }

  // ── computed avg rates ─────────────────────────────────────────────────────
  const currentHour    = new Date().getHours();
  const hoursElapsed   = currentHour >= 6 ? Math.max(1, currentHour - 6) : 8;
  const avgEntryRate   = Math.round((summary.total_entries || 0) / hoursElapsed);
  const avgExitRate    = Math.round((summary.total_exits   || 0) / hoursElapsed);

  return {
    summary, zones, gates, queues, hourlyTrend,
    currentDay, setCurrentDay,
    isOffline,
    criminalRecords, activeDetections,
    currentDetectionIdx, setCurrentDetectionIdx,
    currentRecordIdx,   setCurrentRecordIdx,
    avgEntryRate, avgExitRate,
    getZoneHistory,
    refetch: fetchAll,
  };
}
