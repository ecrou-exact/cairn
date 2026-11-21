/**
 * Task tables: selection for the bulk bar (select all, count, actions enabled only with a
 * selection), inline status/priority selects that save on change, and a confirmation for
 * bulk actions marked data-confirm. Without JavaScript everything still works by buttons.
 */

import { confirmDialog } from '../components/cn-confirm.js';

const bulk = document.getElementById('bulk-form');
const boxes = () => [...document.querySelectorAll('input[name="task_ids"][form="bulk-form"]')];
const all = document.querySelector('[data-select-all]');

function refresh() {
  if (!bulk) return;
  const selected = boxes().filter((box) => box.checked).length;
  bulk.querySelector('[data-selected-count]').textContent = selected
    ? `${selected} selected`
    : 'Select tasks to change them together';
  bulk.classList.toggle('cn-bulk-active', selected > 0);
  for (const button of bulk.querySelectorAll('button[name="action"]')) button.disabled = selected === 0;
  if (all) {
    all.checked = selected > 0 && selected === boxes().length;
    all.indeterminate = selected > 0 && selected < boxes().length;
  }
}

all?.addEventListener('change', () => {
  for (const box of boxes()) box.checked = all.checked;
  refresh();
});
document.addEventListener('change', (event) => {
  if (event.target.matches('input[name="task_ids"]')) refresh();
  if (event.target.matches('select[data-autosubmit]')) event.target.form.requestSubmit();
});

bulk?.addEventListener('submit', async (event) => {
  const button = event.submitter;
  if (!button?.dataset.confirm || button.dataset.confirmed) return;
  event.preventDefault();
  const ok = await confirmDialog({ message: button.dataset.confirm, confirmLabel: 'Move to trash', danger: true });
  if (!ok) return;
  button.dataset.confirmed = '1';
  bulk.requestSubmit(button);
});

refresh();
