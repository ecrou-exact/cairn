/**
 * Job page: the log streams into the viewer, progress moves in place. When the status
 * changes, the page reloads so its actions (cancel, retry), times and result are the
 * server's, not a copy kept in sync by hand.
 */

import '../components/cn-vitrine.js';
import { subscribe } from '../core/events.js';
import { applyJobChange, applyProgress } from './job-live.js';

const panel = document.getElementById('job');
const log = document.getElementById('job-log');
const jobId = panel.dataset.jobId;

subscribe('job', ({ type, payload }) => {
  if (payload.id !== jobId) return;
  if (type === 'job.log') {
    log.write(payload.text);
  } else if (type === 'job.progress') {
    applyProgress(payload);
  } else if (type === 'job.changed') {
    if (payload.status !== panel.dataset.status) window.location.reload();
    else applyJobChange(payload);
  }
});
