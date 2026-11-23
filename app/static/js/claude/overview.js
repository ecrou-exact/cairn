/**
 * Claude overview and session band (D-050): every few seconds, the context gauges, tokens,
 * activity and last steps follow the transcripts, and running instances their ports and log;
 * a session that started or ended shows a notice (the cards are server-rendered: the page
 * reloads to show the new set).
 */

import { api } from '../core/api.js';
import { limitNode } from '../core/claude-limits.js';
import { subscribe } from '../core/events.js';

const EVERY = 5000;
const WORKING = 20; // seconds since the transcript last moved: Claude is working

function tokens(usage) {
  if (!usage.transcript || !usage.window) return 'no turn yet';
  const window = usage.window >= 1e6 ? `${usage.window / 1e6}M` : `${Math.round(usage.window / 1000)}k`;
  return `${Math.round(usage.context_tokens / 1000)}k / ${window}`;
}

function icon(name) {
  const node = document.createElement('i');
  node.className = `fa-solid ${name || 'fa-gear'}`;
  node.setAttribute('aria-hidden', 'true');
  return node;
}

function clock(at) {
  const time = document.createElement('time');
  if (!at) return time;
  const date = new Date(at);
  if (Number.isNaN(date.getTime())) return time;
  time.dateTime = at;
  time.textContent = date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  return time;
}

function label(text) {
  const span = document.createElement('span');
  span.textContent = text;
  return span;
}

/** What Claude does now, and the last steps (newest first). */
function paintSteps(card, usage) {
  const now = card.querySelector('[data-claude-now]');
  if (now) {
    now.hidden = !usage.now;
    now.replaceChildren(icon(usage.now_icon), document.createTextNode(' '), label(usage.now || ''));
  }
  const steps = card.querySelector('[data-claude-steps]');
  const list = steps?.querySelector('ol');
  if (!list) return;
  const events = usage.events || [];
  steps.hidden = !events.length;
  list.replaceChildren(
    ...events
      .slice()
      .reverse()
      .map((event) => {
        const item = document.createElement('li');
        item.className = `is-${event.who}`;
        item.append(icon(event.icon), document.createTextNode(' '), label(event.label), document.createTextNode(' '), clock(event.at));
        return item;
      }),
  );
}

function paintInstance(card, session) {
  const ports = card.querySelector('[data-instance-ports]');
  if (ports) {
    const links = session.ports.map((port) => {
      const link = document.createElement('a');
      link.className = 'cn-port';
      link.href = `http://localhost:${port}/`;
      link.target = '_blank';
      link.rel = 'noopener noreferrer';
      link.append(icon('fa-arrow-up-right-from-square'), document.createTextNode(` localhost:${port}`));
      return link;
    });
    if (!links.length) {
      const none = label('not listening yet');
      none.className = 'cn-muted';
      links.push(none);
    }
    ports.replaceChildren(...links);
  }
  const log = card.querySelector('[data-instance-log]');
  const text = session.log.join('\n');
  if (log && log.dataset.shown !== text) {
    log.dataset.shown = text;
    log.content = text;
  }
}

function paint(card, usage, running) {
  const pct = Math.min(usage.percent || 0, 100);
  const gauge = card.querySelector('[data-gauge]');
  if (gauge) {
    gauge.classList.toggle('is-high', pct >= 80);
    gauge.classList.toggle('is-mid', pct >= 50 && pct < 80);
    gauge.setAttribute('aria-label', `${pct}% of the context window used`);
    gauge.querySelector('[data-gauge-fill]')?.setAttribute('stroke-dasharray', `${pct.toFixed(1)} 100`);
    const value = gauge.querySelector('[data-gauge-value]');
    if (value) {
      const small = document.createElement('small');
      small.textContent = '%';
      value.replaceChildren(document.createTextNode(String(Math.floor(pct))), small);
    }
  }
  paintSteps(card, usage);
  const count = card.querySelector('[data-claude-tokens]');
  if (count) count.textContent = tokens(usage);
  const state = card.querySelector('[data-claude-state]');
  if (state && running) {
    const idle = usage.last_activity ? Date.now() / 1000 - usage.last_activity : Infinity;
    const working = idle < WORKING;
    state.dataset.activity = working ? 'working' : 'waiting';
    state.textContent = working ? 'working' : 'waiting for you';
  }
}

function paintLimits(limits) {
  if (!limits.windows.length) return;
  for (const box of document.querySelectorAll('[data-claude-limits]')) {
    box.replaceChildren(...limits.windows.map((w) => limitNode(w, limits.at)));
  }
}

async function refresh() {
  const cards = document.querySelectorAll('[data-claude-card]');
  if (!cards.length && !document.querySelector('[data-instance-card]')) return;
  let data;
  try {
    data = await api('/claude/sessions');
  } catch {
    return;
  }
  paintLimits(data.limits);
  const seen = new Set();
  for (const s of data.sessions) {
    seen.add(s.id);
    const card = document.querySelector(`[data-claude-card="${s.id}"]`);
    if (card) paint(card, s.usage, s.running);
  }
  for (const s of data.outside) {
    const id = `pid-${s.pid}`;
    seen.add(id);
    const card = document.querySelector(`[data-claude-card="${id}"]`);
    if (card) paint(card, s.usage, true);
  }
  const live = new Set();
  for (const s of data.instances) {
    live.add(s.id);
    const card = document.querySelector(`[data-instance-card="${s.id}"]`);
    if (card) paintInstance(card, s);
  }
  const shownInstances = [...document.querySelectorAll('[data-instance-card]')].map((c) => c.dataset.instanceCard);
  const counter = document.querySelector('[data-claude-count]');
  if (counter) counter.textContent = String(data.running);
  const notice = document.getElementById('claude-changed');
  const shown = [...cards].map((c) => c.dataset.claudeCard).filter((id) => !isEnded(id));
  const changed =
    data.running !== shown.length ||
    shown.some((id) => !seen.has(id)) ||
    shownInstances.some((id) => !live.has(id));
  if (notice && changed) notice.hidden = false;
}

function isEnded(id) {
  return document.querySelector(`[data-claude-card="${id}"]`)?.classList.contains('is-ended');
}

refresh();
setInterval(refresh, EVERY);
for (const name of ['claude.changed', 'instance.changed']) {
  subscribe(name, () => {
    const notice = document.getElementById('claude-changed');
    if (notice) notice.hidden = false;
  });
}
