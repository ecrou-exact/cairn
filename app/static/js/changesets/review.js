/** A proposal's review (D-071): how many changes are kept; one that needs a refused one is
 *  refused with it (the server checks it again). */

const form = document.querySelector('[data-changes]');
const rows = [...form.querySelectorAll('.cn-change')];
const boxes = rows.map((row) => row.querySelector('input[name="keep"]'));
const needs = rows.map((row) => (row.dataset.needs ? row.dataset.needs.split(' ').map(Number) : []));
const kept = form.querySelector('[data-kept]');

function sync() {
  const on = boxes.map((box) => box.checked);
  let moved = true;
  while (moved) {
    moved = false;
    needs.forEach((list, place) => {
      if (on[place] && list.some((other) => !on[other])) {
        on[place] = false;
        moved = true;
      }
    });
  }
  rows.forEach((row, place) => {
    row.classList.toggle('is-refused', !on[place]);
    const note = row.querySelector('.cn-change-needs');
    if (note) note.hidden = !(boxes[place].checked && !on[place]);
  });
  kept.textContent = String(on.filter(Boolean).length);
}

form.addEventListener('change', sync);
sync();
