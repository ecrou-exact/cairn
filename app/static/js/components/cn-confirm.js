/**
 * Confirmation before a destructive action, with a native <dialog>.
 *
 * - `confirmDialog({ message, detail, confirmLabel, cancelLabel, danger })` → Promise<boolean>,
 *   for scripts.
 * - <cn-confirm message="…" detail="…" confirm-label="…" danger><form>…</form></cn-confirm>
 *   asks before its form is sent. Without JavaScript the form is sent directly (the server
 *   action is still the one that counts). Focus starts on the safe choice; Escape keeps.
 */

export function confirmDialog({ message, detail = '', confirmLabel = 'Confirm', cancelLabel = 'Keep', danger = false }) {
  return new Promise((resolve) => {
    const dialog = document.createElement('dialog');
    dialog.className = 'cn-dialog';
    const title = document.createElement('h2');
    title.className = 'cn-dialog-title';
    title.id = `confirm-${crypto.randomUUID().slice(0, 8)}`;
    title.textContent = message || 'Are you sure?';
    dialog.setAttribute('aria-labelledby', title.id);
    const text = document.createElement('p');
    text.className = 'cn-dialog-text';
    text.textContent = detail;
    text.hidden = !detail;
    const actions = document.createElement('div');
    actions.className = 'cn-dialog-actions';
    const keep = document.createElement('button');
    keep.type = 'button';
    keep.className = 'btn btn-outline-secondary';
    keep.textContent = cancelLabel;
    const go = document.createElement('button');
    go.type = 'button';
    go.className = danger ? 'btn btn-danger' : 'btn btn-primary';
    go.textContent = confirmLabel;
    actions.append(keep, go);
    dialog.append(title, text, actions);

    let answer = false;
    keep.addEventListener('click', () => dialog.close());
    go.addEventListener('click', () => {
      answer = true;
      dialog.close();
    });
    dialog.addEventListener('close', () => {
      dialog.remove();
      resolve(answer);
    });
    document.body.append(dialog);
    dialog.showModal();
    keep.focus();
  });
}

class CnConfirm extends HTMLElement {
  #confirmed = false;

  connectedCallback() {
    this.addEventListener('submit', async (event) => {
      if (this.#confirmed) return;
      event.preventDefault();
      const ok = await confirmDialog({
        message: this.getAttribute('message'),
        detail: this.getAttribute('detail') || '',
        confirmLabel: this.getAttribute('confirm-label') || 'Confirm',
        cancelLabel: this.getAttribute('cancel-label') || 'Keep',
        danger: this.hasAttribute('danger'),
      });
      if (!ok) return;
      this.#confirmed = true;
      event.target.requestSubmit(event.submitter || undefined);
      this.#confirmed = false;
    });
  }
}

if (!customElements.get('cn-confirm')) customElements.define('cn-confirm', CnConfirm);
