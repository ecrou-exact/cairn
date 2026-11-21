/**
 * Resources changed elsewhere (another tab, a job that fetched a link preview, Claude):
 * the library shows its notice for any change, a resource page for changes to itself.
 * Panels on task and project pages use core/live-panels.js.
 */

import { subscribe } from '../core/events.js';

const library = document.querySelector('[data-resource-library]');
const page = document.querySelector('[data-resource-id]');

subscribe('resource.changed', ({ payload }) => {
  if (library) library.hidden = false;
  if (page && payload.id === page.dataset.resourceId) document.getElementById('resource-changed').hidden = false;
});
