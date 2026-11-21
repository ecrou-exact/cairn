/**
 * Panels that say when what they show changed elsewhere (another tab, a job, Claude):
 *
 *   <section data-live-target="task:<id>" data-live-events="resource.changed comment.changed">
 *     <div data-live-notice hidden>…Reload…</div>
 *
 * The notice shows when one of the events lists this target in `payload.targets`.
 */

import { subscribe } from './events.js';

for (const panel of document.querySelectorAll('[data-live-target]')) {
  const notice = panel.querySelector('[data-live-notice]');
  for (const type of (panel.dataset.liveEvents || '').split(/\s+/).filter(Boolean)) {
    subscribe(type, ({ payload }) => {
      if (notice && (payload.targets || []).includes(panel.dataset.liveTarget)) notice.hidden = false;
    });
  }
}
