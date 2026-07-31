import React from 'react';

function StatusDot({ status }) {
  const s = (status || '').toLowerCase();
  const dotClass = s === 'normal' ? 'dot-green' : s === 'warning' ? 'dot-yellow' : 'dot-red';
  const label    = s === 'normal' ? 'Normal'    : s === 'warning' ? 'Warning'    : 'Blocked';
  return (
    <div className="status-indicator-wrapper" title={label}>
      <span className={`status-dot ${dotClass}`} aria-hidden="true"></span>
      <span className="status-label">{label}</span>
    </div>
  );
}

/**
 * Gates entry/exit table – mirrors updateGatesTable() from dashboard.js
 */
export default function GatesTable({ gates = [] }) {
  return (
    <div className="table-responsive">
      <table className="grid-table" id="gates-table">
        <thead>
          <tr>
            <th scope="col">Gate no.</th>
            <th scope="col">Entries</th>
            <th scope="col">Exits</th>
            <th scope="col">Status</th>
          </tr>
        </thead>
        <tbody>
          {gates.length === 0 ? (
            <tr>
              <td colSpan={4} style={{ textAlign: 'center', padding: '20px', color: '#94a3b8' }}>
                No gate data
              </td>
            </tr>
          ) : (
            gates.map((gate, i) => (
              <tr key={gate.gate_number || i}>
                <td>{gate.gate_number}</td>
                <td className="font-numeric">{(gate.entries || 0).toLocaleString()}</td>
                <td className="font-numeric">{(gate.exits   || 0).toLocaleString()}</td>
                <td><StatusDot status={gate.status} /></td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
