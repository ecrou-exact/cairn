/**
 * <cn-vitrine>: the one way Cairn shows code, Markdown, JSON, logs and diffs (D-007, D-019).
 *
 * It loads only the Vitrine module it needs, keeps Vitrine's theme in step with Cairn's,
 * and always feeds content through the `content` property, never as markup.
 *
 *   <script type="application/json" id="x">"text"</script>
 *   <cn-vitrine kind="log" source="x" vt-variant="full"></cn-vitrine>
 *
 * - `kind`: log | json | code | markdown | diff.
 * - `source`: id of a <script type="application/json"> holding the text (a JSON string).
 * - A <textarea name> child makes it a form field: the textarea is the no-JS fallback; once
 *   upgraded it is replaced by the editor and a hidden input with the same name.
 * - `vt-*` attributes are passed to the Vitrine element without the prefix.
 */

import { configure } from '../../vendor/vitrine/esm/api.js';

const KINDS = new Set(['log', 'json', 'code', 'markdown', 'diff']);
const DARK_THEMES = new Set(['basalt', 'ember']);
const loading = new Map();

function vitrineTheme() {
  const theme = document.documentElement.dataset.theme || 'auto';
  if (theme === 'auto') return 'auto';
  return DARK_THEMES.has(theme) ? 'dark' : 'light';
}

function syncTheme() {
  configure({ theme: vitrineTheme(), lightTheme: 'light', darkTheme: 'dark' });
}

syncTheme();
new MutationObserver(syncTheme).observe(document.documentElement, { attributeFilter: ['data-theme'] });

function load(kind) {
  if (!loading.has(kind)) loading.set(kind, import(`../../vendor/vitrine/esm/vt-${kind}.js`));
  return loading.get(kind);
}

function readSource(id) {
  const node = id ? document.getElementById(id) : null;
  if (!node || node.type !== 'application/json') return '';
  const value = JSON.parse(node.textContent || '""');
  return typeof value === 'string' ? value : JSON.stringify(value, null, 2);
}

export class CnVitrine extends HTMLElement {
  #viewer = null;
  #pending = '';

  async connectedCallback() {
    if (this.#viewer) return;
    const kind = this.getAttribute('kind');
    if (!KINDS.has(kind)) throw new Error(`cn-vitrine: unknown kind "${kind}"`);

    const textarea = this.querySelector('textarea[name]');
    const content = textarea ? textarea.value : readSource(this.getAttribute('source'));
    let status = null;
    if (!textarea) {
      // A form field keeps its textarea until the editor is ready; a viewer shows a status.
      status = document.createElement('p');
      status.className = 'cn-loading';
      status.setAttribute('role', 'status');
      status.textContent = 'Loading…';
      this.replaceChildren(status);
    }
    try {
      await load(kind);
    } catch {
      loading.delete(kind); // the next element may try again
      if (status) {
        status.className = 'cn-load-error';
        status.textContent = 'This content could not be displayed: the viewer failed to load. Reload the page.';
      }
      return;
    }

    const viewer = document.createElement(`vt-${kind}`);
    for (const { name, value } of this.attributes) {
      if (name.startsWith('vt-')) viewer.setAttribute(name.slice(3), value);
    }
    if (textarea) {
      const field = document.createElement('input');
      field.type = 'hidden';
      field.name = textarea.name;
      field.value = textarea.value;
      viewer.addEventListener('vt-input', (event) => {
        field.value = event.detail.value;
      });
      this.replaceChildren(field, viewer);
    } else {
      this.replaceChildren(viewer);
    }
    viewer.content = content + this.#pending;
    this.#pending = '';
    this.#viewer = viewer;
    this.dispatchEvent(new CustomEvent('cn-ready', { bubbles: true }));
  }

  /** Append text to a live log; lines written before the viewer is ready are kept. */
  write(text) {
    if (this.#viewer && typeof this.#viewer.write === 'function') this.#viewer.write(text);
    else this.#pending += text;
  }

  get viewer() {
    return this.#viewer;
  }
}

if (!customElements.get('cn-vitrine')) customElements.define('cn-vitrine', CnVitrine);
