/**
 * Claude overview and session band (D-050): every few seconds, the context gauges, tokens
 * and activity follow the transcripts; a session that started or ended shows a notice
 * (the cards are server-rendered: the page reloads to show the new set).
 */

import { api } from '../core/api.js';
import { subscribe } from '../core/events.js';

const EVERY = 5000;
const WORKING = 20; // seconds since the transcript last moved: Claude is working

function tokens(usage) {
  if (!usage.transcript || !usage.window) return 'no turn yet';
  const window = usage.window >= 1e6 ? `${usage.window / 1e6}M` : `${Math.round(usage.window / 1000)}k`;
  return `${Math.round(usage.context_tokens / 1000)}k / ${window}`;
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

async function refresh() {
  const cards = document.querySelectorAll('[data-claude-card]');
  if (!cards.length) return;
  let data;
  try {
    data = await api('/claude/sessions');
  } catch {
    return;
  }
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
  const counter = document.querySelector('[data-claude-count]');
  if (counter) counter.textContent = String(data.running);
  const notice = document.getElementById('claude-changed');
  const shown = [...cards].map((c) => c.dataset.claudeCard).filter((id) => !isEnded(id));
  if (notice && (data.running !== shown.length || shown.some((id) => !seen.has(id)))) notice.hidden = false;
}

function isEnded(id) {
  return document.querySelector(`[data-claude-card="${id}"]`)?.classList.contains('is-ended');
}

refresh();
setInterval(refresh, EVERY);
subscribe('claude.changed', () => {
  const notice = document.getElementById('claude-changed');
  if (notice) notice.hidden = false;
});
