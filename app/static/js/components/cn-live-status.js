/**
 * <cn-live-status>: header indicator of the realtime connection. Hidden on pages that
 * do not listen to events; "Live" when connected, "Reconnecting…" otherwise.
 */

import { onConnectionState } from '../core/events.js';

const LABELS = { connecting: 'Reconnecting…', live: 'Live', closed: 'Offline' };

class CnLiveStatus extends HTMLElement {
  #stop = null;

  connectedCallback() {
    const dot = document.createElement('span');
    dot.className = 'cn-live-dot';
    dot.setAttribute('aria-hidden', 'true');
    const text = document.createElement('span');
    this.replaceChildren(dot, text);
    this.setAttribute('role', 'status');
    this.#stop = onConnectionState((state) => {
      this.hidden = state === 'idle';
      this.dataset.state = state;
      text.textContent = LABELS[state] || '';
    });
  }

  disconnectedCallback() {
    this.#stop?.();
  }
}

if (!customElements.get('cn-live-status')) customElements.define('cn-live-status', CnLiveStatus);
