import React, { useState, useEffect, useRef, useCallback } from 'react';
import DashboardLayout from '../components/layout/DashboardLayout';
import { registerFace, fetchPersons, deletePerson } from '../services/api';

function escHTML(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g,'&amp;').replace(/</g,'&lt;')
    .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function Toast({ messages }) {
  return (
    <div style={{ position:'fixed', bottom:'24px', right:'24px', zIndex:9999, display:'flex', flexDirection:'column', gap:'8px' }}>
      {messages.map(m => (
        <div key={m.id} style={{ background: m.type === 'success' ? '#166534' : '#7f1d1d', color:'#fff', padding:'12px 20px', borderRadius:'10px', fontSize:'14px', fontWeight:600, boxShadow:'0 4px 20px rgba(0,0,0,.4)' }}>
          {m.text}
        </div>
      ))}
    </div>
  );
}

function PersonCard({ person, onDelete }) {
  const statusLabel = (person.status || 'active').toLowerCase();
  const isActive    = statusLabel === 'active';
  const createdAt   = person.created_at ? new Date(person.created_at).toLocaleDateString() : '--';

  return (
    <div className="person-card">
      <button className="btn-delete-person" onClick={() => onDelete(person.person_id)} title="Delete">
        <i className="fa-solid fa-trash-can"></i>
      </button>
      <div style={{ width:'80px', height:'80px', borderRadius:'50%', background:'linear-gradient(135deg,#6366f1,#8b5cf6)', margin:'0 auto 10px', display:'flex', alignItems:'center', justifyContent:'center' }}>
        <i className="fa-solid fa-user" style={{ fontSize:'1.8rem', color:'rgba(255,255,255,.8)' }}></i>
      </div>
      <p className="person-id-badge">{person.person_id}</p>
      <p className="person-name">{person.name || 'Unknown'}</p>
      <span className={`person-status-badge${isActive ? '' : ' person-status-inactive'}`}>
        {statusLabel.toUpperCase()}
      </span>
      <p style={{ fontSize:'11px', color:'#4b5563', margin:0 }}>Registered: {createdAt}</p>
    </div>
  );
}

/**
 * Face Registration page – pixel-identical to dashboard/face-registration.blade.php
 * All JS logic (submit, preview, drag-drop, search, toast) ported to React hooks.
 */
export default function FaceRegistration() {
  const [persons, setPersons]         = useState([]);
  const [filtered, setFiltered]       = useState([]);
  const [search, setSearch]           = useState('');
  const [loading, setLoading]         = useState(true);
  const [submitting, setSubmitting]   = useState(false);
  const [previewUrl, setPreviewUrl]   = useState(null);
  const [formError, setFormError]     = useState('');
  const [formSuccess, setFormSuccess] = useState('');
  const [toasts, setToasts]           = useState([]);
  const fileRef   = useRef(null);
  const personId  = useRef(null);
  const personName = useRef(null);

  // ── Load persons ─────────────────────────────────────────────────────────
  const loadPersons = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchPersons();
      const list = data.persons || [];
      setPersons(list);
      setFiltered(list);
    } catch {
      addToast('Failed to load persons. Is FastAPI running?', 'error');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadPersons(); }, [loadPersons]);

  // ── Search filter ─────────────────────────────────────────────────────────
  useEffect(() => {
    const q = search.toLowerCase();
    setFiltered(q
      ? persons.filter(p => (p.name||'').toLowerCase().includes(q) || (p.person_id||'').toLowerCase().includes(q))
      : persons
    );
  }, [search, persons]);

  // ── Image preview ─────────────────────────────────────────────────────────
  function handleFileChange(file) {
    if (!file) return;
    const reader = new FileReader();
    reader.onload = e => setPreviewUrl(e.target.result);
    reader.readAsDataURL(file);
  }

  function handleDrop(e) {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (!file || !file.type.startsWith('image/')) return;
    const dt = new DataTransfer();
    dt.items.add(file);
    fileRef.current.files = dt.files;
    handleFileChange(file);
  }

  // ── Submit ────────────────────────────────────────────────────────────────
  async function handleSubmit(e) {
    e.preventDefault();
    setFormError(''); setFormSuccess('');

    const file = fileRef.current?.files[0];
    if (!file) { setFormError('Please select a photo.'); return; }

    setSubmitting(true);
    const fd = new FormData();
    fd.append('image',     file);
    fd.append('person_id', personId.current?.value || '');
    fd.append('name',      personName.current?.value || '');

    try {
      const data = await registerFace(fd);
      if (data.success || data.person_id || (!data.error && !data.detail)) {
        setFormSuccess(`Person registered successfully! ID: ${personId.current?.value}`);
        e.target.reset();
        setPreviewUrl(null);
        loadPersons();
      } else {
        setFormError(data.message || data.detail || data.error || 'Registration failed.');
      }
    } catch {
      setFormError('Connection error. Is FastAPI running?');
    } finally {
      setSubmitting(false);
    }
  }

  // ── Delete ────────────────────────────────────────────────────────────────
  async function handleDelete(pid) {
    if (!window.confirm(`Delete person "${pid}"? This cannot be undone.`)) return;
    try {
      await deletePerson(pid);
      addToast('Person deleted successfully.', 'success');
      loadPersons();
    } catch {
      addToast('Failed to delete.', 'error');
    }
  }

  // ── Toast ─────────────────────────────────────────────────────────────────
  function addToast(text, type = 'success') {
    const id = Date.now();
    setToasts(t => [...t, { id, text, type }]);
    setTimeout(() => setToasts(t => t.filter(x => x.id !== id)), 4000);
  }

  const inputStyle = { width:'100%', background:'rgba(255,255,255,.06)', border:'1px solid rgba(255,255,255,.12)', borderRadius:'8px', padding:'10px 14px', color:'#fff', fontSize:'14px', boxSizing:'border-box', outline:'none' };
  const labelStyle = { display:'block', fontSize:'13px', color:'#9ca3af', marginBottom:'6px', fontWeight:600 };

  return (
    <DashboardLayout pageTitle="Face Registration">
      <style>{`
        .person-card { background:rgba(255,255,255,.04); border:1px solid rgba(255,255,255,.09); border-radius:12px; padding:16px; text-align:center; transition:border-color .2s, box-shadow .2s; position:relative; }
        .person-card:hover { border-color:rgba(139,92,246,.5); box-shadow:0 0 16px rgba(139,92,246,.1); }
        .person-id-badge { font-size:10px; font-weight:700; letter-spacing:.08em; color:#a5b4fc; text-transform:uppercase; margin-bottom:4px; }
        .person-name { font-size:14px; font-weight:700; color:#fff; margin:0 0 4px; }
        .person-status-badge { font-size:10px; font-weight:700; padding:2px 8px; border-radius:999px; background:rgba(34,197,94,.15); color:#4ade80; border:1px solid rgba(34,197,94,.3); display:inline-block; margin-bottom:10px; }
        .person-status-inactive { background:rgba(107,114,128,.15); color:#9ca3af; border-color:rgba(107,114,128,.3); }
        .btn-delete-person { position:absolute; top:10px; right:10px; background:rgba(239,68,68,.15); border:1px solid rgba(239,68,68,.3); color:#f87171; border-radius:6px; padding:4px 8px; font-size:12px; cursor:pointer; transition:background .15s; }
        .btn-delete-person:hover { background:rgba(239,68,68,.3); }
      `}</style>

      <section style={{ padding:'24px', maxWidth:'1400px', margin:'0 auto', display:'grid', gridTemplateColumns:'380px 1fr', gap:'24px', alignItems:'start' }}>

        {/* ── LEFT: Registration form ───────────────────────────────────── */}
        <div style={{ background:'rgba(255,255,255,.04)', border:'1px solid rgba(255,255,255,.1)', borderRadius:'16px', padding:'28px', position:'sticky', top:'24px' }}>
          <h2 style={{ margin:'0 0 20px', fontSize:'1.1rem', fontWeight:700, color:'#fff' }}>
            <i className="fa-solid fa-user-plus" style={{ color:'#6366f1' }}></i> Register Person
          </h2>

          <form id="face-register-form" onSubmit={handleSubmit}>
            {/* Image upload zone */}
            <div
              id="upload-zone"
              style={{ border:'2px dashed rgba(99,102,241,.4)', borderRadius:'12px', padding:'24px', textAlign:'center', cursor:'pointer', marginBottom:'20px', transition:'border-color .2s, background .2s' }}
              onClick={() => fileRef.current?.click()}
              onDragOver={e => { e.preventDefault(); e.currentTarget.style.borderColor='#6366f1'; e.currentTarget.style.background='rgba(99,102,241,.06)'; }}
              onDragLeave={e => { e.currentTarget.style.borderColor='rgba(99,102,241,.4)'; e.currentTarget.style.background=''; }}
              onDrop={handleDrop}
            >
              {!previewUrl ? (
                <div id="upload-placeholder">
                  <i className="fa-solid fa-cloud-arrow-up" style={{ fontSize:'2rem', color:'#6366f1', marginBottom:'10px', display:'block' }}></i>
                  <p style={{ margin:0, color:'#9ca3af', fontSize:'14px' }}>Click or drag &amp; drop photo</p>
                  <p style={{ margin:'4px 0 0', color:'#6b7280', fontSize:'12px' }}>JPG, PNG, WebP — max 5 MB</p>
                </div>
              ) : (
                <img src={previewUrl} alt="Preview" style={{ maxWidth:'100%', maxHeight:'200px', borderRadius:'8px', objectFit:'cover' }} />
              )}
            </div>
            <input type="file" ref={fileRef} accept="image/*" style={{ display:'none' }}
              onChange={e => handleFileChange(e.target.files[0])} />

            {/* Person ID */}
            <div style={{ marginBottom:'14px' }}>
              <label style={labelStyle}>Person ID <span style={{ color:'#f87171' }}>*</span></label>
              <input type="text" ref={personId} name="person_id" required maxLength={50}
                placeholder="e.g. P001, WL-2026-001" style={inputStyle} />
            </div>

            {/* Name */}
            <div style={{ marginBottom:'20px' }}>
              <label style={labelStyle}>Full Name <span style={{ color:'#f87171' }}>*</span></label>
              <input type="text" ref={personName} name="name" required maxLength={100}
                placeholder="e.g. John Doe" style={inputStyle} />
            </div>

            {/* Messages */}
            {formError && (
              <div style={{ display:'block', background:'rgba(239,68,68,.12)', border:'1px solid rgba(239,68,68,.35)', borderRadius:'8px', padding:'10px 14px', color:'#f87171', fontSize:'13px', marginBottom:'14px' }}>
                {formError}
              </div>
            )}
            {formSuccess && (
              <div style={{ display:'block', background:'rgba(34,197,94,.12)', border:'1px solid rgba(34,197,94,.35)', borderRadius:'8px', padding:'10px 14px', color:'#4ade80', fontSize:'13px', marginBottom:'14px' }}>
                {formSuccess}
              </div>
            )}

            <button type="submit" disabled={submitting}
              style={{ width:'100%', background:'linear-gradient(135deg,#6366f1,#8b5cf6)', color:'#fff', border:'none', borderRadius:'10px', padding:'12px', fontSize:'15px', fontWeight:700, cursor:'pointer', display:'flex', alignItems:'center', justifyContent:'center', gap:'8px', opacity: submitting ? 0.7 : 1 }}>
              {submitting
                ? <><i className="fa-solid fa-spinner fa-spin"></i> Registering...</>
                : <><i className="fa-solid fa-user-plus"></i> Register Person</>
              }
            </button>
          </form>
        </div>

        {/* ── RIGHT: Persons list ───────────────────────────────────────── */}
        <div>
          <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', marginBottom:'16px' }}>
            <h2 style={{ margin:0, fontSize:'1.1rem', fontWeight:700, color:'#fff' }}>
              <i className="fa-solid fa-users" style={{ color:'#8b5cf6' }}></i> Registered Persons
              <span style={{ background:'#8b5cf6', color:'#fff', borderRadius:'999px', padding:'2px 10px', fontSize:'12px', marginLeft:'8px' }}>
                {persons.length}
              </span>
            </h2>
            <button onClick={loadPersons}
              style={{ background:'rgba(255,255,255,.07)', border:'1px solid rgba(255,255,255,.12)', color:'#e5e7eb', borderRadius:'8px', padding:'8px 14px', fontSize:'13px', cursor:'pointer' }}>
              <i className="fa-solid fa-rotate"></i> Refresh
            </button>
          </div>

          {/* Search */}
          <div style={{ position:'relative', marginBottom:'16px' }}>
            <i className="fa-solid fa-magnifying-glass" style={{ position:'absolute', left:'12px', top:'50%', transform:'translateY(-50%)', color:'#6b7280' }}></i>
            <input type="text" placeholder="Search by name or ID..."
              value={search} onChange={e => setSearch(e.target.value)}
              style={{ width:'100%', background:'rgba(255,255,255,.05)', border:'1px solid rgba(255,255,255,.1)', borderRadius:'8px', padding:'10px 14px 10px 38px', color:'#fff', fontSize:'14px', boxSizing:'border-box', outline:'none' }} />
          </div>

          {/* Grid */}
          <div id="persons-grid" style={{ display:'grid', gridTemplateColumns:'repeat(auto-fill,minmax(220px,1fr))', gap:'14px' }}>
            {loading && (
              <div style={{ gridColumn:'1/-1', textAlign:'center', padding:'40px', opacity:.5, color:'#fff' }}>
                <i className="fa-solid fa-spinner fa-spin" style={{ fontSize:'1.5rem' }}></i>
                <p style={{ marginTop:'10px' }}>Loading persons...</p>
              </div>
            )}

            {!loading && filtered.length === 0 && (
              <div style={{ gridColumn:'1/-1', textAlign:'center', padding:'40px', opacity:.5, color:'#fff' }}>
                <i className="fa-solid fa-user-slash" style={{ fontSize:'2rem' }}></i>
                <p style={{ marginTop:'12px' }}>No registered persons found.</p>
              </div>
            )}

            {!loading && filtered.map(p => (
              <PersonCard key={p.person_id} person={p} onDelete={handleDelete} />
            ))}
          </div>
        </div>
      </section>

      <Toast messages={toasts} />
    </DashboardLayout>
  );
}
