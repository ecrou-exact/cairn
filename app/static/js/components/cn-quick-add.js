/**
 * <cn-quick-add>: wraps the quick-add text field and shows, while you type, what Cairn
 * understood (project, dates, type, tags, priority, estimate, assignee) and open tasks
 * that look like the same thing. The form still posts normally; this only previews.
 */

import { api, debounce } from '../core/api.js';

const ICONS = {
  project: 'fa-folder', due: 'fa-calendar-day', do: 'fa-calendar-check', type: 'fa-shapes', tag: 'fa-hashtag',
  priority: 'fa-flag', estimate: 'fa-hourglass-half', assignee: 'fa-user', hard: 'fa-lock',
};

class CnQuickAdd extends HTMLElement {
  #preview;
  #controller = null;

  connectedCallback() {
    const input = this.querySelector('input[name="text"]');
    if (!input || this.#preview) return;
    this.#preview = document.createElement('div');
    this.#preview.className = 'cn-quick-preview';
    this.#preview.setAttribute('aria-live', 'polite');
    this.closest('form').after(this.#preview);
    input.addEventListener('input', debounce(() => this.#update(input.value), 220));
  }

  async #update(text) {
    this.#controller?.abort();
    if (!text.trim()) {
      this.#preview.replaceChildren();
      return;
    }
    this.#controller = new AbortController();
    const body = { text };
    if (this.getAttribute('project-id')) body.project_id = this.getAttribute('project-id');
    let data;
    try {
      data = await api('/tasks/parse', { method: 'POST', body, signal: this.#controller.signal });
    } catch {
      return; // the preview is a help; the form still works without it
    }
    this.#render(data);
  }

  #render({ title, understood, similar }) {
    const nodes = [];
    if (title || understood.length) {
      const line = document.createElement('div');
      line.className = 'cn-quick-chips';
      const titleChip = document.createElement('span');
      titleChip.className = 'cn-quick-title';
      titleChip.textContent = title || '(no title yet)';
      line.append(titleChip);
      for (const item of understood) {
        const chip = document.createElement('span');
        chip.className = `cn-chip cn-chip-${item.kind}`;
        const icon = document.createElement('i');
        icon.className = `fa-solid ${ICONS[item.kind] || 'fa-circle'}`;
        icon.setAttribute('aria-hidden', 'true');
        chip.append(icon, document.createTextNode(` ${item.text}`));
        line.append(chip);
      }
      nodes.push(line);
    }
    if (similar.length) {
      const warn = document.createElement('div');
      warn.className = 'cn-quick-similar';
      warn.append(document.createTextNode('Looks like an open task: '));
      similar.forEach((task, i) => {
        if (i) warn.append(document.createTextNode(', '));
        const link = document.createElement('a');
        link.href = task.url;
        link.textContent = task.title;
        warn.append(link);
      });
      nodes.push(warn);
    }
    this.#preview.replaceChildren(...nodes);
  }
}

if (!customElements.get('cn-quick-add')) customElements.define('cn-quick-add', CnQuickAdd);
