/**
 * <cn-icon-field><input name="icon" …></cn-icon-field>: the icon of something, chosen with
 * Vitrine's icon picker (Font Awesome solid and brands). The text input is the no-JS fallback;
 * once the picker is ready it is hidden and follows it, in Cairn's form: `fa-rocket`,
 * `fa-brands fa-docker`.
 */

import { load } from './cn-vitrine.js';

const toPicker = (icon) => {
  const name = icon.split(/\s+/).pop().replace(/^fa-/, '');
  return name && `${icon.startsWith('fa-brands') ? 'fa-brands' : 'fa-solid'}:${name}`;
};
const toIcon = (set, name) => (name ? `${set === 'fa-brands' ? 'fa-brands ' : ''}fa-${name}` : '');

class CnIconField extends HTMLElement {
  async connectedCallback() {
    const input = this.querySelector('input');
    if (!input || this.querySelector('vt-icon-picker')) return;
    try {
      await load('icon-picker');
    } catch {
      return; // the text field stays
    }
    const picker = document.createElement('vt-icon-picker');
    picker.setAttribute('sets', 'fa-solid,fa-brands');
    picker.setAttribute('label', this.getAttribute('label') || 'Icon');
    picker.setAttribute('value', toPicker(input.value));
    picker.addEventListener('vt-change', (event) => {
      input.value = toIcon(event.detail.set, event.detail.name);
      input.dispatchEvent(new Event('input', { bubbles: true }));
    });
    input.closest('.cn-field').hidden = true;
    this.append(picker);
  }
}

if (!customElements.get('cn-icon-field')) customElements.define('cn-icon-field', CnIconField);
