/**
 * <cn-palette>: the command palette (PROJECT_BRIEF.md §5), opened with Ctrl/Cmd+K or any
 * [data-open-palette] button.
 *
 * - Type to filter pages and actions, and to search projects, tasks and resources.
 * - "Add task: …" creates the typed text through quick add (same parser as the page).
 * - Arrows move, Enter runs, Escape closes. Everything is built with DOM methods.
 */

import { api, debounce } from '../core/api.js';
import { showHelp } from '../core/shortcuts.js';

const ACTIONS = [
  { label: 'Open Claude… (a task, a PR, a fix, a new project)', icon: 'fa-claude', run: () => document.querySelector('cn-claude-launch')?.open() },
  { label: 'Claude sessions', icon: 'fa-gauge-high', url: '/claude' },
  { label: 'New task (full form)', icon: 'fa-pen-to-square', url: '/tasks/new' },
  { label: 'New project', icon: 'fa-folder-plus', url: '/projects/new' },
  { label: 'New resource (link, note, snippet…)', icon: 'fa-paperclip', url: '/resources/new' },
  { label: 'Actionable tasks', icon: 'fa-bolt', url: '/tasks?state=actionable' },
  { label: 'Blocked tasks', icon: 'fa-link-slash', url: '/tasks?state=blocked' },
  { label: 'Overdue tasks', icon: 'fa-calendar-xmark', url: '/tasks?state=overdue' },
  { label: 'Security', icon: 'fa-shield-halved', url: '/account/security' },
  { label: 'Keyboard shortcuts', icon: 'fa-keyboard', run: () => showHelp() },
];

class CnPalette extends HTMLElement {
  #dialog;
  #input;
  #list;
  #items = [];
  #active = 0;
  #query = 0;

  connectedCallback() {
    if (this.#dialog) return;
    this.#build();
    document.addEventListener('keydown', (event) => {
      if (event.target.closest?.('.xterm')) return; // keys typed in a terminal belong to it
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault();
        this.open();
      }
    });
    document.addEventListener('click', (event) => {
      if (event.target.closest('[data-open-palette]')) this.open();
    });
  }

  #build() {
    this.#dialog = document.createElement('dialog');
    this.#dialog.className = 'cn-dialog cn-palette';
    this.#dialog.setAttribute('aria-label', 'Command palette');
    this.#input = document.createElement('input');
    Object.assign(this.#input, { type: 'search', className: 'form-control cn-palette-input', placeholder: 'Search, go to, or type a task to add…' });
    this.#input.setAttribute('role', 'combobox');
    this.#input.setAttribute('aria-controls', 'cn-palette-list');
    this.#input.setAttribute('aria-expanded', 'true');
    this.#input.setAttribute('aria-label', 'Command');
    this.#list = document.createElement('ul');
    this.#list.id = 'cn-palette-list';
    this.#list.className = 'cn-palette-list';
    this.#list.setAttribute('role', 'listbox');
    const hint = document.createElement('p');
    hint.className = 'cn-palette-hint';
    hint.textContent = '↑ ↓ to move · Enter to open · Esc to close';
    this.#dialog.append(this.#input, this.#list, hint);
    this.append(this.#dialog);

    this.#input.addEventListener('input', () => this.#refresh());
    this.#input.addEventListener('input', debounce(() => this.#search(), 160));
    this.#input.addEventListener('keydown', (event) => this.#key(event));
    this.#dialog.addEventListener('click', (event) => {
      if (event.target === this.#dialog) this.#dialog.close();
    });
  }

  open() {
    if (this.#dialog.open) return;
    this.#input.value = '';
    this.#refresh();
    this.#dialog.showModal();
    this.#input.focus();
  }

  #pages() {
    return [...document.querySelectorAll('.cn-nav-link')].map((link) => ({
      label: link.textContent.trim(),
      icon: link.querySelector('i')?.className.split(' ').find((c) => c.startsWith('fa-') && c !== 'fa-solid') || 'fa-arrow-right',
      url: link.getAttribute('href'),
      group: 'Go to',
    }));
  }

  #staticItems(q) {
    const match = (item) => !q || item.label.toLowerCase().includes(q);
    return [...this.#pages(), ...ACTIONS.map((a) => ({ ...a, group: 'Actions' }))].filter(match);
  }

  /** Last, so Enter opens what was found rather than creating a task by accident. */
  #addItem(q) {
    const text = this.#input.value.trim();
    return q.length > 2 ? [{ label: `Add task: ${text}`, icon: 'fa-plus', group: 'Create', add: text }] : [];
  }

  #refresh(found = []) {
    const q = this.#input.value.trim().toLowerCase();
    this.#items = [...this.#staticItems(q), ...found, ...this.#addItem(q)];
    this.#active = 0;
    this.#render();
  }

  async #search() {
    const q = this.#input.value.trim();
    const ticket = ++this.#query;
    if (q.length < 2) return;
    const data = await api(`/search?${new URLSearchParams({ q })}`).catch(() => null);
    if (!data || ticket !== this.#query) return; // an older answer arriving late
    const found = [
      ...data.projects.map((p) => ({ label: p.name, icon: 'fa-folder', url: p.url, group: 'Projects' })),
      ...data.tasks.map((t) => ({
        label: t.title,
        icon: t.open ? 'fa-square' : 'fa-square-check',
        url: t.url,
        group: 'Tasks',
        meta: [t.project, t.status].filter(Boolean).join(' · '),
      })),
      ...(data.resources || []).map((r) => ({ label: r.title, icon: r.icon, url: r.url, group: 'Resources', meta: r.kind })),
    ];
    this.#refresh(found);
  }

  #render() {
    let group = null;
    const nodes = [];
    this.#items.forEach((item, index) => {
      if (item.group !== group) {
        group = item.group;
        const heading = document.createElement('li');
        heading.className = 'cn-palette-group';
        heading.setAttribute('role', 'presentation');
        heading.textContent = group;
        nodes.push(heading);
      }
      const li = document.createElement('li');
      li.id = `cn-palette-${index}`;
      li.setAttribute('role', 'option');
      li.setAttribute('aria-selected', String(index === this.#active));
      const icon = document.createElement('i');
      icon.className = `fa-solid ${item.icon}`;
      icon.setAttribute('aria-hidden', 'true');
      const label = document.createElement('span');
      label.textContent = item.label;
      li.append(icon, label);
      if (item.meta) {
        const meta = document.createElement('small');
        meta.textContent = item.meta;
        li.append(meta);
      }
      li.addEventListener('mousedown', (event) => {
        event.preventDefault();
        this.#run(index);
      });
      nodes.push(li);
    });
    if (!this.#items.length) {
      const empty = document.createElement('li');
      empty.className = 'cn-palette-empty';
      empty.textContent = 'Nothing matches.';
      nodes.push(empty);
    }
    this.#list.replaceChildren(...nodes);
    this.#input.setAttribute('aria-activedescendant', this.#items.length ? `cn-palette-${this.#active}` : '');
    this.#list.querySelector('[aria-selected="true"]')?.scrollIntoView({ block: 'nearest' });
  }

  #key(event) {
    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      event.preventDefault();
      if (!this.#items.length) return;
      const step = event.key === 'ArrowDown' ? 1 : -1;
      this.#active = (this.#active + step + this.#items.length) % this.#items.length;
      this.#render();
    } else if (event.key === 'Enter') {
      event.preventDefault();
      this.#run(this.#active);
    }
  }

  async #run(index) {
    const item = this.#items[index];
    if (!item) return;
    if (item.add) {
      try {
        const data = await api('/tasks/quick', { method: 'POST', body: { text: item.add } });
        window.location.assign(data.url);
      } catch (error) {
        item.label = `Could not add: ${error.message}`;
        this.#render();
      }
      return;
    }
    if (item.run) {
      this.#dialog.close();
      item.run();
      return;
    }
    window.location.assign(item.url);
  }
}

if (!customElements.get('cn-palette')) customElements.define('cn-palette', CnPalette);
