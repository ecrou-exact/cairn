/** A project's or a task's resources (D-096): copy a content or an address, choose some for a zip. */

for (const button of document.querySelectorAll('[data-copy-source], [data-copy-text]')) {
  button.addEventListener('click', async () => {
    const text = button.dataset.copyText ?? JSON.parse(document.getElementById(button.dataset.copySource).textContent);
    const icon = button.querySelector('i');
    try {
      await navigator.clipboard.writeText(text);
      icon.className = 'fa-solid fa-check';
    } catch {
      icon.className = 'fa-solid fa-xmark';
    }
    setTimeout(() => { icon.className = 'fa-regular fa-copy'; }, 1500);
  });
}

for (const form of document.querySelectorAll('[data-resource-zip]')) {
  const boxes = () => [...document.querySelectorAll(`input[name="resource_ids"][form="${form.id}"]`)];
  const all = form.querySelector('[data-zip-all]');
  const button = form.querySelector('button[type="submit"]');
  const sync = () => {
    const on = boxes().filter((box) => box.checked).length;
    button.disabled = on === 0;
    all.checked = on > 0 && on === boxes().length;
    all.indeterminate = on > 0 && on < boxes().length;
  };
  all.addEventListener('change', () => { for (const box of boxes()) box.checked = all.checked; sync(); });
  document.addEventListener('change', (event) => { if (event.target.matches(`input[form="${form.id}"]`)) sync(); });
  sync();
}
