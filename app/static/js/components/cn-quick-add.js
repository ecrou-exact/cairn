/**
 * <cn-quick-add>: wraps the quick-add text field and shows, while you type, what Cairn
 * understood (project, dates, type, tags, priority, estimate, assignee) and open tasks
 * that look like the same thing. Adding goes through the API: the field is emptied and keeps the
 * focus, the list of the page ([data-quick-list]) is read again in place, nothing reloads; many
 * tasks are typed one after the other. Without JavaScript the form posts.
 */

import { api, debounce } from '../core/api.js';

const ICONS = {
  project: 'fa-folder', due: 'fa-calendar-day', do: 'fa-calendar-check', type: 'fa-shapes', tag: 'fa-hashtag',
  priority: 'fa-flag', estimate: 'fa-hourglass-half', assignee: 'fa-user', hard: 'fa-lock', repeat: 'fa-repeat',
};

/** Read the page's task lists again and put them in place (no reload, the field keeps its focus). */
async function refreshLists() {
  const lists = [...document.querySelectorAll('[data-quick-list][id]')];
  if (!lists.length) return;
  const answer = await fetch(window.location.href, { headers: { Accept: 'text/html' } });
  if (!answer.ok || answer.redirected) return;
  const page = new DOMParser().parseFromString(await answer.text(), 'text/html');
  for (const list of lists) {
    const fresh = page.getElementById(list.id);
    if (fresh) list.replaceChildren(...[...fresh.childNodes].map((node) => document.importNode(node, true)));
  }
  const notice = document.getElementById('list-changed');
  if (notice) setTimeout(() => { notice.hidden = true; }, 600); // our own change, not someone else's
}

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
    this.closest('form').addEventListener('submit', (event) => this.#add(event, input));
  }

  async #add(event, input) {
    const form = event.currentTarget;
    if (event.submitter?.formAction && event.submitter.classList.contains('cn-quick-full')) return; // the full form
    event.preventDefault();
    const text = input.value.trim();
    if (!text) return;
    const body = { text };
    for (const name of ['project_id', 'parent_id']) {
      const value = form.querySelector(`input[name="${name}"]`)?.value;
      if (value) body[name] = value;
    }
    input.disabled = true;
    try {
      const made = await api('/tasks/quick', { method: 'POST', body });
      input.value = '';
      this.#preview.replaceChildren(this.#added(made));
      await refreshLists();
    } catch (error) {
      this.#preview.replaceChildren(this.#line(error.message || 'Not added.', 'cn-quick-error'));
    } finally {
      input.disabled = false;
      input.focus();
    }
  }

  #line(text, className) {
    const line = document.createElement('p');
    line.className = className;
    line.textContent = text;
    return line;
  }

  #added({ task, url }) {
    const line = this.#line('Added: ', 'cn-quick-added');
    const link = document.createElement('a');
    link.href = url;
    link.textContent = task.title;
    line.append(link, document.createTextNode('. Type the next one.'));
    return line;
  }

  async #update(text) {
    this.#controller?.abort();
    if (!text.trim()) {
      if (!this.#preview.querySelector('.cn-quick-added')) this.#preview.replaceChildren(); // keep "Added: …"
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
