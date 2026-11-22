/**
 * <cn-upload max-mb="25" paste="page"><form …><input type="file" name="files" multiple>…</form></cn-upload>
 *
 * Turns the plain file field of its form into Vitrine's <vt-upload> (drop zone, file
 * checks, thumbnails) and sends the form as soon as files are added. With `paste="page"`,
 * a file or screenshot pasted anywhere on the page (outside a text field), or files dropped
 * anywhere on it (a full-page overlay says where they go), are uploaded too.
 * Styles: `css/components/upload.css` (Vitrine's parts in Cairn's look, `is-dragging`).
 * Without JavaScript the plain field and its button still work.
 */

import { load } from './cn-vitrine.js';

function editable(node) {
  return node instanceof HTMLElement && (node.isContentEditable || node.matches('input, textarea, select, [contenteditable]'));
}

function stamp() {
  const now = new Date();
  const pad = (n) => String(n).padStart(2, '0');
  return `${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}-${pad(now.getHours())}${pad(now.getMinutes())}${pad(now.getSeconds())}`;
}

/** Screenshots arrive as "image.png": give them a name worth keeping in the library. */
function named(file, index) {
  if (file.name && file.name !== 'image.png') return file;
  const extension = (file.type.split('/')[1] || 'png').replace('jpeg', 'jpg');
  return new File([file], `pasted-${stamp()}${index ? `-${index}` : ''}.${extension}`, { type: file.type });
}

/** Whether a drag carries files (not text or a link being dragged around the page). */
function carriesFiles(event) {
  return [...(event.dataTransfer?.types ?? [])].includes('Files');
}

function dropOverlay(title, detail) {
  const overlay = document.createElement('div');
  overlay.className = 'cn-drop-overlay';
  overlay.hidden = true;
  overlay.setAttribute('aria-hidden', 'true');
  const card = document.createElement('div');
  card.className = 'cn-drop-card';
  const icon = document.createElement('i');
  icon.className = 'fa-solid fa-cloud-arrow-up';
  const strong = document.createElement('strong');
  strong.textContent = title;
  const span = document.createElement('span');
  span.textContent = detail;
  card.append(icon, strong, span);
  overlay.append(card);
  document.body.append(overlay);
  return overlay;
}

class CnUpload extends HTMLElement {
  #field = null;
  #depth = 0; // dragenter / dragleave pairs over this zone

  async connectedCallback() {
    if (this.#field) return;
    const form = this.querySelector('form');
    const input = form?.querySelector('input[type="file"]');
    if (!input) return;
    try {
      await load('upload');
    } catch {
      return; // the plain field stays and works
    }
    const field = document.createElement('vt-upload');
    field.setAttribute('name', input.name);
    if (input.multiple) field.setAttribute('multiple', '');
    if (this.getAttribute('max-mb')) field.setAttribute('max-size', `${this.getAttribute('max-mb')}MB`);
    const label = form.querySelector(`label[for="${input.id}"]`);
    field.setAttribute('label', this.getAttribute('label') || label?.textContent.trim() || 'Files');
    if (this.getAttribute('hint')) field.setAttribute('hint', this.getAttribute('hint'));
    label?.remove();
    input.replaceWith(field);
    for (const button of form.querySelectorAll('[data-upload-submit]')) button.hidden = true;
    field.addEventListener('vt-change', () => {
      if (field.files.length) queueMicrotask(() => form.requestSubmit());
    });
    this.#field = field;
    this.addEventListener('dragenter', (event) => { if (carriesFiles(event)) { this.#depth += 1; this.classList.add('is-dragging'); } });
    this.addEventListener('dragleave', () => { this.#depth = Math.max(0, this.#depth - 1); if (!this.#depth) this.classList.remove('is-dragging'); });
    this.addEventListener('drop', () => { this.#depth = 0; this.classList.remove('is-dragging'); });
    if (this.getAttribute('paste') === 'page') {
      document.addEventListener('paste', (event) => this.#paste(event));
      this.#dropAnywhere();
    }
  }

  /** Files dropped anywhere on the page go to this field; an overlay shows it while dragging. */
  #dropAnywhere() {
    const overlay = dropOverlay(`Drop to add to ${this.getAttribute('target') || 'the library'}`, `Up to ${this.getAttribute('max-mb') || '25'} MB each`);
    let depth = 0;
    const inside = (event) => event.composedPath().includes(this);
    const hide = () => { depth = 0; overlay.hidden = true; };
    document.addEventListener('dragenter', (event) => {
      if (!carriesFiles(event)) return;
      depth += 1;
      overlay.hidden = inside(event); // over the zone itself, the zone lights up instead
    });
    document.addEventListener('dragleave', () => { depth = Math.max(0, depth - 1); if (!depth) overlay.hidden = true; });
    document.addEventListener('dragover', (event) => {
      if (!carriesFiles(event)) return;
      event.preventDefault(); // allow the drop anywhere
      overlay.hidden = inside(event);
    });
    document.addEventListener('drop', (event) => {
      if (!carriesFiles(event)) return;
      hide();
      if (inside(event)) return; // Vitrine's zone takes it
      event.preventDefault();
      const files = [...event.dataTransfer.files];
      if (files.length) this.#field.addFiles(files.map(named));
    });
    window.addEventListener('blur', hide);
  }

  #paste(event) {
    if (editable(event.composedPath()[0])) return;
    const files = [...(event.clipboardData?.files ?? [])];
    if (!files.length) return;
    event.preventDefault();
    this.#field.addFiles(files.map(named));
  }
}

if (!customElements.get('cn-upload')) customElements.define('cn-upload', CnUpload);
