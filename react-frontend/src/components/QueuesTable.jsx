import React from 'react';

function QueueDot({ movement }) {
  const m = (movement || '').toLowerCase().trim();
  if (m === 'very slow' || m === 'veryslow') return { dotClass: 'dot-orange', label: 'Very Slow' };
  if (m === 'slow')                           return { dotClass: 'dot-yellow', label: 'Slow' };
  if (m === 'stopped' || m === 'blocked')     return { dotClass: 'dot-red',    label: 'Stopped' };
  if (m === 'empty')                          return { dotClass: 'dot-grey',   label: 'Empty' };
  return { dotClass: 'dot-green', label: 'Moving' };
}

/**
 * Queue movement table – mirrors updateQueuesTable() from dashboard.js
 */
export default function QueuesTable({ queues = [] }) {
  return (
    <div className="table-responsive">
      <table className="grid-table" id="queues-table">
        <thead>
          <tr>
            <th scope="col">Queue no.</th>
            <th scope="col">Wait time</th>
            <th scope="col">Movement</th>
          </tr>
        </thead>
        <tbody>
          {queues.length === 0 ? (
            <tr>
              <td colSpan={3} style={{ textAlign: 'center', padding: '20px', color: '#94a3b8' }}>
                No queue data
              </td>
            </tr>
          ) : (
            queues.map((q, i) => {
              const { dotClass, label } = QueueDot({ movement: q.movement });
              return (
                <tr key={q.queue_number || i}>
                  <td>{q.queue_number}</td>
                  <td className="font-numeric">{q.wait_minutes} mins</td>
                  <td>
                    <div className="status-indicator-wrapper" title={label}>
                      <span className={`status-dot ${dotClass}`} aria-hidden="true"></span>
                      <span className="status-label">{label}</span>
                    </div>
                  </td>
                </tr>
              );
            })
          )}
        </tbody>
      </table>
    </div>
  );
}
