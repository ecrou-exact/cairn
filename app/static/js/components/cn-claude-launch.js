/**
 * <cn-claude-launch>: open Claude Code from anywhere (D-051). One per page (in the shell);
 * opened by the header's Claude button, the palette, or any [data-claude-launch] element,
 * whose data-project / data-task / data-task-title / data-preset prefill it.
 *
 * What for: work freely, on a task, answer a pull request, fix a bug, review the changes,
 * or a new project (created with its folder, then Claude sets it up). Where: a project with
 * a local folder. The presets come from the server (`/api/claude/targets`), so the launcher,
 * the palette and the buttons say the same thing.
 */

import { api } from '../core/api.js';

const el = (tag, className, text) => {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
};
const icon = (name) => {
  const i = el('i', `fa-solid ${name}`);
  i.setAttribute('aria-hidden', 'true');
  return i;
};
let counter = 0;

class CnClaudeLaunch extends HTMLElement {
  #dialog;
  #targets = null;
  #state = { preset: 'free', project: '', task: '', taskTitle: '' };

  connectedCallback() {
    if (this.#dialog) return;
    this.#dialog = el('dialog', 'cn-dialog cn-claude-launch');
    this.#dialog.setAttribute('aria-label', 'Open Claude');
    this.append(this.#dialog);
    document.addEventListener('click', (event) => {
      const trigger = event.target.closest('[data-claude-launch]');
      if (!trigger) return;
      event.preventDefault();
      this.open(trigger.dataset);
    });
    document.addEventListener('keydown', (event) => {
      if (event.target.closest?.('.xterm, input, textarea, select, [contenteditable]')) return;
      if (event.key === 'c' && event.altKey && !event.ctrlKey && !event.metaKey) {
        event.preventDefault();
        this.open({});
      }
    });
  }

  /** Open, prefilled with `{project, task, taskTitle, preset}` (all optional). */
  async open(prefill = {}) {
    if (!this.#targets) {
      try {
        this.#targets = await api('/claude/targets');
      } catch (error) {
        const message = el('p', 'cn-claude-launch-error', `Claude cannot be opened: ${error.message}`);
        const close = el('button', 'btn btn-outline-secondary', 'Close');
        close.type = 'button';
        close.addEventListener('click', () => this.#dialog.close());
        this.#dialog.replaceChildren(message, close);
        this.#dialog.showModal();
        return;
      }
    }
    this.#state = {
      preset: prefill.preset || (prefill.task ? 'task' : 'free'),
      project: prefill.project || '',
      task: prefill.task || '',
      taskTitle: prefill.taskTitle || '',
    };
    this.#draw();
    this.#dialog.showModal();
    this.#dialog.querySelector('[data-first]')?.focus();
  }

  #draw() {
    const { presets, projects } = this.#targets;
    const form = el('form', 'cn-claude-launch-form');
    form.method = 'dialog';
    const head = el('header', 'cn-claude-launch-head');
    head.append(icon('fa-terminal'), el('h2', 'cn-dialog-title', 'Open Claude'));

    // What for
    const kinds = el('div', 'cn-claude-presets');
    kinds.setAttribute('role', 'radiogroup');
    kinds.setAttribute('aria-label', 'What for');
    for (const preset of [...presets, { key: 'new', label: 'New project', icon: 'fa-folder-plus' }]) {
      const button = el('button', 'cn-claude-preset');
      button.type = 'button';
      button.setAttribute('role', 'radio');
      button.setAttribute('aria-checked', String(this.#state.preset === preset.key));
      if (this.#state.preset === preset.key) button.dataset.first = '';
      button.append(icon(preset.icon), el('span', '', preset.label));
      button.addEventListener('click', () => {
        this.#state.preset = preset.key;
        this.#draw();
      });
      kinds.append(button);
    }

    const fields = el('div', 'cn-claude-launch-fields');
    const error = el('p', 'cn-claude-launch-error');
    error.setAttribute('role', 'alert');
    const preset = presets.find((p) => p.key === this.#state.preset);

    if (this.#state.preset === 'new') {
      fields.append(
        this.#field('Name', 'name', 'input', { required: true, placeholder: 'my-new-app', maxLength: 120 }),
        this.#field('Folder (full path, new or empty)', 'folder', 'input', { required: true, placeholder: 'C:\\Users\\me\\code\\my-new-app' }),
        this.#field('What it is for', 'description', 'textarea', { rows: 4, placeholder: 'A few lines: Claude starts from them.' }),
      );
    } else {
      const where = el('label', 'cn-claude-field');
      where.append(el('span', '', 'Project'));
      const select = el('select', 'form-select');
      select.name = 'project_id';
      select.required = !this.#state.task;
      const first = el('option', '', this.#state.task ? 'The task’s project' : 'Choose a project…');
      first.value = '';
      select.append(first);
      for (const project of projects) {
        const option = el('option', '', project.folder ? project.name : `${project.name} — no local folder yet`);
        option.value = project.id;
        option.disabled = !project.folder;
        option.selected = project.id === this.#state.project;
        select.append(option);
      }
      select.addEventListener('change', () => { this.#state.project = select.value; });
      where.append(select);
      fields.append(where);

      if (this.#state.task) {
        const chosen = el('p', 'cn-claude-task');
        chosen.append(icon('fa-list-check'), el('span', '', this.#state.taskTitle || 'This task'));
        const drop = el('button', 'btn btn-link btn-sm', 'Change');
        drop.type = 'button';
        drop.addEventListener('click', () => { this.#state.task = ''; this.#state.taskTitle = ''; this.#draw(); });
        chosen.append(drop);
        fields.append(chosen);
      } else if (preset?.asks === 'task' || this.#state.preset !== 'free') {
        const label = el('label', 'cn-claude-field');
        label.append(el('span', '', preset?.asks === 'task' ? 'Task' : 'Task (optional)'));
        const picker = document.createElement('cn-picker');
        picker.setAttribute('kind', 'tasks');
        picker.setAttribute('name', 'task_id');
        picker.setAttribute('label', 'Task');
        label.append(picker);
        fields.append(label);
      }
      if (preset) {
        const asks = preset.asks;
        const required = asks === 'url' || asks === 'text';
        const kind = asks === 'url' ? 'input' : 'textarea';
        const label = asks === 'url' ? 'Pull request' : asks === 'text' ? 'The bug' : 'Your words';
        fields.append(this.#field(label, 'detail', kind, { required, placeholder: preset.hint, rows: 3, type: asks === 'url' ? 'url' : 'text' }));
      }
    }

    const actions = el('div', 'cn-dialog-actions');
    const cancel = el('button', 'btn btn-outline-secondary', 'Cancel');
    cancel.type = 'button';
    cancel.addEventListener('click', () => this.#dialog.close());
    const go = el('button', 'btn btn-primary');
    go.type = 'submit';
    go.append(icon('fa-play'), el('span', '', this.#state.preset === 'new' ? 'Create and open Claude' : 'Open Claude'));
    actions.append(cancel, go);

    form.append(head, kinds, fields, error, actions);
    form.addEventListener('submit', (event) => {
      event.preventDefault();
      this.#submit(form, go, error);
    });
    this.#dialog.replaceChildren(form);
  }

  #field(text, name, kind, options) {
    const label = el('label', 'cn-claude-field');
    const id = `claude-launch-${++counter}`;
    const span = el('span', '', text);
    const input = el(kind, 'form-control');
    const { type, rows, ...rest } = options;
    Object.assign(input, { id, name, ...rest });
    if (kind === 'input' && type) input.type = type; // a textarea has no settable type
    if (kind === 'textarea' && rows) input.rows = rows;
    label.htmlFor = id;
    label.append(span, input);
    return label;
  }

  async #submit(form, button, error) {
    const values = Object.fromEntries(new FormData(form));
    const size = { cols: 120, rows: 32 };
    button.disabled = true;
    error.textContent = '';
    try {
      let result;
      if (this.#state.preset === 'new') {
        result = await api('/claude/projects', { method: 'POST', body: { name: values.name, folder: values.folder, description: values.description || '', ...size } });
      } else {
        const task = this.#state.task || values.task_id || null;
        const project = task ? null : values.project_id || this.#state.project || null;
        result = await api('/claude/sessions', {
          method: 'POST',
          body: { project_id: project, task_id: task, preset: this.#state.preset, detail: values.detail || '', ...size },
        });
      }
      window.location.assign(result.session.url);
    } catch (failure) {
      const details = (failure.details || []).map((d) => d.message).join(' ');
      error.textContent = details || failure.message;
      button.disabled = false;
    }
  }
}

if (!customElements.get('cn-claude-launch')) customElements.define('cn-claude-launch', CnClaudeLaunch);
