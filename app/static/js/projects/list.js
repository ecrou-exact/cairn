/**
 * The projects list (D-089): star, pin and hide in place, one project or the chosen ones, through
 * the API; the page is not reloaded. The pinned group of the menu follows. Without JavaScript the
 * same buttons post their forms.
 */

import { api } from '../core/api.js';

const bulk = document.querySelector('[data-project-bulk]');
const boxes = () => [...document.querySelectorAll('input[name="project_ids"][form="bulk-form"]')];
const all = document.querySelector('[data-select-all]');
const hiddenView = new URLSearchParams(window.location.search).get('hidden') === '1';

function paint(button, on) {
  button.classList.toggle('is-on', on);
  button.setAttribute('aria-pressed', String(on));
  const title = on ? button.dataset.onTitle : button.dataset.offTitle;
  button.title = title;
  button.querySelector('i').className = on ? button.dataset.on : button.dataset.off;
  button.querySelector('.visually-hidden').textContent = title;
}

function menuPin(marks, on) {
  let list = document.querySelector('[aria-labelledby="nav-pinned"]');
  const id = marks.dataset.projectMarks;
  if (!on) {
    list?.querySelector(`[data-pinned="${id}"]`)?.remove();
    if (list && !list.children.length) {
      document.getElementById('nav-pinned')?.remove();
      list.remove();
    }
    return;
  }
  if (!list) {
    const title = document.createElement('p');
    title.className = 'cn-nav-group';
    title.id = 'nav-pinned';
    title.textContent = 'Pinned';
    list = document.createElement('ul');
    list.className = 'cn-nav';
    list.setAttribute('aria-labelledby', 'nav-pinned');
    document.querySelector('.cn-sidebar-foot')?.before(title, list);
  }
  if (list.querySelector(`[data-pinned="${id}"]`)) return;
  const item = document.createElement('li');
  item.dataset.pinned = id;
  const link = document.createElement('a');
  link.className = 'cn-nav-link';
  link.href = marks.dataset.url;
  link.title = marks.dataset.name;
  const icon = document.createElement('i');
  icon.className = `fa-solid ${marks.dataset.icon}`;
  icon.setAttribute('aria-hidden', 'true');
  const label = document.createElement('span');
  label.className = 'cn-nav-label';
  label.textContent = marks.dataset.name;
  link.append(icon, label);
  item.append(link);
  list.append(item);
}

/** One project's mark set to `on`; a hidden project leaves this list. */
async function set(marks, field, on) {
  await api(`/projects/${marks.dataset.projectMarks}`, { method: 'PATCH', body: { [field]: on } });
  paint(marks.querySelector(`[data-field="${field}"]`), on);
  if (field === 'pinned') menuPin(marks, on);
  if (field === 'hidden' && on !== hiddenView) marks.closest('li.cn-card, tr')?.remove();
}

document.addEventListener('click', async (event) => {
  const button = event.target.closest('.cn-mark');
  if (!button) return;
  event.preventDefault();
  const marks = button.closest('[data-project-marks]');
  try {
    await set(marks, button.dataset.field, button.getAttribute('aria-pressed') !== 'true');
  } catch {
    button.form.requestSubmit(); // the page way, when the API refuses
  }
});

function refresh() {
  if (!bulk) return;
  const chosen = boxes().filter((box) => box.checked).length;
  bulk.querySelector('[data-selected-count]').textContent = chosen
    ? `${chosen} chosen`
    : 'Choose projects to change them together';
  bulk.classList.toggle('cn-bulk-active', chosen > 0);
  if (all) {
    all.checked = chosen > 0 && chosen === boxes().length;
    all.indeterminate = chosen > 0 && chosen < boxes().length;
  }
}

all?.addEventListener('change', () => {
  for (const box of boxes()) box.checked = all.checked;
  refresh();
});
document.addEventListener('change', (event) => {
  if (event.target.matches('input[name="project_ids"]')) refresh();
});

const ACTIONS = {
  star: ['starred', true], unstar: ['starred', false],
  pin: ['pinned', true], unpin: ['pinned', false],
  hide: ['hidden', true], show: ['hidden', false],
};
const SERVER_ONLY = new Set(['pause', 'resume']); // the page shows the state: done by the form

bulk?.addEventListener('submit', async (event) => {
  if (SERVER_ONLY.has(event.submitter?.value)) return;
  const action = ACTIONS[event.submitter?.value];
  if (!action) return;
  event.preventDefault();
  const chosen = boxes().filter((box) => box.checked);
  try {
    for (const box of chosen) {
      const marks = document.querySelector(`[data-project-marks="${box.value}"]`);
      await set(marks, ...action);
    }
  } catch {
    bulk.requestSubmit(event.submitter);
    return;
  }
  for (const box of boxes()) box.checked = false;
  refresh();
});

refresh();
