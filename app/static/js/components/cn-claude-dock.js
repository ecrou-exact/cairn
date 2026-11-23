/**
 * <cn-claude-dock>: Cairn's main Claude beside every page (D-063). Open or folded (remembered in
 * the `cn_dock` cookie, read by the server so the page never jumps); folding leaves Claude
 * running, Stop closes it, Relaunch takes up its conversation again. Its terminal is a page of
 * its own in a frame: the looser style policy a terminal needs stays there.
 *
 * It tells Cairn which page is in front, so "do this here" means something (`current_page`).
 */

import { api } from '../core/api.js';
import { subscribe } from '../core/events.js';

const root = document.documentElement;

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text) node.textContent = text;
  return node;
}

function iconButton(name, title, act) {
  const button = el('button', 'cn-icon-button');
  button.type = 'button';
  button.title = title;
  const icon = el('i', `fa-solid ${name}`);
  icon.setAttribute('aria-hidden', 'true');
  button.append(icon, el('span', 'visually-hidden', title));
  button.addEventListener('click', act);
  return button;
}

class CnClaudeDock extends HTMLElement {
  #panel;
  #tab;
  #body;
  #note;
  #stop;
  #relaunch;
  #shown = null; // the session in the frame

  connectedCallback() {
    if (this.#panel) return;
    this.#panel = el('aside', 'cn-dock');
    this.#panel.id = 'claude-dock';
    this.#panel.setAttribute('aria-label', 'Cairn’s Claude');
    const head = el('header', 'cn-dock-head');
    const full = el('a', 'cn-icon-button');
    full.href = this.getAttribute('page');
    full.title = 'Every Claude';
    const icon = el('i', 'fa-solid fa-table-cells-large');
    icon.setAttribute('aria-hidden', 'true');
    full.append(icon, el('span', 'visually-hidden', full.title));
    this.#relaunch = iconButton('fa-rotate', 'Relaunch (its conversation goes on)', () => this.#act('restart'));
    this.#stop = iconButton('fa-stop', 'Stop it', () => this.#act('stop'));
    head.append(
      el('strong', '', 'Cairn’s Claude'),
      full,
      this.#relaunch,
      this.#stop,
      iconButton('fa-chevron-right', 'Fold (Claude goes on), Alt+J', () => this.toggle(false)),
    );
    this.#note = el('p', 'cn-dock-note');
    this.#note.setAttribute('role', 'status');
    this.#note.hidden = true;
    this.#body = el('div', 'cn-dock-body');
    this.#panel.append(head, this.#note, this.#body);
    this.#tab = el('button', 'cn-dock-tab');
    this.#tab.type = 'button';
    this.#tab.title = 'Cairn’s Claude (Alt+J)';
    this.#tab.setAttribute('aria-controls', 'claude-dock');
    const mark = el('i', 'fa-solid fa-mountain-sun');
    mark.setAttribute('aria-hidden', 'true');
    this.#tab.append(mark, el('span', '', 'Claude'));
    this.#tab.addEventListener('click', () => this.toggle(true));
    this.append(this.#panel, this.#tab);

    document.addEventListener('keydown', (event) => {
      if (event.altKey && !event.ctrlKey && !event.metaKey && event.key.toLowerCase() === 'j') {
        event.preventDefault();
        this.toggle();
      }
    });
    window.addEventListener('message', (event) => {
      if (event.origin !== window.location.origin || event.source !== this.#frame?.contentWindow) return;
      if (event.data === 'cn-dock-toggle') this.toggle();
      else if (event.data === 'cn-dock-ended') this.#load();
    });
    subscribe('claude.changed', () => { if (this.#isOpen) this.#load(); });
    const here = () => { if (!document.hidden) this.#tellPage(); };
    document.addEventListener('visibilitychange', here);
    window.addEventListener('focus', here);
    here();
    this.#sync();
  }

  get #isOpen() {
    return root.classList.contains('cn-dock-open');
  }

  get #frame() {
    return this.#body.querySelector('iframe');
  }

  #tellPage() {
    const page = { path: `${window.location.pathname}${window.location.search}`.slice(0, 500), title: document.title.slice(0, 300) };
    api('/claude/page', { method: 'POST', body: page }).catch(() => {}); // only a hint for Claude
  }

  toggle(open = !this.#isOpen) {
    root.classList.toggle('cn-dock-open', open);
    document.cookie = `cn_dock=${open ? 'open' : 'closed'}; path=/; max-age=${60 * 60 * 24 * 365}; SameSite=Strict`;
    this.#sync();
    if (open) this.#frame?.focus();
    else this.#tab.focus();
  }

  #sync() {
    const open = this.#isOpen;
    this.#panel.hidden = !open;
    this.#tab.hidden = open;
    this.#tab.setAttribute('aria-expanded', String(open));
    if (open) this.#load();
  }

  async #load() {
    try {
      this.#show((await api('/claude/main')).session);
    } catch (error) {
      this.#say(error.message);
    }
  }

  #say(text = '') {
    this.#note.textContent = text;
    this.#note.hidden = !text;
  }

  #show(session) {
    const id = session?.id || '';
    this.#stop.hidden = !id;
    this.#relaunch.hidden = !id;
    if (this.#shown === id) return;
    this.#shown = id;
    if (!id) {
      const empty = el('div', 'cn-dock-empty');
      const open = el('button', 'btn btn-primary', 'Open it');
      open.type = 'button';
      open.addEventListener('click', () => this.#act('open'));
      empty.append(el('p', '', 'Cairn’s Claude is closed.'), open);
      this.#body.replaceChildren(empty);
      return;
    }
    const frame = el('iframe', 'cn-dock-frame');
    frame.title = 'Cairn’s Claude, terminal';
    frame.src = `/claude/sessions/${id}/panel`;
    this.#body.replaceChildren(frame);
  }

  async #act(action) {
    const paths = { open: '/claude/main', restart: '/claude/main/restart', stop: '/claude/main/stop' };
    const buttons = this.#panel.querySelectorAll('button');
    buttons.forEach((button) => { button.disabled = true; });
    this.#say();
    try {
      this.#show((await api(paths[action], { method: 'POST' })).session);
    } catch (error) {
      this.#say(error.message);
    } finally {
      buttons.forEach((button) => { button.disabled = false; });
    }
  }
}

if (!customElements.get('cn-claude-dock')) customElements.define('cn-claude-dock', CnClaudeDock);
