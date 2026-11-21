/**
 * Calls to Cairn's own API (/api/*): JSON in and out, the CSRF header on writes, and
 * errors thrown with the server's message.
 */

const csrf = () => document.querySelector('meta[name="csrf-token"]')?.content || '';

export class ApiError extends Error {
  constructor(message, status, details) {
    super(message);
    this.status = status;
    this.details = details;
  }
}

export async function api(path, { method = 'GET', body, signal } = {}) {
  const headers = { Accept: 'application/json' };
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  if (method !== 'GET') headers['X-CSRFToken'] = csrf();
  const response = await fetch(`/api${path}`, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
    credentials: 'same-origin',
    signal,
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new ApiError(data.error || `Request failed (${response.status})`, response.status, data.details);
  return data;
}

/** Calls `fn` once input has paused for `wait` ms. */
export function debounce(fn, wait = 250) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), wait);
  };
}
