/**
 * The account's Claude usage as gauges (D-056): the share used of each window, when it resets.
 * Shared by the menu and the Claude pages.
 */

export function remaining(resetsAt) {
  if (!resetsAt) return '';
  const seconds = Math.floor(resetsAt - Date.now() / 1000);
  if (seconds <= 0) return 'soon';
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  if (days) return `${days}d${hours}h`;
  return hours ? `${hours}h${minutes}m` : `${minutes}m`;
}

const SVG = 'http://www.w3.org/2000/svg';

function shape(tag, attributes) {
  const node = document.createElementNS(SVG, tag);
  for (const [name, value] of Object.entries(attributes)) node.setAttribute(name, value);
  return node;
}

function ring(used) {
  const svg = shape('svg', { viewBox: '0 0 36 36', width: 36, height: 36, 'aria-hidden': 'true' });
  const circle = { cx: 18, cy: 18, r: 15.9155, fill: 'none' };
  const track = shape('circle', { ...circle, class: 'cn-limit-track' });
  const fill = shape('circle', { ...circle, class: 'cn-limit-fill', 'stroke-dasharray': `${used} 100`, transform: 'rotate(-90 18 18)' });
  const value = shape('text', { x: 18, y: 18, class: 'cn-limit-value', 'text-anchor': 'middle', 'dominant-baseline': 'central' });
  value.textContent = String(used);
  svg.append(track, fill, value);
  return svg;
}

function bar(used) {
  const svg = shape('svg', { viewBox: '0 0 100 6', width: 100, height: 6, preserveAspectRatio: 'none', 'aria-hidden': 'true' });
  svg.append(shape('rect', { width: 100, height: 6, class: 'cn-limit-track' }), shape('rect', { width: used, height: 6, class: 'cn-limit-fill' }));
  return svg;
}

function words(className, text) {
  const span = document.createElement('span');
  span.className = className;
  span.textContent = text;
  return span;
}

/** One window as a gauge: a ring (header, pages) or a bar (menu). */
export function limitNode(window, at, form = 'ring') {
  const node = document.createElement('span');
  node.className = `cn-limit is-${form}`;
  node.classList.toggle('is-high', window.used >= 80);
  node.classList.toggle('is-mid', window.used >= 50 && window.used < 80);
  const reset = remaining(window.resets_at);
  const read = new Date(at * 1000).toLocaleString([], { weekday: 'short', hour: '2-digit', minute: '2-digit' });
  const told = `${window.label}: ${window.used}% used, ${window.left}% left${reset ? `, resets in ${reset}` : ''}`;
  node.title = `${told} (read ${read})`;
  node.setAttribute('role', 'img');
  node.setAttribute('aria-label', told);
  if (form === 'bar') {
    node.append(words('cn-limit-label', window.label), bar(window.used), words('cn-limit-percent', `${window.used}%`), words('cn-limit-reset', reset));
  } else {
    const text = words('cn-limit-text', '');
    text.append(words('cn-limit-label', window.label), words('cn-limit-reset', reset ? `↻ ${reset}` : ''));
    node.append(ring(window.used), text);
  }
  return node;
}
