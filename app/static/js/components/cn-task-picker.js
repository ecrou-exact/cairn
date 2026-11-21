/**
 * <cn-task-picker name="other_id" exclude="<task id>" label="…">: a search field that
 * finds tasks by title (GET /api/search) and puts the chosen task's id in a hidden input
 * named `name`. Keyboard: arrows move, Enter picks, Escape closes (ARIA combobox).
 */

import { api, debounce } from '../core/api.js';

let counter = 0;

class CnTaskPicker extends HTMLElement {
  #input;
  #hidden;
  #list;
  #items = [];
  #active = -1;

  connectedCallback() {
    if (this.#input) return;
    const id = `task-picker-${++counter}`;
    const label = document.createElement('label');
    label.className = 'visually-hidden';
    label.htmlFor = id;
    label.textContent = this.getAttribute('label') || 'Task';
    this.#input = document.createElement('input');
    Object.assign(this.#input, { id, type: 'search', className: 'form-control', placeholder: 'Search a task…', autocomplete: 'off' });
    this.#input.setAttribute('role', 'combobox');
    this.#input.setAttribute('aria-expanded', 'false');
    this.#input.setAttribute('aria-controls', `${id}-list`);
    this.#input.setAttribute('aria-autocomplete', 'list');
    this.#hidden = document.createElement('input');
    Object.assign(this.#hidden, { type: 'hidden', name: this.getAttribute('name') || 'task_id' });
    this.#list = document.createElement('ul');
    this.#list.id = `${id}-list`;
    this.#list.className = 'cn-picker-list';
    this.#list.setAttribute('role', 'listbox');
    this.#list.hidden = true;
    this.replaceChildren(label, this.#input, this.#hidden, this.#list);

    this.#input.addEventListener('input', debounce(() => this.#search(), 180));
    this.#input.addEventListener('input', () => { this.#hidden.value = ''; });
    this.#input.addEventListener('keydown', (event) => this.#key(event));
    this.#input.addEventListener('blur', () => setTimeout(() => this.#close(), 150));
  }

  async #search() {
    const q = this.#input.value.trim();
    if (q.length < 2) return this.#close();
    const data = await api(`/search?${new URLSearchParams({ q })}`).catch(() => ({ tasks: [] }));
    const exclude = this.getAttribute('exclude');
    this.#items = data.tasks.filter((task) => task.id !== exclude);
    this.#active = this.#items.length ? 0 : -1;
    this.#render();
  }

  #render() {
    const rows = this.#items.map((task, index) => {
      const li = document.createElement('li');
      li.id = `${this.#list.id}-${index}`;
      li.setAttribute('role', 'option');
      li.setAttribute('aria-selected', String(index === this.#active));
      const title = document.createElement('span');
      title.textContent = task.title;
      const meta = document.createElement('small');
      meta.textContent = [task.project, task.status].filter(Boolean).join(' · ');
      li.append(title, meta);
      li.addEventListener('mousedown', (event) => {
        event.preventDefault();
        this.#pick(index);
      });
      return li;
    });
    if (!rows.length) {
      const empty = document.createElement('li');
      empty.className = 'cn-picker-empty';
      empty.textContent = 'No task matches.';
      rows.push(empty);
    }
    this.#list.replaceChildren(...rows);
    this.#list.hidden = false;
    this.#input.setAttribute('aria-expanded', 'true');
    this.#input.setAttribute('aria-activedescendant', this.#active >= 0 ? `${this.#list.id}-${this.#active}` : '');
  }

  #key(event) {
    if (this.#list.hidden) return;
    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      event.preventDefault();
      const step = event.key === 'ArrowDown' ? 1 : -1;
      this.#active = (this.#active + step + this.#items.length) % this.#items.length;
      this.#render();
    } else if (event.key === 'Enter' && this.#active >= 0) {
      event.preventDefault();
      this.#pick(this.#active);
    } else if (event.key === 'Escape') {
      this.#close();
    }
  }

  #pick(index) {
    const task = this.#items[index];
    this.#hidden.value = task.id;
    this.#input.value = task.title;
    this.#close();
  }

  #close() {
    this.#list.hidden = true;
    this.#input.setAttribute('aria-expanded', 'false');
  }
}

if (!customElements.get('cn-task-picker')) customElements.define('cn-task-picker', CnTaskPicker);
