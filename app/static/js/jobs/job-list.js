/** Jobs list: rows update live; a notice offers a reload when a job not on the page appears. */

import { subscribe } from '../core/events.js';
import { applyJobChange, applyProgress } from './job-live.js';

const notice = document.getElementById('jobs-new');

function shown(id) {
  return document.querySelector(`[data-job-id="${CSS.escape(id)}"]`) !== null;
}

subscribe('job.changed', ({ payload }) => {
  if (shown(payload.id)) applyJobChange(payload);
  else if (notice) notice.hidden = false;
});

subscribe('job.progress', ({ payload }) => {
  if (shown(payload.id)) applyProgress(payload);
});
