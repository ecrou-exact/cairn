/**
 * How many Claude Code sessions run on this machine, on the menu's Claude entry, on every
 * page (D-050). Refreshed every few seconds and when a session starts or ends.
 */

import { api } from './api.js';
import { subscribe } from './events.js';

const link = document.querySelector('.cn-nav-link[href="/claude"]');

async function refresh() {
  if (!link) return;
  let running = 0;
  try {
    ({ running } = await api('/claude/sessions'));
  } catch {
    return;
  }
  let badge = link.querySelector('.cn-nav-count');
  if (!running) {
    badge?.remove();
    return;
  }
  if (!badge) {
    badge = document.createElement('span');
    badge.className = 'cn-nav-count';
    link.append(badge);
  }
  badge.textContent = String(running);
  badge.title = `${running} Claude session${running > 1 ? 's' : ''} running`;
}

if (link) {
  refresh();
  setInterval(refresh, 10000);
  subscribe('claude.changed', refresh);
}
