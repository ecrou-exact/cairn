/**
 * Drop-down menus (`details.cn-menu`, D-048): they open without script; this closes an open
 * menu on a click outside it or on Escape (focus back on its button), and keeps one open at
 * a time. Also used for the folded filters (`details.cn-list-more`).
 */

const MENUS = 'details.cn-menu[open], details.cn-list-more[open]';

document.addEventListener('pointerdown', (event) => {
  for (const menu of document.querySelectorAll(MENUS)) {
    if (!menu.contains(event.target)) menu.open = false;
  }
});

document.addEventListener('keydown', (event) => {
  if (event.key !== 'Escape') return;
  const menu = event.target.closest?.(MENUS) || document.querySelector(MENUS);
  if (!menu) return;
  menu.open = false;
  menu.querySelector('summary')?.focus();
});

document.addEventListener('toggle', (event) => {
  const opened = event.target;
  if (!(opened instanceof HTMLDetailsElement) || !opened.open || !opened.matches('.cn-menu, .cn-list-more')) return;
  for (const menu of document.querySelectorAll(MENUS)) if (menu !== opened) menu.open = false;
}, true);
