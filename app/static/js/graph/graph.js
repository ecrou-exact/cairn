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
 * - Find (`/`): a task by its title, even a subtask hidden inside a case, brings its card
 *   into view, selected, with its side panel open.
 */

import { Pivotick } from '../../vendor/pivotick/pivotick.es.js';
import { api, debounce } from '../core/api.js';
import { subscribe } from '../core/events.js';
import { CARD_H, CARD_W, applyChanges, chip, el, fact, fitCards, icon, placePeek, token, viewAt as moveView } from './stage.js';

const READABLE = 0.6; // below this zoom the cards' text is too small to read

// -- the card ---------------------------------------------------------------------------

/** A project on the plan of projects (D-044): its colour, progress, what is open, blocked,
 *  late, and the task to do next there. */
function projectCard(d) {
  const box = el('article', `cn-gcard cn-gcard-project cn-color-${d.projectColor}`);
  box.classList.toggle('is-closed', d.status !== 'active');
  const top = el('div', 'cn-gcard-top');
  const type = el('span', 'cn-gcard-type');
  type.append(icon(`fa-solid ${d.projectIcon}`));
  top.append(type, el('span', 'cn-gcard-project', d.status === 'active' ? 'Project' : d.status));
  if (d.score) top.append(el('span', 'cn-gcard-score', d.score));
  const meta = el('div', 'cn-gcard-meta');
  meta.append(el('span', '', `${d.open} open`));
  if (d.blockedCount) meta.append(chip('cn-gcard-flag', 'fa-solid fa-link-slash', String(d.blockedCount)));
  if (d.late) meta.append(chip('cn-gcard-due is-late', 'fa-regular fa-calendar', `${d.late} late`));
  else if (d.dueText) meta.append(chip(`cn-gcard-due ${d.dueState ? `is-${d.dueState}` : ''}`, 'fa-regular fa-calendar', d.dueText));
  box.append(top, el('p', 'cn-gcard-title', d.label), meta);
  const progress = el('div', 'cn-gcard-children');
  const bar = el('span', 'cn-gcard-bar');
  const fill = el('span');
  fill.style.width = `${d.total ? Math.round((100 * d.done) / d.total) : 0}%`; // CSSOM, allowed by the CSP
  bar.append(fill);
  progress.append(icon('fa-solid fa-play'), el('span', 'cn-gcard-next', d.next || 'nothing ready'), bar);
  box.append(progress);
  return box;
}

function card(node) {
  const d = node.getData();
  if (d.kind === 'project') return projectCard(d);
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
    before: { ...straight, strokeColor: token('--cn-mark'), strokeWidth: 2.4 },
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
  const projectsView = () => current.mode === 'projects';

  function showPeek(event, node) {
    const d = node.getData();
    if (d.kind === 'project') {
      const head = el('div', 'cn-gpeek-head');
      head.append(chip(`cn-project-chip cn-color-${d.projectColor}`, `fa-solid ${d.projectIcon}`, d.label));
      const facts = el('p', 'cn-gpeek-facts', [`${d.open} open`, `${d.done} done`, d.blockedCount && `${d.blockedCount} blocked`, d.late && `${d.late} late`].filter(Boolean).join(' · '));
      peek.replaceChildren(head, el('p', 'cn-gpeek-title', d.next ? `Next: ${d.next}` : 'Nothing ready to do'), facts, el('p', 'cn-gpeek-hint', 'Double-click to open its plan'));
      peek.hidden = false;
      movePeek(event);
      return;
    }
    const head = el('div', 'cn-gpeek-head');
    head.append(chip(`cn-project-chip cn-color-${d.projectColor}`, `fa-solid ${d.projectIcon}`, d.project || 'No project'), el('span', `cn-status cn-status-${d.statusKind}`, d.statusLabel));
    const facts = el('p', 'cn-gpeek-facts');
    facts.textContent = [d.typeLabel, d.priority, d.dueText && `due ${d.dueText}`, d.children && `${d.childrenDone}/${d.children} subtasks`].filter(Boolean).join(' · ');
    const hint = el('p', 'cn-gpeek-hint', d.drill ? 'Double-click to open its subtasks' : 'Double-click to open the task');
    peek.replaceChildren(head, el('p', 'cn-gpeek-title', d.label), facts, hint);
    peek.hidden = false;
    movePeek(event);
  }

  const movePeek = (event) => placePeek(stage, peek, event);

  const hidePeek = () => { peek.hidden = true; };

  function open(d) {
    window.location.assign(d.drill && !d.isRoot ? d.drill : d.url);
  }

  /** A project in the side panel: what is there, the projects around it, order it. */
  function showProjectPanel(d, id) {
    const head = el('header', 'cn-gpanel-head');
    const close = el('button', 'cn-icon-button cn-gpanel-close');
    close.type = 'button';
    close.title = 'Close';
    close.append(icon('fa-solid fa-xmark'));
    close.addEventListener('click', hidePanel);
    head.append(chip(`cn-project-chip cn-color-${d.projectColor}`, `fa-solid ${d.projectIcon}`, d.status), close);
    const facts = el('dl', 'cn-facts');
    facts.append(fact('Open', d.open), fact('Done', d.done));
    if (d.blockedCount) facts.append(fact('Blocked', d.blockedCount));
    if (d.late) facts.append(fact('Late', d.late));
    if (d.dueText) facts.append(fact('Next due', d.dueText));
    if (d.next) facts.append(fact('Next', d.next));

    const note = el('p', 'cn-gpanel-note', message);
    note.setAttribute('role', 'status');
    const nodes = byId();
    const links = el('div', 'cn-gpanel-links');
    for (const [label, list, key] of [
      ['Passes after', current.edges.filter((e) => e.to === id), 'from'],
      ['Passes before', current.edges.filter((e) => e.from === id), 'to'],
    ]) {
      if (!list.length) continue;
      links.append(el('h3', '', label));
      const ul = el('ul');
      for (const edge of list) {
        const other = nodes.get(edge[key]);
        if (!other) continue;
        const li = el('li');
        const a = el('a', '', other.label);
        a.href = other.drill;
        li.append(a);
        if (edge.data.linkId) {
          const drop = el('button', 'cn-icon-button cn-gpanel-unlink');
          drop.type = 'button';
          drop.title = 'Remove this order (undoable)';
          drop.append(icon('fa-solid fa-xmark'));
          drop.addEventListener('click', async () => {
            drop.disabled = true;
            try {
              await api(`/project-links/${edge.data.linkId}`, { method: 'DELETE' });
              message = 'Order removed. You can undo it from the history.';
              later();
            } catch (error) {
              note.textContent = error.message;
              drop.disabled = false;
            }
          });
          li.append(drop);
        } else {
          li.append(el('small', 'cn-muted', edge.data.note));
        }
        ul.append(li);
      }
      links.append(ul);
    }

    const box = el('div', 'cn-gpanel-edit');
    const others = current.nodes.filter((n) => n.id !== id);
    if (others.length) {
      box.append(el('h3', '', 'Order'));
      const form = el('form', 'cn-gpanel-link');
      const how = el('select', 'form-select form-select-sm');
      how.setAttribute('aria-label', 'How');
      for (const [value, label] of [['before', 'passes before'], ['after', 'passes after']]) {
        const option = el('option', '', label);
        option.value = value;
        how.append(option);
      }
      const other = el('select', 'form-select form-select-sm');
      other.setAttribute('aria-label', 'Which project');
      for (const n of others.sort((a, b) => a.data.label.localeCompare(b.data.label))) {
        const option = el('option', '', n.data.label);
        option.value = n.id;
        other.append(option);
      }
      const add = el('button', 'btn btn-sm btn-outline-secondary', 'Order');
      add.type = 'submit';
      form.append(how, other, add);
      form.addEventListener('submit', async (event) => {
        event.preventDefault();
        const [first, then] = how.value === 'before' ? [id, other.value] : [other.value, id];
        add.disabled = true;
        try {
          await api('/project-links', { method: 'POST', body: { from_project_id: first, to_project_id: then } });
          message = 'Ordered.';
          later();
        } catch (error) {
          note.textContent = error.message;
          add.disabled = false;
        }
      });
      box.append(form);
    }
    box.append(note);

    const actions = el('div', 'cn-gpanel-actions');
    const plan = el('a', 'btn btn-primary');
    plan.href = d.drill;
    plan.append(icon('fa-solid fa-diagram-project'), document.createTextNode(' Its plan'));
    const page = el('a', 'btn btn-outline-secondary', 'Tasks');
    page.href = `${d.url}?tab=tasks`;
    actions.append(plan, page);
    panel.replaceChildren(head, el('h2', 'cn-gpanel-title', d.label), facts, links, box, actions);
    panel.hidden = false;
  }

  function showPanel(d, id) {
    hidePeek();
    if (selected !== id) message = '';
    selected = id;
    if (d.kind === 'project') {
      showProjectPanel(d, id);
      return;
    }
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
      UI: { mode: 'viewer', tooltip: { enabled: false }, contextMenu: { enabled: false } },
      layout: { type: 'force' }, // every node is pinned (fx/fy): nothing is simulated
      simulation: { useWorker: false, warmupTicks: 0, cooldownTime: 0 }, // pinned: nothing to simulate
      render: {
        // Every task is a card: the card is the node (no shape behind it, edges land on it).
        defaultNodeStyle: { shape: 'none', html: card, text: '' },
        edgeTypeAccessor: (edge) => edge.getData()?.kind,
        edgeStyleMap: edgeStyles(),
      },
      callbacks: {
        onNodeClick: (_event, node) => (linking ? pickForLink(node) : showPanel(node.getData(), node.id)),
        onNodeDbclick: (_event, node) => { if (!linking) open(node.getData()); },
        onNodeContextmenu: (event, node) => { if (!linking) showMenu(event, node); },
        onNodeHoverIn: (event, node) => showPeek(event, node),
        onNodeHoverOut: hidePeek,
        onCanvasClick: () => { hidePanel(); hidePeek(); hideMenu(); if (!linking) say(''); },
        onCanvasMousemove: movePeek,
        onCanvasZoom: () => saveView(),
      },
    };
  }

  // -- right-click menu ----------------------------------------------------------------

  const menu = stage.querySelector('[data-graph-menu]');

  function hideMenu() {
    if (menu) menu.hidden = true;
  }

  /** Open, go down, move to an allowed status, or start a link from this card. */
  function showMenu(event, node) {
    if (!menu) return;
    hidePeek();
    const d = node.getData();
    const items = [];
    const item = (iconClass, text, act, extra = '') => {
      const button = el('button', `cn-gmenu-item ${extra}`);
      button.type = 'button';
      button.setAttribute('role', 'menuitem');
      button.tabIndex = -1;
      button.append(icon(`fa-solid ${iconClass}`), el('span', '', text));
      button.addEventListener('click', () => { hideMenu(); act(); });
      items.push(button);
      return button;
    };
    const title = el('p', 'cn-gmenu-title', d.label);
    if (d.kind === 'project') {
      item('fa-diagram-project', 'Open its plan', () => window.location.assign(d.drill));
      item('fa-list-check', 'Its tasks', () => window.location.assign(`${d.url}?tab=tasks`));
      item('fa-link', 'Order from here…', () => { setLinking(true); pickForLink(node); });
      item('fa-circle-info', 'Details', () => showPanel(d, node.id));
      menu.replaceChildren(title, ...items);
      menu.hidden = false;
      placeMenu(event);
      items[0].focus();
      return;
    }
    item('fa-arrow-up-right-from-square', 'Open the task', () => window.location.assign(d.url));
    if (d.drill && !d.isRoot) item('fa-layer-group', `Open its ${d.children} subtasks`, () => window.location.assign(d.drill));
    item('fa-link', 'Link from here…', () => { setLinking(true); pickForLink(node); });
    item('fa-terminal', 'Claude on this task…', () => document.querySelector('cn-claude-launch')?.open({ task: node.id, taskTitle: d.label, preset: 'task' }));
    item('fa-circle-info', 'Details', () => showPanel(d, node.id));
    const moves = (d.next || []).map((status) => item('fa-circle', `Move to ${status.label}`, async () => {
      try {
        await api(`/tasks/${node.id}/status`, { method: 'POST', body: { status: status.key } });
        say(`“${d.label}” is now ${status.label}. Undo it from the task's history.`, 'ok');
        later();
      } catch (error) {
        say(error.message, 'warn');
      }
    }, `cn-gmenu-move cn-move-${status.kind}`));
    const parts = [title, ...items.slice(0, items.length - moves.length)];
    if (moves.length) parts.push(el('hr', 'cn-gmenu-sep'), ...moves);
    menu.replaceChildren(...parts);
    menu.hidden = false;
    placeMenu(event);
    items[0].focus();
  }

  function placeMenu(event) {
    const box = stage.getBoundingClientRect();
    const x = Math.min(event.clientX - box.left, box.width - menu.offsetWidth - 8);
    const y = Math.min(event.clientY - box.top, box.height - menu.offsetHeight - 8);
    menu.style.transform = `translate(${Math.max(8, x)}px, ${Math.max(8, y)}px)`;
  }

  menu?.addEventListener('keydown', (event) => {
    const items = [...menu.querySelectorAll('[role="menuitem"]')];
    const at = items.indexOf(document.activeElement);
    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      event.preventDefault();
      items[(at + (event.key === 'ArrowDown' ? 1 : -1) + items.length) % items.length].focus();
    } else if (event.key === 'Escape' || event.key === 'Tab') {
      event.preventDefault();
      hideMenu();
    }
  });
  document.addEventListener('pointerdown', (event) => { if (menu && !menu.hidden && !menu.contains(event.target)) hideMenu(); });

  // -- the same cards as a table, in plan order ---------------------------------------

  const tableBox = stage.querySelector('[data-graph-table]');
  const tableButton = stage.querySelector('[data-graph-action="table"]');
  let tableOn = false;

  function drawTable() {
    if (!tableBox || !tableOn) return;
    const step = 224 + 104; // CARD_W + COL_GAP in graph_core: one column per step
    const left = Math.min(...current.nodes.map((n) => n.x));
    const rows = [...current.nodes].sort((a, b) => a.x - b.x || a.y - b.y);
    const table = el('table', 'table cn-table');
    const caption = el('caption', 'visually-hidden', 'The cards of this graph, in plan order');
    const head = el('thead');
    const hr = el('tr');
    for (const label of ['Step', 'Task', 'Project', 'Status', 'Priority', 'Due', 'Score', 'Links']) {
      const th = el('th', '', label);
      th.scope = 'col';
      hr.append(th);
    }
    head.append(hr);
    const body = el('tbody');
    for (const n of rows) {
      const d = n.data;
      const tr = el('tr', d.critical ? 'is-critical' : '');
      const link = el('a', '', d.label);
      link.href = d.drill && !d.isRoot ? d.drill : d.url;
      const name = el('td', 'cn-gtable-task');
      name.append(icon(`fa-solid ${d.typeIcon}`), document.createTextNode(' '), link);
      if (d.children) name.append(el('small', '', ` ${d.childrenDone}/${d.children}`));
      const links = el('td');
      if (d.blocked) links.append(chip('cn-gcard-flag', 'fa-solid fa-link-slash', 'blocked'));
      else if (d.unblocks) links.append(chip('cn-gcard-unlocks', 'fa-solid fa-unlock', String(d.unblocks)));
      const due = el('td', d.dueState ? `is-${d.dueState}` : '', d.dueText || '—');
      tr.append(
        el('td', 'cn-gtable-step', Math.round((n.x - left) / step) + 1),
        name,
        el('td', '', d.project || '—'),
        (() => { const td = el('td'); td.append(el('span', `cn-status cn-status-${d.statusKind}`, d.statusLabel)); return td; })(),
        el('td', `cn-gtable-prio is-${d.priority}`, d.priority),
        due,
        el('td', 'cn-gtable-score', d.open ? d.score : '✓'),
        links,
      );
      body.append(tr);
    }
    table.append(caption, head, body);
    tableBox.replaceChildren(table);
  }

  function setTable(on) {
    tableOn = on;
    stage.classList.toggle('cn-graph-tabled', on);
    tableButton?.setAttribute('aria-pressed', String(on));
    if (tableBox) tableBox.hidden = !on;
    if (on) {
      hidePanel();
      hideMenu();
      drawTable();
    }
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
      say(projectsView() ? 'Order mode: touch the project that passes first. Esc to stop.' : 'Link mode: touch the task that must come first. Esc to stop.');
    } else {
      graph?.deselectAll();
      say('');
    }
  }

  async function pickForLink(node) {
    if (!linkFrom) {
      linkFrom = node;
      graph.selectElement(node);
      say(projectsView() ? `“${node.getData().label}” passes first. Now touch the project that comes after it.` : `“${node.getData().label}” comes first. Now touch the task it blocks.`);
      return;
    }
    if (linkFrom.id === node.id) {
      say(projectsView() ? 'Pick another project.' : 'Pick another task: a task cannot block itself.', 'warn');
      return;
    }
    const first = linkFrom;
    linkFrom = null;
    graph.deselectAll();
    try {
      if (projectsView()) {
        await api('/project-links', { method: 'POST', body: { from_project_id: first.id, to_project_id: node.id } });
        say(`Ordered: “${first.getData().label}” passes before “${node.getData().label}”. Touch the next pair, or Esc.`, 'ok');
      } else {
        await api('/dependencies', { method: 'POST', body: { from_task_id: first.id, to_task_id: node.id, kind: 'blocks' } });
        say(`Linked: “${first.getData().label}” blocks “${node.getData().label}”. Touch the next pair, or Esc.`, 'ok');
      }
      later();
    } catch (error) {
      say(`${error.message} Touch another pair, or Esc.`, 'warn');
    }
  }

  // -- find ----------------------------------------------------------------------------

  /** Find a task by its title, subtasks hidden inside a case included (server-side search). */
  function setupFind(box) {
    const input = box.querySelector('input');
    const list = box.querySelector('[role="listbox"]');
    let matches = [];
    let active = -1;
    let asked = 0;

    const close = () => {
      list.hidden = true;
      active = -1;
      input.setAttribute('aria-expanded', 'false');
      input.removeAttribute('aria-activedescendant');
    };

    function mark(index) {
      active = index;
      list.querySelectorAll('[role="option"]').forEach((item, i) => item.setAttribute('aria-selected', String(i === index)));
      if (index >= 0) input.setAttribute('aria-activedescendant', `graph-find-${index}`);
      else input.removeAttribute('aria-activedescendant');
    }

    function draw(found) {
      const items = found.matches.map((match, index) => {
        const item = el('li', `cn-graph-find-item${match.card ? '' : ' is-off'}`);
        item.id = `graph-find-${index}`;
        item.setAttribute('role', 'option');
        item.setAttribute('aria-selected', 'false');
        const where = match.card
          ? (match.inside.length ? `inside ${match.inside.join(' › ')}` : 'on this graph')
          : 'not on this graph: opens the task';
        const line = el('span', 'cn-graph-find-meta');
        line.append(el('span', `cn-status cn-status-${match.statusKind}`, match.statusLabel), document.createTextNode([match.project, where].filter(Boolean).join(' · ')));
        item.append(el('span', 'cn-graph-find-title', match.label), line);
        item.addEventListener('pointerdown', (event) => event.preventDefault()); // keep the focus in the field
        item.addEventListener('click', () => choose(match));
        return item;
      });
      if (!items.length) items.push(el('li', 'cn-graph-find-none', `No task here has “${found.query}” in its title.`));
      if (found.more) items.push(el('li', 'cn-graph-find-none', `${found.more} more: add a word to narrow it down.`));
      list.replaceChildren(...items);
      list.hidden = false;
      input.setAttribute('aria-expanded', 'true');
      mark(found.matches.length ? 0 : -1);
    }

    function choose(match) {
      close();
      const node = match.card && graph?.getNode(match.card);
      if (!node) {
        window.location.assign(match.url);
        return;
      }
      if (linking) setLinking(false);
      const zoom = graph.renderer.getZoomTransform().k;
      viewAt(Math.max(zoom, compact ? 0.7 : 0.8), node.x, node.y);
      graph.deselectAll();
      graph.selectElement(node);
      showPanel(node.getData(), node.id);
      say(match.inside.length ? `“${match.label}” is inside this case. Double-click it to open its subtasks.` : '', 'ok');
    }

    const search = debounce(async () => {
      const text = input.value.trim();
      const ticket = ++asked;
      if (!text) {
        matches = [];
        close();
        return;
      }
      const params = new URLSearchParams(query());
      params.set('q', text);
      try {
        const found = await api(`/graph/find?${params}`);
        if (ticket !== asked) return; // a newer search is on its way
        matches = found.matches;
        draw(found);
      } catch (error) {
        if (ticket !== asked) return;
        matches = [];
        list.replaceChildren(el('li', 'cn-graph-find-none', error.message));
        list.hidden = false;
      }
    }, 180);

    input.addEventListener('input', search);
    input.addEventListener('focus', () => { if (matches.length) { list.hidden = false; input.setAttribute('aria-expanded', 'true'); } });
    input.addEventListener('blur', close);
    input.addEventListener('keydown', (event) => {
      if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
        if (!matches.length) return;
        event.preventDefault();
        if (list.hidden) { list.hidden = false; input.setAttribute('aria-expanded', 'true'); }
        const step = event.key === 'ArrowDown' ? 1 : -1;
        mark((active + step + matches.length) % matches.length);
        document.getElementById(`graph-find-${active}`)?.scrollIntoView({ block: 'nearest' });
      } else if (event.key === 'Enter') {
        event.preventDefault();
        if (matches.length) choose(matches[Math.max(active, 0)]);
      } else if (event.key === 'Escape') {
        event.stopPropagation();
        input.value = '';
        matches = [];
        close();
        input.blur();
      }
    });
  }

  // -- view ----------------------------------------------------------------------------

  const viewAt = (scale, x, y, smooth = true) => moveView(graph, scale, x, y, smooth);

  function nowNode() {
    const ready = current.nodes.filter((n) => n.data.open && !n.data.blocked);
    return (ready.length ? ready : current.nodes).reduce((a, b) => (b.data.score > a.data.score ? b : a), current.nodes[0]);
  }

  const fitAll = (smooth = true) => fitCards(graph, current.nodes, smooth);

  function openView(smooth = false) {
    if (!current.nodes.length) return;
    const svg = graph.renderer.getCanvasSelection().node();
    if (!svg.clientWidth || !svg.clientHeight) return; // not laid out yet: the resize watch retries
    const xs = current.nodes.map((n) => n.x);
    const ys = current.nodes.map((n) => n.y);
    const width = Math.max(...xs) - Math.min(...xs) + CARD_W + 96;
    const height = Math.max(...ys) - Math.min(...ys) + CARD_H + 96;
    if (Math.min(svg.clientWidth / width, svg.clientHeight / height) >= READABLE) {
      fitAll(smooth);
      return;
    }
    // Too wide to read whole: zoom in on what to do now, placed near the left so what it opens
    // up is in view to its right; never past the plan's edges; centred in height when it fits.
    const scale = compact ? 0.7 : 0.8;
    const now = nowNode();
    const viewW = svg.clientWidth / scale;
    const viewH = svg.clientHeight / scale;
    const left = Math.max(Math.min(...xs) - CARD_W / 2 - 48, now.x - CARD_W / 2 - viewW * 0.18);
    const top = height <= viewH
      ? Math.min(...ys) - CARD_H / 2 - 48 + height / 2 - viewH / 2
      : Math.max(Math.min(...ys) - CARD_H / 2 - 48, now.y - viewH / 2);
    viewAt(scale, left + viewW / 2, top + viewH / 2, smooth);
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
    const noun = { top: 'case', projects: 'project' }[current.mode] || 'task';
    count.textContent = `${total} ${noun}${total === 1 ? '' : 's'} · ${current.steps} step${current.steps === 1 ? '' : 's'}`;
    const path = current.critical;
    const criticalSummary = stage.querySelector('[data-graph-critical-summary]');
    if (criticalSummary) criticalSummary.textContent = path.nodes.length
      ? `${path.nodes.length} · ~${path.hours} h${path.unknown ? ` (${path.unknown} unestimated)` : ''}`
      : 'none';
    stage.querySelector('[data-graph-empty]').hidden = total > 0;
    const crumbs = document.querySelector('[data-graph-crumbs]');
    if (crumbs && current.breadcrumb) {
      // The path above the graph: All projects / project / case / …, the last one is here.
      crumbs.replaceChildren(...current.breadcrumb.map((step, index) => {
        const li = el('li');
        const last = index === current.breadcrumb.length - 1;
        const item = last ? el('span', 'cn-crumb-current', step.label) : el('a', '', step.label);
        if (last) item.setAttribute('aria-current', 'page');
        else item.href = step.url;
        if (index === 0) item.prepend(icon('fa-solid fa-mountain-sun'), document.createTextNode(' '));
        li.append(item);
        return li;
      }));
      const up = document.querySelector('[data-graph-up]');
      const parent = current.breadcrumb.at(-2);
      if (up) {
        up.hidden = !parent;
        if (parent) {
          up.href = parent.url;
          up.title = `Up to “${parent.label}” (Backspace)`;
        }
      }
    }
  }

  const query = () => stage.dataset.query || '';

  // -- the view, remembered per graph for this browser session ---------------------------

  const viewKey = `cn-graph-view:${window.location.pathname}?${query()}`;
  let framed = false; // the first view is set: from then on, moves are remembered

  function savedView() {
    try {
      const view = JSON.parse(window.sessionStorage.getItem(viewKey) || 'null');
      return view && [view.k, view.x, view.y].every(Number.isFinite) ? view : null;
    } catch {
      return null;
    }
  }

  const saveView = debounce(() => {
    if (!graph || !framed) return;
    const t = graph.renderer.getZoomTransform();
    const svg = graph.renderer.getCanvasSelection().node();
    if (!svg.clientWidth) return;
    const view = { k: t.k, x: (svg.clientWidth / 2 - t.x) / t.k, y: (svg.clientHeight / 2 - t.y) / t.k };
    try {
      window.sessionStorage.setItem(viewKey, JSON.stringify(view));
    } catch {
      // storage full or refused: the view is simply not remembered
    }
  }, 300);

  async function load() {
    current = await api(`/graph?${query()}`);
    summary();
    graph = new Pivotick(canvas, { nodes: current.nodes, edges: current.edges }, options());
    // Cairn frames the view itself (from the pinned places). Pivotick's own first fit waits for
    // the HTML cards to stop changing size (up to ~3 s) before saying `ready`, then measures the
    // SVG, which misses the cards: it is turned off on this instance. It runs after two awaits
    // in Pivotick's start, so replacing it here, right after the constructor, is in time.
    graph.renderer.fitAndCenterWhenSettled = () => Promise.resolve();
    // Back on a view seen in this session (Up from a case, say): where it was left. Otherwise
    // the opening view. Until the owner moves it, a stage that gets its size late is framed again.
    const saved = savedView();
    let touched = Boolean(saved);
    graph.on('ready', () => {
      if (saved) viewAt(saved.k, saved.x, saved.y, false);
      else openView(true);
      framed = true;
    });
    canvas.addEventListener('pointerdown', () => { touched = true; }, { once: true });
    canvas.addEventListener('wheel', () => { touched = true; }, { once: true, passive: true });
    new ResizeObserver(() => { if (!touched) openView(false); }).observe(canvas);
    stage.classList.remove('cn-graph-loading');
  }

  /** Apply what changed since the last load without rebuilding the graph. */
  async function refresh() {
    const next = await api(`/graph?${query()}`);
    applyChanges(graph, current, next);
    current = next;
    summary();
    drawTable();
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
      else if (action === 'fit') fitAll();
      else if (action === 'link') setLinking(!linking);
      else if (action === 'table') setTable(!tableOn);
      else openView(true);
    });
  });
  stage.querySelector('[data-graph-critical]')?.addEventListener('change', (event) => lightCritical(event.target.checked));
  stage.addEventListener('mouseleave', hidePeek);
  const finder = stage.querySelector('[data-graph-find]');
  if (finder) setupFind(finder);
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') {
      hidePanel();
      hidePeek();
      if (linking) setLinking(false);
    }
    const typing = event.composedPath()[0]?.matches?.('input, textarea, select, [contenteditable]');
    const up = document.querySelector('[data-graph-up]');
    if (!typing && !compact && event.key === 'Backspace' && up && !up.hidden) {
      event.preventDefault();
      window.location.assign(up.href);
    }
    if (!typing && !compact && event.key.toLowerCase() === 'l' && !event.ctrlKey && !event.metaKey && !event.altKey) {
      setLinking(!linking);
    }
    if (!typing && !compact && event.key.toLowerCase() === 't' && !event.ctrlKey && !event.metaKey && !event.altKey) {
      setTable(!tableOn);
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
