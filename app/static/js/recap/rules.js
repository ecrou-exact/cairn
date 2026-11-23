/** The rules (D-078): narrow the projects and activities as you type; every word must be there. */

const filter = document.getElementById('place-filter');
const place = document.getElementById('place');
if (filter && place) {
  filter.hidden = false;
  filter.addEventListener('input', () => {
    const words = filter.value.toLowerCase().split(/\s+/).filter(Boolean);
    for (const group of place.querySelectorAll('optgroup')) {
      let shown = 0;
      for (const option of group.children) {
        const text = option.dataset.words.toLowerCase();
        option.hidden = !words.every((word) => text.includes(word));
        if (!option.hidden) shown += 1;
      }
      group.hidden = shown === 0;
    }
  });
}
