/**
 * Patches the job pieces of the current page (status pill, progress, attempts) from
 * `job.*` events. Shared by the Jobs list and the job page.
 */

export function applyJobChange(payload) {
  const id = CSS.escape(payload.id);
  for (const pill of document.querySelectorAll(`[data-status-for="${id}"]`)) {
    pill.className = `cn-status cn-status-${payload.status}`;
    pill.textContent = payload.status;
  }
  if (typeof payload.progress === 'number') applyProgress(payload);
  for (const cell of document.querySelectorAll(`[data-attempts-for="${id}"]`)) {
    const max = cell.textContent.split('/')[1]?.trim();
    cell.textContent = max ? `${payload.attempts} / ${max}` : String(payload.attempts);
  }
}

export function applyProgress(payload) {
  const id = CSS.escape(payload.id);
  for (const cell of document.querySelectorAll(`[data-progress-for="${id}"]`)) {
    cell.textContent = `${payload.progress}%`;
  }
  for (const meter of document.querySelectorAll(`[data-meter-for="${id}"]`)) {
    meter.value = payload.progress;
  }
}
