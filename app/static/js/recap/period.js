/** The preview of a period (D-103): what the ticked rules would send stands out. */

const ticks = [...document.querySelectorAll('input[name="rules"]')];
const total = document.querySelector('[data-chosen]');

function show() {
  const chosen = new Set(ticks.filter((tick) => tick.checked).map((tick) => tick.value));
  let minutes = 0;
  for (const chip of document.querySelectorAll('[data-rule]')) {
    const on = chosen.has(chip.dataset.rule);
    chip.classList.toggle('is-chosen', on);
    if (on) minutes += Number(chip.dataset.minutes);
  }
  if (total) {
    total.textContent = `${Math.floor(minutes / 60)}:${String(minutes % 60).padStart(2, '0')} ticked`;
  }
}

for (const tick of ticks) tick.addEventListener('change', show);
show();
