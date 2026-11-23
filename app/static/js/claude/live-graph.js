/**
 * What every Claude is doing now, as a graph (D-059). Cairn's server reads the facts and lays
 * the cards out; they follow every few seconds while the page is in view. Click: details;
 * double click on a session: its own graph, with all it did since the last request.
 */

import { Pivotick } from '../../vendor/pivotick/pivotick.es.js';
import { api } from '../core/api.js';
import { subscribe } from '../core/events.js';
import { applyChanges, chip, el, fact, fitCards, icon, placePeek, token } from '../graph/stage.js';

const EVERY = 3000;
const KINDS = {
  session: ['Session', 'terracotta'],
  agent: ['Agent', 'plum'],
  running: ['Running now', 'ochre'],
  background: ['In the background', 'moss'],
  process: ['Process', 'slate'],
  skill: ['Skill', 'sea'],
  file: ['File changed', 'moss'],
  commands: ['Commands', 'slate'],
  reads: ['Read', 'slate'],
  searches: ['Searches', 'slate'],
  web: ['Web', 'sea'],
  server: ['MCP server', 'plum'],
};

const stage = document.querySelector('[data-live-graph]');
const canvas = stage.querySelector('[data-graph-canvas]');
const panel = stage.querySelector('[data-graph-panel]');
const peek = stage.querySelector('[data-graph-peek]');
const session = stage.dataset.session;
let graph = null;
let current = { nodes: [], edges: [] };
let selected = null;
let touched = false; // the owner moved the view: it is no longer framed for them
let busy = false;

const clock = (at) => {
  const date = new Date(at);
  return at && !Number.isNaN(date.getTime()) ? date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : '';
};

function since(at) {
  const seconds = Math.max(0, Math.round((Date.now() - new Date(at).getTime()) / 1000));
  if (!Number.isFinite(seconds)) return '';
  if (seconds < 60) return `${seconds}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)} min`;
  return `${Math.floor(seconds / 3600)} h ${Math.floor((seconds % 3600) / 60)} min`;
}

function card(node) {
  const d = node.getData();
  const [label, color] = KINDS[d.kind];
  const box = el('article', `cn-gcard cn-live-card cn-color-${d.project?.color || color} cn-live-${d.kind}`);
  box.classList.toggle('is-live', d.live);
  box.classList.toggle('is-quiet', !d.live);
  const top = el('div', 'cn-gcard-top');
  const type = el('span', 'cn-gcard-type');
  type.append(icon(`fa-solid ${d.icon}`));
  top.append(type, el('span', 'cn-gcard-project', d.kind === 'session' ? d.project?.name || d.where : d.agent || label));
  if (d.kind === 'session') top.append(el('span', 'cn-gcard-score', `${Math.round(d.context)}%`));
  if (d.live) top.append(el('span', 'cn-live-pulse'));
  const meta = el('div', 'cn-gcard-meta');
  meta.append(el('span', 'cn-live-state', d.state));
  if (d.model) meta.append(el('span', '', d.model));
  if (d.calls) meta.append(chip('', 'fa-solid fa-hammer', String(d.calls)));
  if (d.failed) meta.append(chip('cn-gcard-due is-late', 'fa-solid fa-xmark', String(d.failed)));
  for (const port of d.ports || []) meta.append(chip('cn-gcard-unlocks', 'fa-solid fa-link', `:${port}`));
  box.append(top, el('p', 'cn-gcard-title', d.label), meta);
  if (d.now) {
    const now = el('div', 'cn-gcard-children');
    now.append(icon('fa-solid fa-play'), el('span', 'cn-gcard-next', d.now));
    box.append(now);
  }
  return box;
}

function showPanel(id, d) {
  selected = id;
  peek.hidden = true;
  const [label, color] = KINDS[d.kind];
  const head = el('header', 'cn-gpanel-head');
  const close = el('button', 'cn-icon-button cn-gpanel-close');
  close.type = 'button';
  close.title = 'Close';
  close.append(icon('fa-solid fa-xmark'));
  close.addEventListener('click', hidePanel);
  head.append(chip(`cn-project-chip cn-color-${d.project?.color || color}`, `fa-solid ${d.icon}`, d.project?.name || label), close);
  const facts = el('dl', 'cn-facts');
  facts.append(fact('State', d.state));
  if (d.agent) facts.append(fact('Agent', d.agent));
  if (d.model) facts.append(fact('Model', d.model));
  if (d.kind === 'session') facts.append(fact('Context', `${d.context}%`), fact('Runs', d.where), fact('Folder', d.cwd));
  if (d.path) facts.append(fact('File', d.path));
  if (d.pid) facts.append(fact('Process', d.pid));
  if (d.family) facts.append(fact('Started', `${d.family} other process${d.family > 1 ? 'es' : ''}`));
  if (d.since) facts.append(fact('For', since(d.since)));
  if (d.calls) facts.append(fact('Steps', `${d.calls}${d.kind === 'session' ? ' since your last request' : ''}`));
  const parts = [head, el('h2', 'cn-gpanel-title', d.label), facts];
  if (d.prompt) {
    const asked = el('div', 'cn-gpanel-links');
    asked.append(el('h3', '', 'Your last request'), el('p', 'cn-live-prompt', d.prompt));
    parts.push(asked);
  }
  if (d.items?.length) {
    const steps = el('div', 'cn-gpanel-links');
    const list = el('ul', 'cn-live-steps');
    for (const item of d.items) {
      const li = el('li', `is-${item.state}`);
      li.append(el('span', '', item.label), el('time', '', clock(item.at)));
      list.append(li);
    }
    steps.append(el('h3', '', 'Steps, newest first'), list);
    parts.push(steps);
  }
  const actions = el('div', 'cn-gpanel-actions');
  for (const [href, text, main] of [[d.drill, 'Its own graph', true], [d.url, 'Open its terminal', false]]) {
    if (!href) continue;
    const link = el('a', `btn ${main ? 'btn-primary' : 'btn-outline-secondary'}`, text);
    link.href = href;
    actions.append(link);
  }
  for (const port of d.ports || []) {
    const link = el('a', 'btn btn-outline-secondary', `localhost:${port}`);
    link.href = `http://localhost:${port}/`;
    link.target = '_blank';
    link.rel = 'noopener noreferrer';
    actions.append(link);
  }
  if (actions.children.length) parts.push(actions);
  const scroll = panel.scrollTop;
  panel.replaceChildren(...parts);
  panel.hidden = false;
  panel.scrollTop = scroll;
}

function hidePanel() {
  panel.hidden = true;
  selected = null;
}

function showPeek(event, node) {
  const d = node.getData();
  peek.replaceChildren(
    el('p', 'cn-gpeek-title', d.label),
    el('p', 'cn-gpeek-facts', [KINDS[d.kind][0], d.state, d.since && since(d.since)].filter(Boolean).join(' · ')),
    el('p', 'cn-gpeek-hint', d.drill ? 'Double-click: all it did since your last request' : 'Click for details'),
  );
  peek.hidden = false;
  placePeek(stage, peek, event);
}

function summary() {
  const plural = (n, word) => `${n} ${word}${n === 1 ? '' : 's'}`;
  stage.querySelector('[data-graph-count]').textContent = `${plural(current.sessions, 'session')} · ${current.live} active`;
  stage.querySelector('[data-live-at]').textContent = clock(current.at * 1000);
  stage.querySelector('[data-graph-empty]').hidden = current.nodes.length > 0;
}

const load = () => api(`/claude/live${session ? `?${new URLSearchParams({ session })}` : ''}`);
const fit = (smooth) => { if (graph) fitCards(graph, current.nodes, smooth); };

async function start() {
  current = await load();
  const edge = { curveStyle: 'straight', markerEnd: '' };
  graph = new Pivotick(canvas, { nodes: current.nodes, edges: current.edges }, {
    isDirected: true,
    UI: { mode: 'viewer', tooltip: { enabled: false }, contextMenu: { enabled: false } },
    layout: { type: 'force' }, // every card is pinned
    simulation: { useWorker: false, warmupTicks: 0, cooldownTime: 0 },
    render: {
      defaultNodeStyle: { shape: 'none', html: card, text: '' },
      edgeTypeAccessor: (e) => e.getData()?.kind,
      edgeStyleMap: {
        live: { ...edge, strokeColor: token('--cn-mark'), strokeWidth: 2.4 },
        past: { ...edge, strokeColor: token('--cn-border-strong'), strokeWidth: 1.4 },
      },
    },
    callbacks: {
      onNodeClick: (_event, node) => showPanel(node.id, node.getData()),
      onNodeDbclick: (_event, node) => { if (node.getData().drill) window.location.assign(node.getData().drill); },
      onNodeHoverIn: showPeek,
      onNodeHoverOut: () => { peek.hidden = true; },
      onCanvasClick: hidePanel,
      onCanvasMousemove: (event) => placePeek(stage, peek, event),
    },
  });
  graph.renderer.fitAndCenterWhenSettled = () => Promise.resolve(); // framed by Cairn (D-043)
  graph.on('ready', () => fit(false));
  for (const name of ['pointerdown', 'wheel']) canvas.addEventListener(name, () => { touched = true; }, { passive: true });
  new ResizeObserver(() => { if (!touched) fit(false); }).observe(canvas);
  stage.classList.remove('cn-graph-loading');
  summary();
}

async function refresh() {
  if (busy || !graph || document.hidden) return;
  busy = true;
  try {
    const next = await load();
    const ids = (data) => data.nodes.map((n) => `${n.id}@${n.x},${n.y}`).join('|');
    const moved = ids(current) !== ids(next);
    const links = new Map(current.edges.map((e) => [e.id, e.data.kind]));
    for (const e of next.edges) { // an edge that changed kind is drawn again
      if (links.has(e.id) && links.get(e.id) !== e.data.kind) {
        graph.removeEdge(e.id);
        current.edges = current.edges.filter((known) => known.id !== e.id);
      }
    }
    applyChanges(graph, current, next);
    current = next;
    summary();
    if (moved && !touched) fit(true);
    const still = selected && current.nodes.find((n) => n.id === selected);
    if (still) showPanel(still.id, still.data);
    else if (selected) hidePanel();
    stage.classList.remove('is-stale');
  } catch {
    stage.classList.add('is-stale'); // the server is away: what is shown is old
  } finally {
    busy = false;
  }
}

stage.querySelectorAll('[data-graph-action]').forEach((button) => {
  button.addEventListener('click', () => {
    if (!graph) return;
    const action = button.dataset.graphAction;
    if (action === 'fit') {
      touched = false;
      fit(true);
      return;
    }
    touched = true;
    if (action === 'in') graph.renderer.zoomIn();
    else graph.renderer.zoomOut();
  });
});
document.addEventListener('keydown', (event) => { if (event.key === 'Escape') hidePanel(); });
stage.addEventListener('mouseleave', () => { peek.hidden = true; });

start()
  .then(() => {
    setInterval(refresh, EVERY);
    subscribe('claude.changed', refresh);
    document.addEventListener('visibilitychange', refresh);
  })
  .catch((error) => {
    stage.classList.remove('cn-graph-loading');
    const failed = stage.querySelector('[data-graph-error]');
    failed.hidden = false;
    failed.querySelector('[data-error]').textContent = error.message || String(error);
  });
