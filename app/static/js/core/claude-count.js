/**
 * How many Claude Code sessions run on this machine, on the menu's Claude entry, on every
 * page (D-050), with the account's usage while one runs (D-056). Refreshed every few seconds and when a session starts or ends.
 */

import { api } from './api.js';
import { limitNode } from './claude-limits.js';
import { subscribe } from './events.js';

const link = document.querySelector('.cn-nav-link[href="/claude"]');

/** In the header, next to the Claude button: the same numbers, on every page. */
function paintHeader(limits) {
  const box = document.querySelector('[data-claude-header-limits]');
  if (!box) return;
  box.hidden = !limits.windows.length;
  box.replaceChildren(...limits.windows.map((window) => limitNode(window, limits.at)));
}

/** Under the menu's Claude entry while a Claude runs: the usage of the account. */
function paintLimits(limits) {
  let line = document.querySelector('.cn-nav-limits');
  if (!limits.windows.length) {
    line?.remove();
    return;
  }
  if (!line) {
    line = document.createElement('p');
    line.className = 'cn-nav-limits';
    line.setAttribute('aria-label', 'Claude usage of your account');
    link.after(line);
  }
  line.replaceChildren(...limits.windows.map((window) => limitNode(window, limits.at, 'bar')));
}

async function refresh() {
  if (!link) return;
  let running = 0;
  let limits = { windows: [] };
  try {
    ({ running, limits } = await api('/claude/sessions'));
  } catch {
    return;
  }
  paintHeader(limits);
  paintLimits(running ? limits : { windows: [] });
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
