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

/* An entry in its window, as Kimai shows it (D-105): read what is in Kimai, change the rest. */

const dialog = document.querySelector('[data-entry-dialog]');
if (dialog) {
  const places = JSON.parse(document.getElementById('kimai-places').textContent);
  const form = dialog.querySelector('form');
  const field = (name) => form.elements.namedItem(name);
  const [customer, project, activity, end] = ['customer', 'project', 'activity', 'end'].map((name) =>
    form.querySelector(`[data-${name}]`),
  );
  const minutes = (text) => {
    const [h, m] = text.split(':').map(Number);
    return h * 60 + (m || 0);
  };
  const two = (n) => String(n).padStart(2, '0');
  const fill = (select, rows, chosen) => {
    select.replaceChildren(
      ...rows.map(([value, text]) => new Option(text, value, false, String(value) === String(chosen))),
    );
  };
  const fillActivities = (chosen) => {
    const found = places.find((p) => String(p.id) === project.value);
    fill(activity, (found?.activities ?? []).map((a) => [a.id, a.name]), chosen);
  };
  const fillProjects = (chosen, act) => {
    const rows = places.filter((p) => p.customer === customer.value);
    fill(project, rows.map((p) => [p.id, p.name]), chosen);
    fillActivities(act);
  };
  const showEnd = () => {
    const at = minutes(field('begin').value) + minutes(field('duration').value);
    if (at < 24 * 60) end.value = `${two(Math.floor(at / 60))}:${two(at % 60)}`;
  };
  customer.addEventListener('change', () => fillProjects());
  project.addEventListener('change', () => fillActivities());
  field('begin').addEventListener('change', showEnd);
  field('duration').addEventListener('change', showEnd);
  end.addEventListener('change', () => {
    const long = minutes(end.value) - minutes(field('begin').value);
    if (long > 0) field('duration').value = `${Math.floor(long / 60)}:${two(long % 60)}`;
  });
  form.addEventListener('submit', () => {
    const known = project.value && activity.value && places.length;
    field('place').value = known ? `${project.value}:${activity.value}` : '';
  });
  dialog.querySelector('[data-close]').addEventListener('click', () => dialog.close());

  const open = (block) => {
    const locked = block.state === 'kimai' || block.state === 'update';
    field('entry').value = block.id;
    field('trial_day').value = block.day;
    field('trial_begin').value = block.begin;
    field('rule').value = block.rule;
    field('day').value = block.day;
    field('begin').value = block.begin;
    field('duration').value = `${Math.floor(block.minutes / 60)}:${two(block.minutes % 60)}`;
    end.value = block.end;
    field('description').value = block.description;
    field('tags').value = block.tags.join(', ');
    if (places.some((p) => p.id === block.project_id)) {
      fill(customer, [...new Set(places.map((p) => p.customer))].map((c) => [c, c]), block.customer);
      fillProjects(block.project_id, block.activity_id);
    } else {
      fill(customer, [[block.customer, block.customer]]);
      fill(project, [[block.project_id, block.project]]);
      fill(activity, [[block.activity_id, block.activity]]);
    }
    dialog.querySelector('[data-entry-fields]').disabled = locked;
    dialog.querySelector('[data-save]').hidden = locked;
    dialog.querySelector('[data-remove]').hidden = block.state !== 'draft';
    dialog.querySelector('[data-entry-note]').textContent = {
      kimai: 'Already in Kimai: it is left as it is. Change it there.',
      update: 'In Kimai, with words that changed: they are updated when you send.',
      trial: 'Only a try. Saving makes the drafts of this day.',
      draft: 'A draft: nothing is in Kimai yet.',
    }[block.state];
    dialog.showModal();
  };
  for (const button of document.querySelectorAll('[data-block]')) {
    button.addEventListener('click', () => open(JSON.parse(button.dataset.block)));
  }
}
