/**
 * Resources changed elsewhere (another tab, a job that fetched a link preview, Claude):
 * - the library shows its "list changed" notice for any change;
 * - a resources panel (`#resources[data-target="task:<id>"]`) and a resource page
 *   (`[data-resource-id]`) show theirs only for changes that concern them.
 */

import { subscribe } from '../core/events.js';

const library = document.querySelector('[data-resource-library]');
const panel = document.querySelector('#resources[data-target]');
const page = document.querySelector('[data-resource-id]');

subscribe('resource.changed', ({ payload }) => {
  if (library) document.getElementById('list-changed').hidden = false;
  if (panel && payload.targets.includes(panel.dataset.target)) document.getElementById('resources-changed').hidden = false;
  if (page && payload.id === page.dataset.resourceId) document.getElementById('resource-changed').hidden = false;
});
