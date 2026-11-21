/**
 * Keyboard shortcuts (PROJECT_BRIEF.md §5). Ctrl/Cmd+K is the palette (cn-palette.js).
 * Never active while typing in a field or an editor (including Vitrine's shadow DOM).
 */

const GO = { h: '/', t: '/tasks', p: '/projects', g: '/graph', r: '/resources', j: '/jobs', s: '/settings', x: '/trash' };
const HELP = [
  ['Ctrl K', 'Search, go to a page, add a task'],
  ['n', 'New task (quick add)'],
  ['/', 'Search in this list'],
  ['g then h', 'Today'],
  ['g then t', 'Tasks'],
  ['g then p', 'Projects'],
  ['g then g', 'Graph'],
  ['g then r', 'Resources'],
  ['g then j', 'Jobs'],
  ['g then x', 'Trash'],
  ['g then s', 'Settings'],
  ['?', 'This help'],
];
let pending = null;

function typing(event) {
  return event.composedPath().some(
    (node) => node instanceof HTMLElement && (node.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(node.tagName)),
  );
}

function focusFirst(selector) {
  const field = document.querySelector(selector);
  if (!field) return false;
  field.focus();
  field.scrollIntoView({ block: 'center', behavior: 'smooth' });
  return true;
}

function showHelp() {
  const dialog = document.createElement('dialog');
  dialog.className = 'cn-dialog cn-shortcuts';
  dialog.setAttribute('aria-label', 'Keyboard shortcuts');
  const title = document.createElement('h2');
  title.className = 'cn-dialog-title';
  title.textContent = 'Keyboard shortcuts';
  const list = document.createElement('dl');
  for (const [keys, what] of HELP) {
    const dt = document.createElement('dt');
    for (const [i, key] of keys.split(' then ').entries()) {
      if (i) dt.append(document.createTextNode(' then '));
      const kbd = document.createElement('kbd');
      kbd.textContent = key;
      dt.append(kbd);
    }
    const dd = document.createElement('dd');
    dd.textContent = what;
    list.append(dt, dd);
  }
  const close = document.createElement('button');
  close.type = 'button';
  close.className = 'btn btn-outline-secondary';
  close.textContent = 'Close';
  close.addEventListener('click', () => dialog.close());
  const actions = document.createElement('div');
  actions.className = 'cn-dialog-actions';
  actions.append(close);
  dialog.append(title, list, actions);
  dialog.addEventListener('close', () => dialog.remove());
  document.body.append(dialog);
  dialog.showModal();
  close.focus();
}

document.addEventListener('keydown', (event) => {
  if (event.ctrlKey || event.metaKey || event.altKey || typing(event) || document.querySelector('dialog[open]')) return;
  if (pending === 'g') {
    pending = null;
    if (GO[event.key]) {
      event.preventDefault();
      window.location.assign(GO[event.key]);
    }
    return;
  }
  if (event.key === 'g') {
    pending = 'g';
    setTimeout(() => { pending = null; }, 1500);
  } else if (event.key === 'n' && focusFirst('.cn-quick-add input[name="text"]')) {
    event.preventDefault();
  } else if (event.key === '/' && focusFirst('#list-q')) {
    event.preventDefault();
  } else if (event.key === '?') {
    event.preventDefault();
    showHelp();
  }
});

export { showHelp };
