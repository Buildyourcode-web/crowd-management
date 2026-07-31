import React, { useRef, useEffect } from 'react';

/**
 * Summary stat card – replaces x-summary-card Blade component.
 * Uses the same animateValue counter logic from dashboard.js.
 */
export default function SummaryCard({ id, title, value = 0, icon, colorClass }) {
  const valRef    = useRef(null);
  const prevRef   = useRef(0);
  const rafRef    = useRef(null);

  useEffect(() => {
    const endVal   = value;
    const startVal = prevRef.current;
    if (startVal === endVal) {
      if (valRef.current) valRef.current.textContent = endVal.toLocaleString();
      return;
    }
    prevRef.current = endVal;

    const duration  = 800;
    const startTime = performance.now();

    function step(ts) {
      const progress = Math.min((ts - startTime) / duration, 1);
      const current  = Math.floor(progress * (endVal - startVal) + startVal);
      if (valRef.current) valRef.current.textContent = current.toLocaleString();
      if (progress < 1) {
        rafRef.current = requestAnimationFrame(step);
      } else {
        if (valRef.current) valRef.current.textContent = endVal.toLocaleString();
      }
    }

    rafRef.current = requestAnimationFrame(step);
    return () => rafRef.current && cancelAnimationFrame(rafRef.current);
  }, [value]);

  return (
    <div className="summary-card" id={id}>
      <div className={`summary-card-icon-container ${colorClass}`}>
        <i className={icon}></i>
      </div>
      <div className="summary-card-info">
        <span className="summary-card-title">{title}</span>
        <span
          className="summary-card-value font-numeric"
          ref={valRef}
          data-target-value={value}
        >
          {value.toLocaleString()}
        </span>
      </div>
    </div>
  );
}
