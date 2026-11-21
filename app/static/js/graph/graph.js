/**
 * The plan as a graph, drawn by Pivotick (D-035). Mounts every `[data-graph]` stage on the
 * page (the Graph page, and the graph on each task page).
 *
 * - The server lays the plan out left to right (one column per step) and pins every card;
 *   Pivotick only draws. Cards are built with DOM methods, never markup from data.
 * - Levels: a project shows its cases; a case with subtasks opens its own graph (double
 *   click, or the side panel), with a breadcrumb back up.
 * - Hover shows a peek with the full title; click opens the side panel; the critical path
 *   can be lit; changes elsewhere arrive live (SSE) and are applied as differences.
 */

import { Node, Pivotick } from '../../vendor/pivotick/pivotick.es.js';
import { api, debounce } from '../core/api.js';
import { subscribe } from '../core/events.js';

const READABLE = 0.6; // below this zoom the cards' text is too small to read

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

function chip(className, iconClass, text) {
  const span = el('span', className);
  if (iconClass) span.append(icon(iconClass), document.createTextNode(' '));
  span.append(document.createTextNode(text));
  return span;
}

// -- the card ---------------------------------------------------------------------------

function card(node) {
  const d = node.getData();
  const box = el('article', `cn-gcard cn-color-${d.projectColor} cn-gk-${d.statusKind}`);
  box.classList.toggle('is-blocked', d.blocked);
  box.classList.toggle('is-closed', !d.open);
  box.classList.toggle('is-critical', d.critical);
  box.classList.toggle('is-root', d.isRoot);
  box.classList.toggle('has-children', Boolean(d.drill));

  const top = el('div', 'cn-gcard-top');
  const type = el('span', 'cn-gcard-type');
  type.append(icon(`fa-solid ${d.typeIcon}`));
  top.append(type, el('span', 'cn-gcard-project', d.project || 'No project'));
  if (d.open) top.append(el('span', 'cn-gcard-score', d.score));
  else top.append(icon('fa-solid fa-check cn-gcard-done'));

  const meta = el('div', 'cn-gcard-meta');
  meta.append(el('span', 'cn-gcard-status', d.statusLabel));
  if (d.dueText) meta.append(chip(`cn-gcard-due ${d.dueState ? `is-${d.dueState}` : ''}`, d.hardDeadline ? 'fa-solid fa-lock' : 'fa-regular fa-calendar', d.dueText));
  if (d.priority === 'critical' || d.priority === 'high') meta.append(el('span', `cn-gcard-prio is-${d.priority}`, d.priority));
  if (d.blocked) meta.append(chip('cn-gcard-flag', 'fa-solid fa-link-slash', 'blocked'));
  else if (d.unblocks) meta.append(chip('cn-gcard-unlocks', 'fa-solid fa-unlock', String(d.unblocks)));

  box.append(top, el('p', 'cn-gcard-title', d.label), meta);
  if (d.children) {
    const progress = el('div', 'cn-gcard-children');
    const bar = el('span', 'cn-gcard-bar');
    const fill = el('span');
    fill.style.width = `${Math.round((100 * d.childrenDone) / d.children)}%`; // CSSOM, allowed by the CSP
    bar.append(fill);
    progress.append(icon('fa-solid fa-layer-group'), el('span', '', `${d.childrenDone}/${d.children} subtasks`), bar);
    if (d.drill) progress.append(icon('fa-solid fa-chevron-right cn-gcard-open'));
    box.append(progress);
  }
  return box;
}

function edgeStyles() {
  const strong = token('--cn-text-muted');
  const faint = token('--cn-border-strong');
  const straight = { curveStyle: 'straight' };
  return {
    blocks: { ...straight, strokeColor: strong, strokeWidth: 2 },
    follows: { ...straight, strokeColor: faint, strokeWidth: 1.6, dashed: true, animateDash: false },
    relates: { ...straight, strokeColor: faint, strokeWidth: 1.2, dashed: true, animateDash: false, markerEnd: '' },
    duplicates: { ...straight, strokeColor: token('--cn-warning'), strokeWidth: 1.4, dashed: true, animateDash: false },
    subtask: { ...straight, strokeColor: faint, strokeWidth: 1, opacity: 0.7, markerEnd: '' },
  };
}

// -- one stage --------------------------------------------------------------------------

function mount(stage) {
  const canvas = stage.querySelector('[data-graph-canvas]');
  const panel = stage.querySelector('[data-graph-panel]');
  const peek = stage.querySelector('[data-graph-peek]');
  const compact = stage.classList.contains('cn-graph-compact');
  let graph = null;
  let current = { nodes: [], edges: [], critical: { nodes: [] } };
  let criticalOn = false;
  let selected = null; // id of the task shown in the side panel
  let linking = false; // link mode: first touch = what comes first, second = what it blocks
  let linkFrom = null;
  const hint = stage.querySelector('[data-graph-hint]');
  const linkButton = stage.querySelector('[data-graph-action="link"]');
  let message = ''; // last edit result, kept when the panel is redrawn with fresh data

  const byId = () => new Map(current.nodes.map((n) => [n.id, n.data]));

  // Hover: a peek with the full title and where the task stands (Pivotick's tooltip is off).
  function showPeek(event, node) {
    const d = node.getData();
    const head = el('div', 'cn-gpeek-head');
    head.append(chip(`cn-project-chip cn-color-${d.projectColor}`, `fa-solid ${d.projectIcon}`, d.project || 'No project'), el('span', `cn-status cn-status-${d.statusKind}`, d.statusLabel));
    const facts = el('p', 'cn-gpeek-facts');
    facts.textContent = [d.typeLabel, d.priority, d.dueText && `due ${d.dueText}`, d.children && `${d.childrenDone}/${d.children} subtasks`].filter(Boolean).join(' · ');
    const hint = el('p', 'cn-gpeek-hint', d.drill ? 'Double-click to open its subtasks' : 'Double-click to open the task');
    peek.replaceChildren(head, el('p', 'cn-gpeek-title', d.label), facts, hint);
    peek.hidden = false;
    movePeek(event);
  }

  function movePeek(event) {
    if (peek.hidden || !event) return;
    const box = stage.getBoundingClientRect();
    const x = Math.min(event.clientX - box.left + 18, box.width - peek.offsetWidth - 12);
    const y = Math.min(event.clientY - box.top + 18, box.height - peek.offsetHeight - 12);
    peek.style.transform = `translate(${Math.max(12, x)}px, ${Math.max(12, y)}px)`;
  }

  const hidePeek = () => { peek.hidden = true; };

  function open(d) {
    window.location.assign(d.drill && !d.isRoot ? d.drill : d.url);
  }

  function fact(label, value) {
    const row = el('div');
    row.append(el('dt', '', label), el('dd', '', value));
    return row;
  }

  function showPanel(d, id) {
    hidePeek();
    if (selected !== id) message = '';
    selected = id;
    const head = el('header', 'cn-gpanel-head');
    const close = el('button', 'cn-icon-button cn-gpanel-close');
    close.type = 'button';
    close.title = 'Close';
    close.append(icon('fa-solid fa-xmark'));
    close.addEventListener('click', hidePanel);
    head.append(chip(`cn-project-chip cn-color-${d.projectColor}`, `fa-solid ${d.projectIcon}`, d.project || 'No project'), close);

    const status = el('p', 'cn-gpanel-status');
    status.append(el('span', `cn-status cn-status-${d.statusKind}`, d.statusLabel));
    if (d.blocked) status.append(el('span', 'cn-badge cn-badge-warning', 'blocked'));
    if (d.critical) status.append(el('span', 'cn-badge cn-badge-accent', 'critical path'));

    const facts = el('dl', 'cn-facts');
    facts.append(fact('Type', d.typeLabel), fact('Priority', d.priority));
    if (d.open) facts.append(fact('Score', d.score));
    if (d.dueText) facts.append(fact('Due', `${d.dueText}${d.hardDeadline ? ' (hard)' : ''}`));
    if (d.estimate) facts.append(fact('Estimate', `${d.estimate} h`));
    if (d.children) facts.append(fact('Subtasks', `${d.childrenDone} of ${d.children} done`));
    if (d.unblocks) facts.append(fact('Unblocks', `${d.unblocks} task${d.unblocks > 1 ? 's' : ''}`));

    const links = el('div', 'cn-gpanel-links');
    const nodes = byId();
    for (const [label, list, key] of [
      ['Must come first', current.edges.filter((e) => e.to === id && e.data.kind !== 'subtask'), 'from'],
      ['Opens up', current.edges.filter((e) => e.from === id && e.data.kind !== 'subtask'), 'to'],
    ]) {
      if (!list.length) continue;
      links.append(el('h3', '', label));
      const ul = el('ul');
      for (const edge of list) {
        const other = nodes.get(edge[key]);
        if (!other) continue;
        const li = el('li');
        const a = el('a', '', other.label);
        a.href = other.drill || other.url;
        li.append(a, el('span', `cn-status cn-status-${other.statusKind}`, other.statusLabel));
        ul.append(li);
      }
      links.append(ul);
    }

    const editing = editTools(d, id);

    const actions = el('div', 'cn-gpanel-actions');
    if (d.drill && !d.isRoot) {
      const deeper = el('a', 'btn btn-primary');
      deeper.href = d.drill;
      deeper.append(icon('fa-solid fa-layer-group'), document.createTextNode(` Open its ${d.children} subtasks`));
      actions.append(deeper);
    }
    const page = el('a', d.drill && !d.isRoot ? 'btn btn-outline-secondary' : 'btn btn-primary', 'Open the task');
    page.href = d.url;
    actions.append(page);

    panel.replaceChildren(head, el('h2', 'cn-gpanel-title', d.label), status, facts, links, editing, actions);
    panel.hidden = false;
  }

  /** Change the status, or link the task to another card of this graph (undoable, logged). */
  function editTools(d, id) {
    const box = el('div', 'cn-gpanel-edit');
    const note = el('p', 'cn-gpanel-note', message);
    note.setAttribute('role', 'status');
    const run = async (button, work, done) => {
      button.disabled = true;
      try {
        await work();
        message = done;
        note.textContent = done;
        later(); // the graph and this panel follow: columns, edges, critical path recomputed
      } catch (error) {
        note.textContent = error.message;
        button.disabled = false;
      }
    };

    if (d.next?.length) {
      box.append(el('h3', '', 'Move to'));
      const row = el('div', 'cn-gpanel-moves');
      for (const status of d.next) {
        const button = el('button', `btn btn-sm cn-move cn-move-${status.kind}`, status.label);
        button.type = 'button';
        button.addEventListener('click', () => run(button,
          () => api(`/tasks/${id}/status`, { method: 'POST', body: { status: status.key } }),
          `Now ${status.label}. You can undo it from the task page history.`));
        row.append(button);
      }
      box.append(row);
    }

    const others = current.nodes.filter((n) => n.id !== id);
    if (others.length) {
      box.append(el('h3', '', 'Link'));
      const form = el('form', 'cn-gpanel-link');
      const how = el('select', 'form-select form-select-sm');
      how.setAttribute('aria-label', 'How');
      for (const [value, label] of [['blocks', 'blocks'], ['blocked_by', 'is blocked by'], ['follows', 'comes after'], ['relates', 'relates to']]) {
        const option = el('option', '', label);
        option.value = value;
        how.append(option);
      }
      const other = el('select', 'form-select form-select-sm');
      other.setAttribute('aria-label', 'Which task');
      for (const n of others.sort((a, b) => a.data.label.localeCompare(b.data.label))) {
        const option = el('option', '', n.data.label);
        option.value = n.id;
        other.append(option);
      }
      const add = el('button', 'btn btn-sm btn-outline-secondary', 'Link');
      add.type = 'submit';
      form.append(how, other, add);
      form.addEventListener('submit', (event) => {
        event.preventDefault();
        const kind = how.value === 'blocked_by' ? 'blocks' : how.value;
        const [from, to] = how.value === 'blocked_by' || how.value === 'follows' ? [other.value, id] : [id, other.value];
        run(add, () => api('/dependencies', { method: 'POST', body: { from_task_id: from, to_task_id: to, kind } }), 'Linked.');
      });
      box.append(form);
    }
    box.append(note);
    return box;
  }

  const hidePanel = () => {
    panel.hidden = true;
    selected = null;
  };

  function options() {
    return {
      isDirected: true,
      UI: { mode: 'viewer', tooltip: { enabled: false } },
      layout: { type: 'force' }, // every node is pinned (fx/fy): nothing is simulated
      simulation: { useWorker: false },
      render: {
        // Every task is a card: the card is the node (no shape behind it, edges land on it).
        defaultNodeStyle: { shape: 'none', html: card, text: '' },
        edgeTypeAccessor: (edge) => edge.getData()?.kind,
        edgeStyleMap: edgeStyles(),
      },
      callbacks: {
        onNodeClick: (_event, node) => (linking ? pickForLink(node) : showPanel(node.getData(), node.id)),
        onNodeDbclick: (_event, node) => { if (!linking) open(node.getData()); },
        onNodeHoverIn: (event, node) => showPeek(event, node),
        onNodeHoverOut: hidePeek,
        onCanvasClick: () => { hidePanel(); hidePeek(); },
        onCanvasMousemove: movePeek,
      },
    };
  }

  // -- link mode -----------------------------------------------------------------------

  function say(text, tone = '') {
    hint.textContent = text;
    hint.dataset.tone = tone;
    hint.hidden = !text;
  }

  function setLinking(on) {
    linking = on;
    linkFrom = null;
    stage.classList.toggle('cn-graph-linking', on);
    linkButton?.setAttribute('aria-pressed', String(on));
    if (on) {
      hidePanel();
      say('Link mode: touch the task that must come first. Esc to stop.');
    } else {
      graph?.deselectAll();
      say('');
    }
  }

  async function pickForLink(node) {
    if (!linkFrom) {
      linkFrom = node;
      graph.selectElement(node);
      say(`“${node.getData().label}” comes first. Now touch the task it blocks.`);
      return;
    }
    if (linkFrom.id === node.id) {
      say('Pick another task: a task cannot block itself.', 'warn');
      return;
    }
    const first = linkFrom;
    linkFrom = null;
    graph.deselectAll();
    try {
      await api('/dependencies', { method: 'POST', body: { from_task_id: first.id, to_task_id: node.id, kind: 'blocks' } });
      say(`Linked: “${first.getData().label}” blocks “${node.getData().label}”. Touch the next pair, or Esc.`, 'ok');
      later();
    } catch (error) {
      say(`${error.message} Touch another pair, or Esc.`, 'warn');
    }
  }

  // -- view ----------------------------------------------------------------------------

  function viewAt(scale, x, y, smooth = true) {
    const renderer = graph.renderer;
    const canvasSel = renderer.getCanvasSelection();
    const svg = canvasSel.node();
    const Transform = renderer.getZoomTransform().constructor;
    const target = new Transform(scale, svg.clientWidth / 2 - scale * x, svg.clientHeight / 2 - scale * y);
    (smooth ? canvasSel.transition().duration(350) : canvasSel).call(renderer.getZoomBehavior().transform, target);
  }

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
    if (Math.min(svg.clientWidth / width, svg.clientHeight / height) >= READABLE) {
      graph.renderer.fitAndCenter();
      return;
    }
    const now = nowNode();
    viewAt(compact ? 0.7 : 0.8, now.x + 112, now.y + 48, smooth);
  }

  function lightCritical(on) {
    criticalOn = on;
    stage.classList.toggle('cn-graph-critical', on);
    if (!graph) return;
    graph.clearHighlightedElements();
    if (!on) return;
    for (const id of current.critical.nodes) {
      const node = graph.getNode(id);
      if (node) graph.highlightElement(node);
    }
    const critical = new Set(current.edges.filter((e) => e.data.critical).map((e) => e.id));
    for (const id of current.critical.nodes) {
      for (const edge of graph.getEdgesFromNode(id)) {
        if (edge && critical.has(edge.id) && typeof edge.getGraphElement === 'function') graph.highlightElement(edge);
      }
    }
  }

  function summary() {
    const total = current.nodes.length;
    const count = stage.querySelector('[data-graph-count]');
    count.textContent = `${total} ${current.mode === 'top' ? 'case' : 'task'}${total === 1 ? '' : 's'} · ${current.steps} step${current.steps === 1 ? '' : 's'}`;
    const path = current.critical;
    stage.querySelector('[data-graph-critical-summary]').textContent = path.nodes.length
      ? `${path.nodes.length} · ~${path.hours} h${path.unknown ? ` (${path.unknown} unestimated)` : ''}`
      : 'none';
    stage.querySelector('[data-graph-empty]').hidden = total > 0;
    const crumbs = document.querySelector('[data-graph-crumbs]');
    if (crumbs && current.breadcrumb) {
      const parts = [];
      current.breadcrumb.forEach((step, index) => {
        const last = index === current.breadcrumb.length - 1;
        if (index) parts.push(icon('fa-solid fa-chevron-right cn-crumb-sep'));
        const item = last ? el('span', 'cn-crumb-current', step.label) : el('a', '', step.label);
        if (last) item.setAttribute('aria-current', 'page');
        else item.href = step.url;
        parts.push(item);
      });
      crumbs.replaceChildren(...parts);
    }
  }

  const query = () => stage.dataset.query || '';

  async function load() {
    current = await api(`/graph?${query()}`);
    summary();
    graph = new Pivotick(canvas, { nodes: current.nodes, edges: current.edges }, options());
    // Pivotick fits the whole plan first, then says `ready`: glide to "now" from there.
    graph.on('ready', () => openView(true));
    stage.classList.remove('cn-graph-loading');
  }

  /** Apply what changed since the last load without rebuilding the graph. */
  async function refresh() {
    const next = await api(`/graph?${query()}`);
    const before = new Map(current.nodes.map((n) => [n.id, JSON.stringify([n.data, n.x, n.y])]));
    const after = new Set(next.nodes.map((n) => n.id));
    const edgesAfter = new Set(next.edges.map((e) => e.id));
    const edgesBefore = new Set(current.edges.map((e) => e.id));
    for (const edge of current.edges) if (!edgesAfter.has(edge.id)) graph.removeEdge(edge.id);
    for (const node of current.nodes) if (!after.has(node.id)) graph.removeNode(node.id);
    for (const node of next.nodes) {
      if (!before.has(node.id)) graph.addNode(node);
      else if (before.get(node.id) !== JSON.stringify([node.data, node.x, node.y])) {
        const fresh = new Node(node.id, node.data);
        Object.assign(fresh, { x: node.x, y: node.y, fx: node.fx, fy: node.fy });
        graph.updateData([fresh]);
      }
    }
    for (const edge of next.edges) if (!edgesBefore.has(edge.id)) graph.addEdge(edge);
    current = next;
    summary();
    lightCritical(criticalOn);
    const still = selected && current.nodes.find((n) => n.id === selected);
    if (still && !panel.hidden) showPanel(still.data, still.id);
    else if (selected && !still) hidePanel();
  }

  stage.querySelectorAll('[data-graph-action]').forEach((button) => {
    button.addEventListener('click', () => {
      if (!graph) return;
      const action = button.dataset.graphAction;
      if (action === 'in') graph.renderer.zoomIn();
      else if (action === 'out') graph.renderer.zoomOut();
      else if (action === 'fit') graph.renderer.fitAndCenter();
      else if (action === 'link') setLinking(!linking);
      else openView(true);
    });
  });
  stage.querySelector('[data-graph-critical]')?.addEventListener('change', (event) => lightCritical(event.target.checked));
  stage.addEventListener('mouseleave', hidePeek);
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') {
      hidePanel();
      hidePeek();
      if (linking) setLinking(false);
    }
    const typing = event.composedPath()[0]?.matches?.('input, textarea, select, [contenteditable]');
    if (!typing && !compact && event.key.toLowerCase() === 'l' && !event.ctrlKey && !event.metaKey && !event.altKey) {
      setLinking(!linking);
    }
  });

  const later = debounce(() => refresh().catch(() => window.location.reload()), 400);
  subscribe('task.changed', later);
  subscribe('project.changed', later);

  load().catch((error) => {
    stage.classList.remove('cn-graph-loading');
    const failed = stage.querySelector('[data-graph-error]');
    failed.hidden = false;
    failed.querySelector('[data-error]').textContent = error.message || String(error);
  });
}

document.querySelectorAll('[data-graph]').forEach(mount);

// The Graph page's own toolbar: a level or project change applies at once.
const toolbar = document.querySelector('.cn-graph-toolbar');
toolbar?.addEventListener('change', (event) => {
  if (event.target.matches('select, input[type="radio"]')) toolbar.requestSubmit();
});
