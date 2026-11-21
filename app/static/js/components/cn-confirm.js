/**
 * <cn-confirm>: asks before a form is sent.
 *
 *   <cn-confirm message="Cancel this job?" confirm-label="Cancel job">
 *     <form method="post" …>…</form>
 *   </cn-confirm>
 *
 * Without JavaScript the form is sent directly (the server action is still the one that
 * counts). With it, submitting opens a native <dialog>: Escape or "Keep" closes it, the
 * confirm button sends the form. Focus starts on the safe choice.
 */

class CnConfirm extends HTMLElement {
  #dialog = null;
  #confirmed = false;

  connectedCallback() {
    if (this.#dialog) return;
    this.#dialog = this.#build();
    this.append(this.#dialog);
    this.addEventListener('submit', (event) => {
      if (this.#confirmed) return;
      event.preventDefault();
      this.#dialog.showModal();
      this.#dialog.querySelector('[data-role="cancel"]').focus();
    });
  }

  #build() {
    const dialog = document.createElement('dialog');
    dialog.className = 'cn-dialog';
    const title = document.createElement('h2');
    title.className = 'cn-dialog-title';
    title.id = `${this.id || 'confirm'}-${crypto.randomUUID().slice(0, 8)}`;
    title.textContent = this.getAttribute('message') || 'Are you sure?';
    dialog.setAttribute('aria-labelledby', title.id);

    const detail = this.getAttribute('detail');
    const text = document.createElement('p');
    text.className = 'cn-dialog-text';
    text.textContent = detail || '';
    text.hidden = !detail;

    const actions = document.createElement('div');
    actions.className = 'cn-dialog-actions';
    const cancel = document.createElement('button');
    cancel.type = 'button';
    cancel.className = 'btn btn-outline-secondary';
    cancel.dataset.role = 'cancel';
    cancel.textContent = this.getAttribute('cancel-label') || 'Keep';
    cancel.addEventListener('click', () => dialog.close());
    const confirm = document.createElement('button');
    confirm.type = 'button';
    confirm.className = this.hasAttribute('danger') ? 'btn btn-danger' : 'btn btn-primary';
    confirm.textContent = this.getAttribute('confirm-label') || 'Confirm';
    confirm.addEventListener('click', () => {
      dialog.close();
      this.#confirmed = true;
      this.querySelector('form')?.requestSubmit();
      this.#confirmed = false;
    });
    actions.append(cancel, confirm);
    dialog.append(title, text, actions);
    return dialog;
  }
}

if (!customElements.get('cn-confirm')) customElements.define('cn-confirm', CnConfirm);
