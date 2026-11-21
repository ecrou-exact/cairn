/**
 * The main menu: on wide screens the toggle folds the sidebar to icons (remembered in the
 * `cn_nav` cookie, which the server reads so the page never jumps); on phones it opens the
 * sidebar as a drawer over the page, closed by the backdrop, Escape or following a link.
 */

const root = document.documentElement;
const toggle = document.querySelector('[data-nav-toggle]');
const sidebar = document.getElementById('sidebar');
const backdrop = document.querySelector('[data-nav-close]');
const phone = window.matchMedia('(max-width: 768px)');

function remember(collapsed) {
  const year = 60 * 60 * 24 * 365;
  document.cookie = `cn_nav=${collapsed ? 'collapsed' : 'open'}; path=/; max-age=${year}; SameSite=Strict`;
}

function setDrawer(open) {
  root.classList.toggle('cn-nav-open', open);
  backdrop.hidden = !open;
  toggle.setAttribute('aria-expanded', String(open));
  if (open) sidebar.querySelector('a')?.focus();
}

function sync() {
  const expanded = phone.matches ? root.classList.contains('cn-nav-open') : !root.classList.contains('cn-nav-collapsed');
  toggle.setAttribute('aria-expanded', String(expanded));
  if (!phone.matches) setDrawer(false);
}

toggle?.addEventListener('click', () => {
  if (phone.matches) {
    setDrawer(!root.classList.contains('cn-nav-open'));
  } else {
    const collapsed = root.classList.toggle('cn-nav-collapsed');
    remember(collapsed);
    sync();
  }
});
backdrop?.addEventListener('click', () => setDrawer(false));
document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape' && root.classList.contains('cn-nav-open')) {
    setDrawer(false);
    toggle.focus();
  }
});
sidebar?.addEventListener('click', (event) => {
  if (phone.matches && event.target.closest('a')) setDrawer(false);
});
phone.addEventListener('change', sync);
sync();
