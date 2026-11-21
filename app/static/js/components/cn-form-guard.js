/**
 * <cn-form-guard> inside a form: once a field changed, leaving the page asks first
 * (the browser's own dialog). Submitting the form, or putting it back as it was, clears it.
 */

class CnFormGuard extends HTMLElement {
  connectedCallback() {
    const form = this.closest('form');
    if (!form) return;
    const snapshot = () => new URLSearchParams(new FormData(form)).toString();
    let initial = null;
    let submitting = false;
    // Editors (cn-vitrine) replace their textarea when ready: take the reference after that.
    requestAnimationFrame(() => setTimeout(() => { initial = snapshot(); }, 400));
    form.addEventListener('submit', () => { submitting = true; });
    window.addEventListener('beforeunload', (event) => {
      if (!submitting && initial !== null && snapshot() !== initial) event.preventDefault();
    });
  }
}

if (!customElements.get('cn-form-guard')) customElements.define('cn-form-guard', CnFormGuard);
