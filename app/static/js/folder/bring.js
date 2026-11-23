/** Bring in (D-081): choose a whole group at once; at most 100 things are taken together. */

const MOST = 100;
const form = document.querySelector('.cn-bring');
const count = document.querySelector('[data-bring-count]');
const boxes = (root = form) => [...root.querySelectorAll('input[name="keys"]')];

function sync(note = '') {
  const chosen = boxes().filter((box) => box.checked).length;
  for (const group of form.querySelectorAll('[data-bring-group]')) {
    const all = group.querySelector('[data-bring-all]');
    const mine = boxes(group);
    const on = mine.filter((box) => box.checked).length;
    all.checked = on > 0 && on === Math.min(mine.length, MOST);
    all.indeterminate = on > 0 && !all.checked;
  }
  count.textContent = note || (chosen ? `${chosen} chosen (at most ${MOST})` : '');
}

if (form) {
  form.addEventListener('change', (event) => {
    if (event.target.matches('[data-bring-all]')) {
      const group = event.target.closest('[data-bring-group]');
      let room = MOST - boxes().filter((box) => box.checked && !group.contains(box)).length;
      for (const box of boxes(group)) {
        box.checked = event.target.checked && room > 0;
        if (box.checked) room -= 1;
      }
      sync(room <= 0 && event.target.checked ? `At most ${MOST} at a time: the rest next.` : '');
      return;
    }
    if (event.target.checked && boxes().filter((box) => box.checked).length > MOST) {
      event.target.checked = false;
      sync(`At most ${MOST} at a time: the rest next.`);
      return;
    }
    sync();
  });
  sync();
}
