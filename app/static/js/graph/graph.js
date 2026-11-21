/**
 * The plan as a graph, drawn by Pivotick (D-035).
 *
 * - Nodes are task cards, built with DOM methods (never markup from data). Pivotick's own
 *   chrome is hidden: Cairn draws the toolbar, zoom buttons, legend and side panel.
 * - Edges are styled by kind: blocks, follows, relates, duplicates, subtask.
 * - The plan reads left to right: the server places every card in its column (what must come
 *   first on the left) and pins it; Pivotick only draws, with straight lines.
 * - The critical path (server-computed) can be lit. A click opens the task in the side
 *   panel, a double click opens its page. Changes elsewhere arrive live (SSE).
 */

import { Node, Pivotick } from '../../vendor/pivotick/pivotick.es.js';
import { api, debounce } from '../core/api.js';
import { subscribe } from '../core/events.js';

const root = document.getElementById('graph');
const canvas = document.getElementById('graph-canvas');
const panel = document.getElementById('graph-panel');
const query = new URLSearchParams(window.location.search);
let graph = null;
let current = { nodes: [], edges: [], critical: { nodes: [] } };
let criticalOn = false;

/** A design token's resolved colour, so the canvas follows the theme. */
function token(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || '#888';
}

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined && text !== null) node.textContent = String(text);
  return node;
}

function icon(classes) {
  const i = el('i', classes);
  i.setAttribute('aria-hidden', 'true');
  return i;
}

// -- the card ---------------------------------------------------------------------------

function card(node) {
  const d = node.getData();
  const box = el('article', `cn-gcard cn-color-${d.projectColor} cn-gk-${d.statusKind}`);
  box.classList.toggle('is-blocked', d.blocked);
  box.classList.toggle('is-closed', !d.open);
  box.classList.toggle('is-critical', d.critical);

  const top = el('div', 'cn-gcard-top');
  const type = el('span', 'cn-gcard-type');
  type.title = d.typeLabel;
  type.append(icon(`fa-solid ${d.typeIcon}`));
  top.append(type, el('span', 'cn-gcard-project', d.project || 'No project'));
  if (d.open) top.append(el('span', 'cn-gcard-score', d.score));
  else top.append(icon('fa-solid fa-check cn-gcard-done'));

  const title = el('p', 'cn-gcard-title', d.label);

  const meta = el('div', 'cn-gcard-meta');
  meta.append(el('span', 'cn-gcard-status', d.statusLabel));
  if (d.dueText) {
    const due = el('span', `cn-gcard-due ${d.dueState ? `is-${d.dueState}` : ''}`);
    due.append(icon(`fa-${d.hardDeadline ? 'solid fa-lock' : 'regular fa-calendar'}`), document.createTextNode(` ${d.dueText}`));
    meta.append(due);
  }
  if (d.priority === 'critical' || d.priority === 'high') meta.append(el('span', `cn-gcard-prio is-${d.priority}`, d.priority));
  if (d.blocked) {
    const blocked = el('span', 'cn-gcard-flag');
    blocked.append(icon('fa-solid fa-link-slash'), document.createTextNode(' blocked'));
    meta.append(blocked);
  } else if (d.unblocks) {
    const unlocks = el('span', 'cn-gcard-unlocks');
    unlocks.append(icon('fa-solid fa-unlock'), document.createTextNode(` ${d.unblocks}`));
    unlocks.title = `Finishing it unblocks ${d.unblocks}`;
    meta.append(unlocks);
  }
  box.append(top, title, meta);
  return box;
}

// -- styles -----------------------------------------------------------------------------

function edgeStyles() {
  const strong = token('--cn-text-muted');
  const faint = token('--cn-border-strong');
  return {
    blocks: { strokeColor: strong, strokeWidth: 2, curveStyle: 'straight' },
    follows: { strokeColor: faint, strokeWidth: 1.6, dashed: true, animateDash: false, curveStyle: 'straight' },
    relates: { strokeColor: faint, strokeWidth: 1.2, dashed: true, animateDash: false, curveStyle: 'straight', markerEnd: '' },
    duplicates: { strokeColor: token('--cn-warning'), strokeWidth: 1.4, dashed: true, animateDash: false, curveStyle: 'straight' },
    subtask: { strokeColor: faint, strokeWidth: 1, opacity: 0.7, curveStyle: 'straight', markerEnd: '' },
  };
}

function options() {
  return {
    isDirected: true,
    UI: { mode: 'viewer' },
    layout: { type: 'force' }, // every node is pinned (fx/fy): nothing is simulated
    simulation: { useWorker: false },
    render: {
      // Every task is a card: the card is the node (no shape behind it, edges land on it).
      defaultNodeStyle: { shape: 'none', html: card, text: '' },
      edgeTypeAccessor: (edge) => edge.getData()?.kind,
      edgeStyleMap: edgeStyles(),
    },
    callbacks: {
      onNodeClick: (_event, node) => showPanel(node.getData(), node.id),
      onNodeDbclick: (_event, node) => window.location.assign(node.getData().url),
      onCanvasClick: () => hidePanel(),
    },
  };
}

// -- side panel -------------------------------------------------------------------------

function fact(label, value) {
  const row = el('div');
  row.append(el('dt', '', label), el('dd', '', value));
  return row;
}

function showPanel(d, id) {
  const head = el('header', 'cn-gpanel-head');
  const close = el('button', 'cn-icon-button cn-gpanel-close');
  close.type = 'button';
  close.title = 'Close';
  close.append(icon('fa-solid fa-xmark'));
  close.addEventListener('click', hidePanel);
  const chip = el('span', `cn-project-chip cn-color-${d.projectColor}`);
  chip.append(icon(`fa-solid ${d.projectIcon}`), document.createTextNode(d.project || 'No project'));
  head.append(chip, close);

  const title = el('h2', 'cn-gpanel-title', d.label);
  const status = el('p', 'cn-gpanel-status');
  status.append(el('span', `cn-status cn-status-${d.statusKind}`, d.statusLabel));
  if (d.blocked) status.append(el('span', 'cn-badge cn-badge-warning', 'blocked'));
  if (d.critical) status.append(el('span', 'cn-badge cn-badge-accent', 'critical path'));

  const facts = el('dl', 'cn-facts');
  facts.append(fact('Type', d.typeLabel), fact('Priority', d.priority));
  if (d.open) facts.append(fact('Score', d.score));
  if (d.dueText) facts.append(fact('Due', `${d.dueText}${d.hardDeadline ? ' (hard)' : ''}`));
  if (d.estimate) facts.append(fact('Estimate', `${d.estimate} h`));
  if (d.unblocks) facts.append(fact('Unblocks', `${d.unblocks} task${d.unblocks > 1 ? 's' : ''}`));

  const links = el('div', 'cn-gpanel-links');
  const incoming = current.edges.filter((e) => e.to === id && e.data.kind === 'blocks');
  const outgoing = current.edges.filter((e) => e.from === id && e.data.kind === 'blocks');
  const byId = new Map(current.nodes.map((n) => [n.id, n.data]));
  for (const [label, list, key] of [['Blocked by', incoming, 'from'], ['Blocks', outgoing, 'to']]) {
    if (!list.length) continue;
    links.append(el('h3', '', label));
    const ul = el('ul');
    for (const edge of list) {
      const other = byId.get(edge[key]);
      if (!other) continue;
      const li = el('li');
      const a = el('a', '', other.label);
      a.href = other.url;
      li.append(a, el('span', `cn-status cn-status-${other.statusKind}`, other.statusLabel));
      ul.append(li);
    }
    links.append(ul);
  }

  const open = el('a', 'btn btn-primary', 'Open the task');
  open.href = d.url;
  const actions = el('div', 'cn-gpanel-actions');
  actions.append(open);

  panel.replaceChildren(head, title, status, facts, links, actions);
  panel.hidden = false;
}

function hidePanel() {
  panel.hidden = true;
}

// -- critical path, layouts, toolbar -------------------------------------------------------

function lightCritical(on) {
  criticalOn = on;
  root.classList.toggle('cn-graph-critical', on);
  if (!graph) return;
  graph.clearHighlightedElements();
  if (!on) return;
  for (const id of current.critical.nodes) {
    const node = graph.getNode(id);
    if (node) graph.highlightElement(node);
  }
}

// -- where the view opens ------------------------------------------------------------------

const READABLE = 0.6; // below this zoom the cards' text is too small to read

/** Centre the view on graph point (x, y) at `scale`, with Pivotick's own zoom behaviour. */
function viewAt(scale, x, y, smooth = true) {
  const renderer = graph.renderer;
  const canvasSel = renderer.getCanvasSelection();
  const svg = canvasSel.node();
  const Transform = renderer.getZoomTransform().constructor;
  const target = new Transform(scale, svg.clientWidth / 2 - scale * x, svg.clientHeight / 2 - scale * y);
  (smooth ? canvasSel.transition().duration(350) : canvasSel).call(renderer.getZoomBehavior().transform, target);
}

/** The task to start with: open, not blocked, best score. */
function nowNode() {
  const ready = current.nodes.filter((n) => n.data.open && !n.data.blocked);
  return (ready.length ? ready : current.nodes).reduce((a, b) => (b.data.score > a.data.score ? b : a), current.nodes[0]);
}

function openView(smooth = false) {
  if (!current.nodes.length) return;
  const xs = current.nodes.map((n) => n.x);
  const ys = current.nodes.map((n) => n.y);
  const width = Math.max(...xs) - Math.min(...xs) + 320;
  const height = Math.max(...ys) - Math.min(...ys) + 160;
  const svg = graph.renderer.getCanvasSelection().node();
  const fit = Math.min(svg.clientWidth / width, svg.clientHeight / height);
  if (fit >= READABLE) {
    graph.renderer.fitAndCenter();
    return;
  }
  const now = nowNode();
  viewAt(0.8, now.x + 112, now.y + 48, smooth);
}

function summary() {
  const total = current.nodes.length;
  document.getElementById('graph-count').textContent = `${total} task${total === 1 ? '' : 's'} · ${current.steps} step${current.steps === 1 ? '' : 's'}`;
  const critical = document.getElementById('graph-critical-summary');
  const path = current.critical;
  if (path.nodes.length) {
    critical.textContent = `${path.nodes.length} tasks · ~${path.hours} h${path.unknown ? ` (${path.unknown} unestimated)` : ''}`;
  } else {
    critical.textContent = 'no chain yet';
  }
  document.getElementById('graph-empty').hidden = total > 0;
}

// -- data -------------------------------------------------------------------------------

function dataUrl() {
  const params = new URLSearchParams();
  if (query.get('project')) params.set('project', query.get('project'));
  if (query.get('closed') === '1') params.set('closed', '1');
  return `/graph?${params}`;
}

async function load() {
  current = await api(dataUrl());
  summary();
  graph = new Pivotick(canvas, { nodes: current.nodes, edges: current.edges }, options());
  // Pivotick fits the whole plan first, then says `ready`: glide to "now" from there, so the
  // plan shows for a moment and the view lands where the work starts.
  graph.on('ready', () => openView(true));
  if (criticalOn) lightCritical(true);
  root.classList.remove('cn-graph-loading');
}

/** Apply what changed since the last load without rebuilding the graph (positions stay). */
async function refresh() {
  const next = await api(dataUrl());
  const before = new Map(current.nodes.map((n) => [n.id, JSON.stringify(n.data)]));
  const after = new Set(next.nodes.map((n) => n.id));
  const edgesBefore = new Set(current.edges.map((e) => e.id));
  const edgesAfter = new Set(next.edges.map((e) => e.id));
  for (const edge of current.edges) if (!edgesAfter.has(edge.id)) graph.removeEdge(edge.id);
  for (const node of current.nodes) if (!after.has(node.id)) graph.removeNode(node.id);
  for (const node of next.nodes) {
    if (!before.has(node.id)) graph.addNode(node);
    else if (graph.getNode(node.id)) Object.assign(graph.getMutableNode(node.id), { fx: node.fx, fy: node.fy, x: node.x, y: node.y });
    else if (before.get(node.id) !== JSON.stringify(node.data)) graph.updateData([new Node(node.id, node.data)]);
  }
  for (const edge of next.edges) if (!edgesBefore.has(edge.id)) graph.addEdge(edge);
  current = next;
  summary();
  lightCritical(criticalOn);
}

// -- wiring -----------------------------------------------------------------------------

document.getElementById('graph-critical')?.addEventListener('change', (event) => lightCritical(event.target.checked));
document.getElementById('graph-fit')?.addEventListener('click', () => graph?.renderer.fitAndCenter());
document.getElementById('graph-now')?.addEventListener('click', () => graph && openView(true));
document.getElementById('graph-zoom-in')?.addEventListener('click', () => graph?.renderer.zoomIn());
document.getElementById('graph-zoom-out')?.addEventListener('click', () => graph?.renderer.zoomOut());
document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape' && !panel.hidden) hidePanel();
});

const later = debounce(() => refresh().catch(() => window.location.reload()), 400);
subscribe('task.changed', later);
subscribe('project.changed', later);

load().catch((error) => {
  root.classList.remove('cn-graph-loading');
  const failed = document.getElementById('graph-error');
  failed.hidden = false;
  failed.querySelector('[data-error]').textContent = error.message || String(error);
});
