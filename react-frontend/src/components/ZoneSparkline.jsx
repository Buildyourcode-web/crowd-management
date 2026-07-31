import React, { useRef, useEffect } from 'react';

/**
 * SVG Sparkline – extracted from updateZoneSparkline() in dashboard.js
 * Renders a live cubic-spline line + area chart inside the wave ZoneCard.
 */
export default function ZoneSparkline({ history = [], capacity = 1, statusClass = 'green' }) {
  const svgRef = useRef(null);

  useEffect(() => {
    const svg = svgRef.current;
    if (!svg || history.length === 0) return;

    const width  = 400;
    const height = 100;
    const pad    = 5;
    const ch     = height - pad * 2;
    const maxVal = capacity || 1;

    const points = history.map((val, i) => ({
      x: (i / (history.length - 1)) * width,
      y: height - pad - (val / maxVal) * ch,
    }));

    // Build cubic spline path
    let pathD = `M ${points[0].x.toFixed(1)},${points[0].y.toFixed(1)}`;
    for (let i = 0; i < points.length - 1; i++) {
      const p0  = points[i], p1 = points[i + 1];
      const cpX = p0.x + (p1.x - p0.x) / 2;
      pathD += ` C ${cpX.toFixed(1)},${p0.y.toFixed(1)} ${cpX.toFixed(1)},${p1.y.toFixed(1)} ${p1.x.toFixed(1)},${p1.y.toFixed(1)}`;
    }

    const linePath = svg.querySelector('.sparkline-line-path');
    const areaPath = svg.querySelector('.sparkline-area-path');
    const lastDot  = svg.querySelector('.sparkline-last-dot');
    const glow     = svg.querySelector('.sparkline-last-dot-glow');
    const last     = points[points.length - 1];

    if (linePath) {
      linePath.setAttribute('d', pathD);
      linePath.setAttribute('class', `sparkline-line-path stroke-${statusClass}`);
    }
    if (areaPath) {
      const areaD = `${pathD} L ${last.x.toFixed(1)},${height} L ${points[0].x.toFixed(1)},${height} Z`;
      areaPath.setAttribute('d', areaD);
      areaPath.setAttribute('fill', `url(#area-grad-${statusClass})`);
    }
    if (lastDot) {
      lastDot.setAttribute('cx', last.x.toFixed(1));
      lastDot.setAttribute('cy', last.y.toFixed(1));
      lastDot.setAttribute('class', `sparkline-last-dot fill-${statusClass}`);
    }
    if (glow) {
      glow.setAttribute('cx', last.x.toFixed(1));
      glow.setAttribute('cy', last.y.toFixed(1));
      glow.setAttribute('class', `sparkline-last-dot-glow fill-${statusClass}`);
    }
  }, [history, capacity, statusClass]);

  const tickVals = [
    Math.round(capacity * 0.9),
    Math.round(capacity * 0.68),
    Math.round(capacity * 0.45),
    Math.round(capacity * 0.22),
    0,
  ];

  return (
    <div className="sparkline-container">
      <div className="sparkline-y-ticks">
        {['y-max','y-mid-high','y-mid','y-mid-low','y-min'].map((cls, i) => (
          <span key={cls} className={`tick-label ${cls}`}>{tickVals[i].toLocaleString()}</span>
        ))}
      </div>
      <div className="sparkline-svg-wrapper">
        <svg ref={svgRef} className="sparkline-svg" viewBox="0 0 400 100" preserveAspectRatio="none">
          <defs>
            {['green','yellow','orange','red'].map(c => (
              <linearGradient key={c} id={`area-grad-${c}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={c === 'green' ? '#10b981' : c === 'yellow' ? '#f59e0b' : c === 'orange' ? '#f97316' : '#ef4444'} stopOpacity="0.25" />
                <stop offset="100%" stopColor={c === 'green' ? '#10b981' : c === 'yellow' ? '#f59e0b' : c === 'orange' ? '#f97316' : '#ef4444'} stopOpacity="0" />
              </linearGradient>
            ))}
          </defs>
          {[0,25,50,75,100].map(y => (
            <line key={y} className="grid-line" x1="0" y1={y} x2="400" y2={y} />
          ))}
          <path className="sparkline-area-path" d="" />
          <path className="sparkline-line-path" d="" />
          <circle className="sparkline-last-dot" cx="-10" cy="-10" r="4.5" />
          <circle className="sparkline-last-dot-glow" cx="-10" cy="-10" r="9" />
        </svg>
      </div>
    </div>
  );
}
