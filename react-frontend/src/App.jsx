import React, { Suspense, lazy } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';

// Lazy-load all pages for code splitting
const Overview         = lazy(() => import('./pages/Overview'));
const Metrics          = lazy(() => import('./pages/Metrics'));
const Zones            = lazy(() => import('./pages/Zones'));
const Traffic          = lazy(() => import('./pages/Traffic'));
const Cameras          = lazy(() => import('./pages/Cameras'));
const FaceRegistration = lazy(() => import('./pages/FaceRegistration'));

function PageLoader() {
  return (
    <div style={{ display:'flex', justifyContent:'center', alignItems:'center', height:'100vh', background:'var(--bg-primary, #0f172a)', color:'#94a3b8', flexDirection:'column', gap:'16px' }}>
      <i className="fa-solid fa-spinner fa-spin" style={{ fontSize:'32px', color:'#3b82f6' }}></i>
      <p style={{ margin:0, fontSize:'14px', fontWeight:500 }}>Loading...</p>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Suspense fallback={<PageLoader />}>
        <Routes>
          {/* Root → redirect to dashboard */}
          <Route path="/" element={<Navigate to="/dashboard" replace />} />

          {/* Main pages – same URL structure as Laravel routes */}
          <Route path="/dashboard"         element={<Overview />} />
          <Route path="/metrics"           element={<Metrics />} />
          <Route path="/zones"             element={<Zones />} />
          <Route path="/traffic"           element={<Traffic />} />
          <Route path="/cameras"           element={<Cameras />} />
          <Route path="/face-registration" element={<FaceRegistration />} />

          {/* Catch-all → back to dashboard */}
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </Suspense>
    </BrowserRouter>
  );
}
