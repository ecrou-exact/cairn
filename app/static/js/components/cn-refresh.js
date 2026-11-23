/**
 * <cn-refresh every="8000"><div id="x">…</div></cn-refresh>: its content is read again from the same
 * page every few seconds, only while the page is in front and nothing in it is in use (D-082).
 * Times in it (`<time data-since="epoch seconds">`) are written in the reader's own format.
 */

function paintSince(root) {
  for (const time of root.querySelectorAll('[data-since]')) {
    const at = new Date(Number(time.dataset.since) * 1000);
    time.dateTime = at.toISOString();
    time.textContent = at.toLocaleString([], { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });
  }
}

class CnRefresh extends HTMLElement {
  #timer = null;

  connectedCallback() {
    paintSince(this);
    this.#timer = setInterval(() => this.#look(), Number(this.getAttribute('every')) || 8000);
  }

  disconnectedCallback() {
    clearInterval(this.#timer);
  }

  #busy() {
    return document.hidden || document.querySelector('dialog[open]') || this.contains(document.activeElement)
      || this.querySelector('details[open]');
  }

  async #look() {
    if (this.#busy()) return;
    try {
      const answer = await fetch(window.location.href, { headers: { Accept: 'text/html' } });
      if (!answer.ok || answer.redirected) return;
      const page = new DOMParser().parseFromString(await answer.text(), 'text/html');
      const fresh = this.id ? page.getElementById(this.id) : null;
      if (!fresh || this.#busy()) return;
      this.replaceChildren(...[...fresh.childNodes].map((node) => document.importNode(node, true)));
      paintSince(this);
    } catch {
      // Cairn restarts: the next look finds it
    }
  }
}

customElements.define('cn-refresh', CnRefresh);
