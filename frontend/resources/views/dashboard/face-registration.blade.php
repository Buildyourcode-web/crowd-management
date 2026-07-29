@extends('layouts.dashboard')

@section('title', 'Face Registration — AI Crowd Management')

@section('content')
<!-- Header Section -->
<header class="dashboard-header">
    <div class="header-left">
        <img src="{{ asset('images/police-logo.png') }}" alt="Police Logo" class="logo-image">
        <!-- <img src="{{ asset('images/white-TG.png') }}" alt="State Logo" class="logo-image"> -->
    </div>
    <div class="header-center">
        <h1 class="main-title">Face Registration</h1>
        <p class="subtitle">Powered by <img src="{{ asset('images/LOGO_Bold.png') }}" alt="BYC AI Logo" class="byc-logo"></p>
    </div>
    <div class="header-right">
        <div class="time-block">
            <span id="current-date" class="header-date">-- --- ----</span>
            <span class="divider">|</span>
            <span id="current-time" class="header-time">00:00:00 AM</span>
        </div>
    </div>
</header>

<!-- Navigation Tabs Bar -->
<nav class="dashboard-nav">
    <a href="{{ route('dashboard') }}" class="nav-link">
        <i class="fa-solid fa-chart-pie"></i> Overview
    </a>
    <a href="{{ route('dashboard.metrics') }}" class="nav-link">
        <i class="fa-solid fa-users-viewfinder"></i> Metrics Detail
    </a>
    <a href="{{ route('dashboard.zones') }}" class="nav-link">
        <i class="fa-solid fa-map-location-dot"></i> Zone Heatmap
    </a>
    <a href="{{ route('dashboard.traffic') }}" class="nav-link">
        <i class="fa-solid fa-arrows-spin"></i> Gates &amp; Queues
    </a>
    <a href="{{ route('dashboard.cameras') }}" class="nav-link">
        <i class="fa-solid fa-video"></i> Cameras
    </a>
    <a href="{{ route('dashboard.face-registration') }}" class="nav-link active">
        <i class="fa-solid fa-face-viewfinder"></i> Face Register
    </a>
</nav>

<!-- Page Content: Two-column layout -->
<section style="padding: 24px; max-width: 1400px; margin: 0 auto; display:grid; grid-template-columns: 380px 1fr; gap: 24px; align-items: start;">

    <!-- LEFT: Registration Form -->
    <div style="background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.1);border-radius:16px;padding:28px;position:sticky;top:24px;">
        <h2 style="margin:0 0 20px;font-size:1.1rem;font-weight:700;color:#fff;">
            <i class="fa-solid fa-user-plus" style="color:#6366f1;"></i> Register Person
        </h2>

        <form id="face-register-form" onsubmit="submitFaceRegistration(event)" enctype="multipart/form-data">
            @csrf

            <!-- Image Upload Zone -->
            <div id="upload-zone" style="border:2px dashed rgba(99,102,241,.4);border-radius:12px;padding:24px;text-align:center;cursor:pointer;margin-bottom:20px;transition:border-color .2s,background .2s;"
                onclick="document.getElementById('image-input').click()"
                ondragover="event.preventDefault();this.style.borderColor='#6366f1';this.style.background='rgba(99,102,241,.06)'"
                ondragleave="this.style.borderColor='rgba(99,102,241,.4)';this.style.background=''"
                ondrop="handleDrop(event)">
                <div id="upload-placeholder">
                    <i class="fa-solid fa-cloud-arrow-up" style="font-size:2rem;color:#6366f1;margin-bottom:10px;"></i>
                    <p style="margin:0;color:#9ca3af;font-size:14px;">Click or drag &amp; drop photo</p>
                    <p style="margin:4px 0 0;color:#6b7280;font-size:12px;">JPG, PNG, WebP — max 5 MB</p>
                </div>
                <img id="image-preview" src="" alt="Preview" style="display:none;max-width:100%;max-height:200px;border-radius:8px;object-fit:cover;">
            </div>
            <input type="file" id="image-input" name="image" accept="image/*" style="display:none;" onchange="previewImage(event)">

            <!-- Person ID -->
            <div style="margin-bottom:14px;">
                <label style="display:block;font-size:13px;color:#9ca3af;margin-bottom:6px;font-weight:600;">
                    Person ID <span style="color:#f87171;">*</span>
                </label>
                <input type="text" id="person-id" name="person_id" required maxlength="50"
                    placeholder="e.g. P001, WL-2026-001"
                    style="width:100%;background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.12);border-radius:8px;padding:10px 14px;color:#fff;font-size:14px;box-sizing:border-box;outline:none;">
            </div>

            <!-- Name -->
            <div style="margin-bottom:20px;">
                <label style="display:block;font-size:13px;color:#9ca3af;margin-bottom:6px;font-weight:600;">
                    Full Name <span style="color:#f87171;">*</span>
                </label>
                <input type="text" id="person-name" name="name" required maxlength="100"
                    placeholder="e.g. John Doe"
                    style="width:100%;background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.12);border-radius:8px;padding:10px 14px;color:#fff;font-size:14px;box-sizing:border-box;outline:none;">
            </div>

            <!-- Error / Success messages -->
            <div id="form-error" style="display:none;background:rgba(239,68,68,.12);border:1px solid rgba(239,68,68,.35);border-radius:8px;padding:10px 14px;color:#f87171;font-size:13px;margin-bottom:14px;"></div>
            <div id="form-success" style="display:none;background:rgba(34,197,94,.12);border:1px solid rgba(34,197,94,.35);border-radius:8px;padding:10px 14px;color:#4ade80;font-size:13px;margin-bottom:14px;"></div>

            <!-- Submit -->
            <button type="submit" id="btn-register"
                style="width:100%;background:linear-gradient(135deg,#6366f1,#8b5cf6);color:#fff;border:none;border-radius:10px;padding:12px;font-size:15px;font-weight:700;cursor:pointer;display:flex;align-items:center;justify-content:center;gap:8px;transition:opacity .2s;">
                <i class="fa-solid fa-user-plus"></i> Register Person
            </button>
        </form>
    </div>

    <!-- RIGHT: Registered Persons List -->
    <div>
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px;">
            <h2 style="margin:0;font-size:1.1rem;font-weight:700;color:#fff;">
                <i class="fa-solid fa-users" style="color:#8b5cf6;"></i> Registered Persons
                <span id="persons-count" style="background:#8b5cf6;color:#fff;border-radius:999px;padding:2px 10px;font-size:12px;margin-left:8px;">0</span>
            </h2>
            <button onclick="loadPersons()"
                style="background:rgba(255,255,255,.07);border:1px solid rgba(255,255,255,.12);color:#e5e7eb;border-radius:8px;padding:8px 14px;font-size:13px;cursor:pointer;">
                <i class="fa-solid fa-rotate"></i> Refresh
            </button>
        </div>

        <!-- Search Bar -->
        <div style="position:relative;margin-bottom:16px;">
            <i class="fa-solid fa-magnifying-glass" style="position:absolute;left:12px;top:50%;transform:translateY(-50%);color:#6b7280;"></i>
            <input type="text" id="search-persons" placeholder="Search by name or ID..."
                oninput="filterPersons()"
                style="width:100%;background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.1);border-radius:8px;padding:10px 14px 10px 38px;color:#fff;font-size:14px;box-sizing:border-box;outline:none;">
        </div>

        <!-- Persons Grid -->
        <div id="persons-grid" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:14px;">
            <div id="persons-loading" style="grid-column:1/-1;text-align:center;padding:40px;opacity:.5;">
                <i class="fa-solid fa-spinner fa-spin" style="font-size:1.5rem;"></i>
                <p style="margin-top:10px;">Loading persons...</p>
            </div>
        </div>
    </div>
</section>

<style>
.person-card {
    background: rgba(255,255,255,.04);
    border: 1px solid rgba(255,255,255,.09);
    border-radius: 12px;
    padding: 16px;
    text-align: center;
    transition: border-color .2s, box-shadow .2s;
    position: relative;
}
.person-card:hover {
    border-color: rgba(139,92,246,.5);
    box-shadow: 0 0 16px rgba(139,92,246,.1);
}
.person-avatar {
    width: 80px;
    height: 80px;
    border-radius: 50%;
    object-fit: cover;
    border: 3px solid rgba(139,92,246,.4);
    margin: 0 auto 10px;
    display: block;
    background: rgba(255,255,255,.05);
}
.person-id-badge {
    font-size: 10px;
    font-weight: 700;
    letter-spacing: .08em;
    color: #a5b4fc;
    text-transform: uppercase;
    margin-bottom: 4px;
}
.person-name {
    font-size: 14px;
    font-weight: 700;
    color: #fff;
    margin: 0 0 4px;
}
.person-status-badge {
    font-size: 10px;
    font-weight: 700;
    padding: 2px 8px;
    border-radius: 999px;
    background: rgba(34,197,94,.15);
    color: #4ade80;
    border: 1px solid rgba(34,197,94,.3);
    display: inline-block;
    margin-bottom: 10px;
}
.person-status-inactive {
    background: rgba(107,114,128,.15);
    color: #9ca3af;
    border-color: rgba(107,114,128,.3);
}
.btn-delete-person {
    position: absolute;
    top: 10px;
    right: 10px;
    background: rgba(239,68,68,.15);
    border: 1px solid rgba(239,68,68,.3);
    color: #f87171;
    border-radius: 6px;
    padding: 4px 8px;
    font-size: 12px;
    cursor: pointer;
    transition: background .15s;
}
.btn-delete-person:hover {
    background: rgba(239,68,68,.3);
}
</style>

<script>
const CSRF_FACE = document.querySelector('meta[name="csrf-token"]')?.content || '';
let allPersons = [];

document.addEventListener('DOMContentLoaded', () => {
    loadPersons();
    startClock();
});

// ─── Image Preview ─────────────────────────────────────────────────────────────
function previewImage(event) {
    const file = event.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = e => {
        document.getElementById('upload-placeholder').style.display = 'none';
        const img = document.getElementById('image-preview');
        img.src  = e.target.result;
        img.style.display = 'block';
    };
    reader.readAsDataURL(file);
}

function handleDrop(event) {
    event.preventDefault();
    document.getElementById('upload-zone').style.borderColor = 'rgba(99,102,241,.4)';
    document.getElementById('upload-zone').style.background  = '';
    const file = event.dataTransfer.files[0];
    if (!file || !file.type.startsWith('image/')) return;
    const dt = new DataTransfer();
    dt.items.add(file);
    document.getElementById('image-input').files = dt.files;
    previewImage({ target: { files: [file] } });
}

// ─── Submit Registration ────────────────────────────────────────────────────────
async function submitFaceRegistration(e) {
    e.preventDefault();

    const errEl  = document.getElementById('form-error');
    const succEl = document.getElementById('form-success');
    const btn    = document.getElementById('btn-register');
    errEl.style.display  = 'none';
    succEl.style.display = 'none';

    const imageFile = document.getElementById('image-input').files[0];
    if (!imageFile) {
        errEl.textContent = 'Please select a photo.';
        errEl.style.display = 'block';
        return;
    }

    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Registering...';

    const formData = new FormData();
    formData.append('image',     imageFile);
    formData.append('person_id', document.getElementById('person-id').value);
    formData.append('name',      document.getElementById('person-name').value);
    formData.append('_token',    CSRF_FACE);

    try {
        const res  = await fetch('/ajax/face/register', {
            method:  'POST',
            headers: { 'Accept': 'application/json', 'X-CSRF-TOKEN': CSRF_FACE },
            body:    formData
        });
        const data = await res.json();

        if (res.ok && (data.success || data.person_id || data.message === undefined || !data.error)) {
            succEl.textContent = `Person registered successfully! ID: ${document.getElementById('person-id').value}`;
            succEl.style.display = 'block';
            document.getElementById('face-register-form').reset();
            document.getElementById('upload-placeholder').style.display = 'block';
            document.getElementById('image-preview').style.display      = 'none';
            loadPersons();
        } else {
            errEl.textContent = data.message || data.detail || data.error || 'Registration failed.';
            errEl.style.display = 'block';
        }
    } catch (err) {
        errEl.textContent = 'Connection error. Is FastAPI running?';
        errEl.style.display = 'block';
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="fa-solid fa-user-plus"></i> Register Person';
    }
}

// ─── Load Persons ───────────────────────────────────────────────────────────────
async function loadPersons() {
    try {
        const res  = await fetch('/ajax/face/persons', { headers: { 'Accept': 'application/json' } });
        const data = await res.json();
        allPersons = data.persons || [];
        document.getElementById('persons-count').textContent = allPersons.length;
        renderPersons(allPersons);
    } catch (err) {
        console.error('loadPersons error:', err);
        document.getElementById('persons-grid').innerHTML =
            '<div style="grid-column:1/-1;text-align:center;padding:40px;opacity:.5;color:#f87171;">Failed to load persons. Is FastAPI running?</div>';
    }
}

function filterPersons() {
    const q = document.getElementById('search-persons').value.toLowerCase();
    const filtered = q
        ? allPersons.filter(p => (p.name || '').toLowerCase().includes(q) || (p.person_id || '').toLowerCase().includes(q))
        : allPersons;
    renderPersons(filtered);
}

function renderPersons(persons) {
    const grid = document.getElementById('persons-grid');
    const loading = document.getElementById('persons-loading');
    if (loading) loading.remove();
    grid.innerHTML = '';

    if (persons.length === 0) {
        grid.innerHTML = `<div style="grid-column:1/-1;text-align:center;padding:40px;opacity:.5;">
            <i class="fa-solid fa-user-slash" style="font-size:2rem;"></i>
            <p style="margin-top:12px;">No registered persons found.</p>
        </div>`;
        return;
    }

    persons.forEach(p => {
        const card = document.createElement('div');
        card.className = 'person-card';
        card.setAttribute('data-person-id', p.person_id);

        const statusLabel = (p.status || 'active').toLowerCase();
        const statusClass = statusLabel === 'active' ? '' : 'person-status-inactive';
        const createdAt   = p.created_at ? new Date(p.created_at).toLocaleDateString() : '--';

        card.innerHTML = `
            <button class="btn-delete-person" onclick="deletePerson('${escHTML(p.person_id)}')" title="Delete">
                <i class="fa-solid fa-trash-can"></i>
            </button>
            <div style="width:80px;height:80px;border-radius:50%;background:linear-gradient(135deg,#6366f1,#8b5cf6);margin:0 auto 10px;display:flex;align-items:center;justify-content:center;">
                <i class="fa-solid fa-user" style="font-size:1.8rem;color:rgba(255,255,255,.8);"></i>
            </div>
            <p class="person-id-badge">${escHTML(p.person_id)}</p>
            <p class="person-name">${escHTML(p.name || 'Unknown')}</p>
            <span class="person-status-badge ${statusClass}">${statusLabel.toUpperCase()}</span>
            <p style="font-size:11px;color:#4b5563;margin:0;">Registered: ${createdAt}</p>
        `;
        grid.appendChild(card);
    });
}

// ─── Delete Person ─────────────────────────────────────────────────────────────
async function deletePerson(personId) {
    if (!confirm(`Delete person "${personId}"? This cannot be undone.`)) return;
    try {
        const res  = await fetch(`/ajax/face/${encodeURIComponent(personId)}`, {
            method:  'DELETE',
            headers: { 'Accept': 'application/json', 'X-CSRF-TOKEN': CSRF_FACE }
        });
        const data = await res.json();
        if (res.ok) {
            showFaceToast('Person deleted successfully.', 'success');
            loadPersons();
        } else {
            showFaceToast(data.message || data.detail || 'Failed to delete.', 'error');
        }
    } catch (err) {
        showFaceToast('Connection error.', 'error');
    }
}

// ─── Toast ─────────────────────────────────────────────────────────────────────
function showFaceToast(msg, type = 'success') {
    let c = document.getElementById('toast-face');
    if (!c) {
        c = document.createElement('div');
        c.id = 'toast-face';
        c.style.cssText = 'position:fixed;bottom:24px;right:24px;z-index:9999;display:flex;flex-direction:column;gap:8px;';
        document.body.appendChild(c);
    }
    const t = document.createElement('div');
    t.style.cssText = `background:${type === 'success' ? '#166534' : '#7f1d1d'};color:#fff;padding:12px 20px;border-radius:10px;font-size:14px;font-weight:600;opacity:0;transition:opacity .3s;box-shadow:0 4px 20px rgba(0,0,0,.4);`;
    t.textContent = msg;
    c.appendChild(t);
    setTimeout(() => t.style.opacity = '1', 20);
    setTimeout(() => { t.style.opacity = '0'; setTimeout(() => t.remove(), 400); }, 4000);
}

function escHTML(str) {
    if (!str) return '';
    return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

// ─── Clock ─────────────────────────────────────────────────────────────────────
function startClock() {
    function tick() {
        const now = new Date();
        const day = String(now.getDate()).padStart(2,'0');
        const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
        let h = now.getHours();
        const ampm = h >= 12 ? 'PM' : 'AM';
        h = h % 12 || 12;
        const m = String(now.getMinutes()).padStart(2,'0');
        const s = String(now.getSeconds()).padStart(2,'0');
        const dateEl = document.getElementById('current-date');
        const timeEl = document.getElementById('current-time');
        if (dateEl) dateEl.textContent = `${day} ${months[now.getMonth()]} ${now.getFullYear()}`;
        if (timeEl) timeEl.textContent = `${String(h).padStart(2,'0')}:${m}:${s} ${ampm}`;
    }
    tick();
    setInterval(tick, 1000);
}
</script>
@endsection
