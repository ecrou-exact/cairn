/** The day summary (D-078): copy it; nothing is sent while an entry has changes not saved. */

for (const button of document.querySelectorAll('[data-copy]')) {
  const label = button.querySelector('span');
  button.addEventListener('click', async () => {
    const text = JSON.parse(document.getElementById(button.dataset.copy).textContent);
    try {
      await navigator.clipboard.writeText(text);
      label.textContent = 'Copied';
    } catch {
      label.textContent = 'Not copied: select the text';
    }
  });
}

const send = document.querySelector('[data-send]');
const unsaved = document.querySelector('[data-unsaved]');
for (const form of document.querySelectorAll('[data-entry]')) {
  form.addEventListener('input', () => {
    if (!send) return;
    send.disabled = true;
    unsaved.hidden = false;
  });
}

for (const form of document.querySelectorAll('[data-slow]')) {
  form.addEventListener('submit', () => {
    const button = form.querySelector('button');
    button.disabled = true;
    button.querySelector('span').textContent = form.dataset.slow;
  });
}
