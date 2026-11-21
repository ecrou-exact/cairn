/**
 * Client event bus over the `GET /events` Server-Sent Events stream (D-020).
 *
 *   import { subscribe } from '/static/js/core/events.js';
 *   subscribe('job', (event) => { ... event.type, event.payload ... });
 *
 * One connection per tab, opened on the first subscription. Topics are prefixes
 * (`job` receives `job.changed`, `job.log`…). The page may set
 * <meta name="cn-events-after" content="<id>"> to the last event id it was rendered
 * with, so nothing that happened between rendering and connecting is missed. The browser
 * reconnects by itself; the stream resumes from its last id and duplicates are dropped.
 */

const handlers = new Map(); // topic -> Set<handler>
const seen = new Set();
const SEEN_LIMIT = 2000;
const stateListeners = new Set();
let source = null;
let openTopics = '';
let scheduled = false;
let state = 'idle';

function setState(next) {
  if (next === state) return;
  state = next;
  for (const listener of stateListeners) listener(state);
}

function topicsKey() {
  return [...handlers.keys()].sort().join(',');
}

function startAfter() {
  const meta = document.querySelector('meta[name="cn-events-after"]');
  return meta && /^\d+$/.test(meta.content) ? meta.content : null;
}

function deliver(message) {
  let event;
  try {
    event = JSON.parse(message.data);
  } catch {
    return;
  }
  if (seen.has(event.id)) return;
  seen.add(event.id);
  if (seen.size > SEEN_LIMIT) seen.delete(seen.values().next().value);
  for (const [topic, set] of handlers) {
    if (event.type === topic || event.type.startsWith(`${topic}.`)) {
      for (const handler of set) handler(event);
    }
  }
}

function connect() {
  scheduled = false;
  const key = topicsKey();
  if (source && key === openTopics) return;
  if (source) source.close();
  openTopics = key;
  const params = new URLSearchParams({ topics: key });
  const after = startAfter();
  if (after !== null) params.set('after', after);
  source = new EventSource(`/events?${params}`);
  setState('connecting');
  source.addEventListener('open', () => setState('live'));
  source.addEventListener('error', () => setState(source.readyState === EventSource.CLOSED ? 'closed' : 'connecting'));
  source.addEventListener('message', deliver);
}

/** Calls `handler(event)` for every event whose type starts with `topic`. Returns an unsubscribe function. */
export function subscribe(topic, handler) {
  if (!/^[a-z][a-z_]*(\.[a-z_]+)*$/.test(topic)) throw new Error(`Invalid topic "${topic}"`);
  if (!handlers.has(topic)) handlers.set(topic, new Set());
  handlers.get(topic).add(handler);
  if (!scheduled) {
    scheduled = true;
    queueMicrotask(connect); // subscriptions made in the same task share one connection
  }
  return () => handlers.get(topic)?.delete(handler);
}

/** `listener(state)` with state = idle | connecting | live | closed, now and on every change. */
export function onConnectionState(listener) {
  stateListeners.add(listener);
  listener(state);
  return () => stateListeners.delete(listener);
}
