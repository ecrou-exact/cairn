/** Task page: say so when this task changes elsewhere (another tab, Claude, a module). */

import { subscribe } from '../core/events.js';

const header = document.getElementById('task');
const notice = document.getElementById('task-changed');
subscribe('task.changed', ({ payload }) => {
  if (payload.id === header?.dataset.taskId && notice) notice.hidden = false;
});
