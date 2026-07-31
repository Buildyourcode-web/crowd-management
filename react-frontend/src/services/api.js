import axios from 'axios';

const BASE = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api/v1';
const CAM_BASE = import.meta.env.VITE_CAMERAS_API_URL || 'http://127.0.0.1:8001/api/v1';

const api = axios.create({
  baseURL: BASE,
  headers: {
    Accept: 'application/json',
    'X-Requested-With': 'XMLHttpRequest',
  },
  timeout: 10000,
});

const camApi = axios.create({
  baseURL: CAM_BASE,
  headers: {
    Accept: 'application/json',
    'X-User-ID': 'admin',
    'X-User-Name': 'admin',
  },
  timeout: 10000,
});

// ── Dashboard ───────────────────────────────────────────────────────────────
export async function fetchDashboardData() {
  try {
    let data = { success: true, summary: {}, zones: [], gates: [], queues: [], hourly_trend: [] };
    try {
      const res = await api.get('/crowd-data');
      if (res.data) data = { ...data, ...res.data };
    } catch {
      /* fallback if /crowd-data not present */
    }

    // Always fetch real-time queue status directly from FastAPI /api/v1/queue/status
    try {
      const qRes = await api.get('/queue/status');
      if (qRes.data && qRes.data.data && Array.isArray(qRes.data.data.cameras)) {
        data.queues = qRes.data.data.cameras.map((c, i) => {
          let m = (c.queue_health || 'MOVING').toLowerCase();
          if (c.stagnation_seconds > 0 || c.stagnation_label === 'BLOCKED' || c.stagnation_label === 'CRITICAL') {
            m = 'stopped';
          }
          return {
            queue_number: `Queue ${i + 1}`,
            wait_minutes: Math.max(0, Math.round((c.stagnation_seconds || 0) / 60)),
            movement: m,
          };
        });
      }
    } catch (e) {
      /* ignore if no queue workers active */
    }

    return data;
  } catch (error) {
    console.error('fetchDashboardData Error:', error);
    return { success: false, queues: [] };
  }
}

// ── Notifications ───────────────────────────────────────────────────────────
export async function fetchNotifications(severity = '') {
  const params = { t: Date.now() };
  if (severity && severity !== 'all') params.severity = severity;
  const res = await api.get('/dashboard/notifications', { params });
  return res.data;
}

export async function markNotificationRead(id) {
  const res = await api.post(`/dashboard/notifications/${id}/read`);
  return res.data;
}

export async function markAllNotificationsRead() {
  const res = await api.post('/dashboard/notifications/read-all');
  return res.data;
}

// ── Criminal ────────────────────────────────────────────────────────────────
export async function fetchCriminalRecords() {
  const res = await api.get('/criminal-records', { params: { t: Date.now() } });
  return res.data;
}

export async function fetchCriminalDetections() {
  const res = await api.get('/criminal-detections', { params: { t: Date.now() } });
  return res.data;
}

export async function acknowledgeCriminalDetection(id) {
  const res = await api.patch(`/criminal-detections/${id}/acknowledge`);
  return res.data;
}

// ── Cameras ─────────────────────────────────────────────────────────────────
export async function fetchCameras() {
  const res = await camApi.get('/cameras');
  const data = res.data;
  return (data && data.data) ? data.data : (Array.isArray(data) ? data : []);
}

// ── Face Registration ────────────────────────────────────────────────────────
export async function registerFace(formData) {
  const res = await api.post('/face/register', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return res.data;
}

export async function fetchPersons() {
  const res = await api.get('/face/persons');
  return res.data;
}

export async function deletePerson(personId) {
  const res = await api.delete(`/face/${encodeURIComponent(personId)}`);
  return res.data;
}
