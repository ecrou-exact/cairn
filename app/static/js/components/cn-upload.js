/**
 * <cn-upload max-mb="25" paste="page"><form …><input type="file" name="files" multiple>…</form></cn-upload>
 *
 * Turns the plain file field of its form into Vitrine's <vt-upload> (drop zone, file
 * checks, thumbnails) and sends the form as soon as files are added. With `paste="page"`,
 * a file or screenshot pasted anywhere on the page (outside a text field) is uploaded too.
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

class CnUpload extends HTMLElement {
  #field = null;

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
    if (this.getAttribute('paste') === 'page') document.addEventListener('paste', (event) => this.#paste(event));
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
