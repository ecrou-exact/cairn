/** <cn-timer started="<ISO date>">: shows the elapsed time of the running timer (H:MM). */

class CnTimer extends HTMLElement {
  #tick = null;

  connectedCallback() {
    const started = Date.parse(this.getAttribute('started') || '');
    const out = this.querySelector('[data-elapsed]');
    if (Number.isNaN(started) || !out) return;
    const draw = () => {
      const minutes = Math.max(0, Math.floor((Date.now() - started) / 60000));
      out.textContent = `${Math.floor(minutes / 60)}:${String(minutes % 60).padStart(2, '0')}`;
    };
    draw();
    this.#tick = setInterval(draw, 15000);
  }

  disconnectedCallback() {
    clearInterval(this.#tick);
  }
}

if (!customElements.get('cn-timer')) customElements.define('cn-timer', CnTimer);
