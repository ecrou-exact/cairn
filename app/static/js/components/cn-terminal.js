/**
 * <cn-terminal session="<id>" nonce="<style nonce>"></cn-terminal>
 *
 * A Claude Code session in a terminal (D-050), drawn by xterm.js. Output comes from
 * `/claude/sessions/<id>/stream` (SSE: the browser resumes after a dropped connection, and a
 * page that comes back replays the kept output); keys go to the API in small ordered batches;
 * the size follows the element. Emits `cn-terminal-end` when the session ends.
 *
 * xterm.js writes three <style> elements of its own: the page's CSP lets only <style>
 * carrying this response's nonce through, so they get it as they are created.
 */

import { Terminal } from '../../vendor/xterm/xterm.mjs';
import { FitAddon } from '../../vendor/xterm/addon-fit.mjs';
import { api } from '../core/api.js';

const MAX_INPUT = 32768; // the API takes up to 65536 characters at once

function allowStylesWith(nonce) {
  if (!nonce || Document.prototype.createElement.cnNonce) return;
  const original = Document.prototype.createElement;
  function createElement(tag, options) {
    const element = original.call(this, tag, options);
    if (String(tag).toLowerCase() === 'style') element.nonce = nonce;
    return element;
  }
  createElement.cnNonce = true;
  Document.prototype.createElement = createElement;
}

const token = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();

function theme() {
  return {
    background: token('--cn-chrome-bg'),
    foreground: token('--cn-chrome-text'),
    cursor: token('--cn-mark'),
    cursorAccent: token('--cn-chrome-bg'),
    selectionBackground: /^#[0-9a-f]{6}$/i.test(token('--cn-mark')) ? `${token('--cn-mark')}5c` : undefined, // xterm reads #rrggbbaa, not color-mix()
  };
}

/** A long paste in pieces the API accepts, never cut inside a surrogate pair. */
function pieces(text) {
  const found = [];
  for (let at = 0; at < text.length; ) {
    let end = Math.min(at + MAX_INPUT, text.length);
    if (end < text.length && /[\uD800-\uDBFF]/.test(text[end - 1])) end -= 1;
    found.push(text.slice(at, end));
    at = end;
  }
  return found;
}

class CnTerminal extends HTMLElement {
  #term = null;
  #fit = null;
  #notice = null;
  #source = null;
  #queue = '';
  #sending = Promise.resolve();
  #timer = 0;
  #resizeTimer = 0;
  #ended = false;

  connectedCallback() {
    if (this.#term) return;
    const id = this.getAttribute('session');
    allowStylesWith(this.nonce || this.getAttribute('nonce'));
    this.#term = new Terminal({
      fontFamily: token('--cn-font-mono') || 'monospace',
      fontSize: 13,
      lineHeight: 1.15,
      cursorBlink: true,
      scrollback: 5000,
      allowProposedApi: false,
      theme: theme(),
    });
    this.#fit = new FitAddon();
    this.#term.loadAddon(this.#fit);
    const screen = document.createElement('div');
    screen.className = 'cn-terminal-screen';
    this.append(screen);
    this.#term.open(screen);
    this.#notice = document.createElement('p');
    this.#notice.className = 'cn-terminal-notice';
    this.#notice.setAttribute('role', 'alert');
    this.#notice.hidden = true;
    this.append(this.#notice);

    this.#term.onData((data) => this.#type(id, data));
    this.#term.onResize(({ cols, rows }) => {
      clearTimeout(this.#resizeTimer);
      this.#resizeTimer = setTimeout(() => {
        if (!this.#ended) api(`/claude/sessions/${id}/resize`, { method: 'POST', body: { cols, rows } }).catch(() => {});
      }, 120);
    });
    // after the listeners: the program must get this first size too
    this.#fitNow();
    new ResizeObserver(() => this.#fitNow()).observe(this);

    this.#source = new EventSource(`/claude/sessions/${id}/stream?after=0`);
    this.#source.addEventListener('message', (event) => {
      const { t } = JSON.parse(event.data);
      if (t) this.#term.write(t);
    });
    this.#source.addEventListener('end', () => this.#end());
    this.#term.focus();
  }

  disconnectedCallback() {
    this.#source?.close();
  }

  #fitNow() {
    try {
      this.#fit.fit();
    } catch {
      // not laid out yet: the observer fits it once it has a size
    }
  }

  /** Keys are sent in order, a few milliseconds' worth at a time. */
  #type(id, data) {
    if (this.#ended) return;
    this.#queue += data;
    clearTimeout(this.#timer);
    this.#timer = setTimeout(() => {
      const typed = this.#queue;
      this.#queue = '';
      for (const chunk of pieces(typed)) this.#sending = this.#sending.then(() => this.#send(id, chunk));
    }, 8);
  }

  async #send(id, data) {
    try {
      await api(`/claude/sessions/${id}/input`, { method: 'POST', body: { data } });
      this.#notice.hidden = true;
    } catch (error) {
      if (error.status === 409) {
        this.#end();
        return;
      }
      this.#notice.textContent = `Not sent: ${error.message}`;
      this.#notice.hidden = false;
    }
  }

  #end() {
    if (this.#ended) return;
    this.#ended = true;
    this.#source?.close();
    this.#term.options.cursorBlink = false;
    this.#term.write('\r\n\x1b[2m— session ended —\x1b[0m\r\n');
    this.classList.add('is-ended');
    this.dispatchEvent(new CustomEvent('cn-terminal-end', { bubbles: true }));
  }

  /** Close the session (like closing its terminal). */
  async stop() {
    await api(`/claude/sessions/${this.getAttribute('session')}/stop`, { method: 'POST' });
  }

  focus() {
    this.#term?.focus();
  }
}

if (!customElements.get('cn-terminal')) customElements.define('cn-terminal', CnTerminal);
