/** Pages listing tasks or projects: say so when the plan changed after the page loaded. */

import { subscribe } from '../core/events.js';

const notice = document.getElementById('list-changed');
const show = () => { if (notice) notice.hidden = false; };
subscribe('task.changed', show);
subscribe('project.changed', show);
