/**
 * A project's Instances tab (D-061): says when something started or stopped, in Cairn or
 * outside, and since when each one runs.
 */

import { api } from '../core/api.js';
import { subscribe } from '../core/events.js';

const EVERY = 5000;
const notice = document.getElementById('instances-changed');
let shown = null;

for (const time of document.querySelectorAll('[data-instance-since]')) {
  const date = new Date(Number(time.dataset.instanceSince) * 1000);
  time.dateTime = date.toISOString();
  time.textContent = date.toLocaleString([], { weekday: 'short', hour: '2-digit', minute: '2-digit' });
}

function signature({ instances, outside }) {
  return JSON.stringify([
    instances.map((i) => [i.id, i.running?.id || null, i.ports]),
    outside.map((o) => [o.id, o.ports]),
  ]);
}

async function look() {
  if (document.hidden) return;
  try {
    const now = signature(await api(`/instances?${new URLSearchParams({ project: notice.dataset.project })}`));
    if (shown === null) shown = now;
    else if (now !== shown) notice.hidden = false;
  } catch {
    // Cairn is away: asked again at the next turn
  }
}

if (notice) {
  look();
  setInterval(look, EVERY);
  subscribe('instance.changed', look);
}
