/** The machine's instances (D-079): looked at again every few seconds, left alone while in use. */

const EVERY = 8000;
const list = document.querySelector('[data-machine]');

function paintSince() {
  for (const time of list.querySelectorAll('[data-instance-since]')) {
    const at = new Date(Number(time.dataset.instanceSince) * 1000);
    time.dateTime = at.toISOString();
    time.textContent = at.toLocaleString([], { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });
  }
}

async function look() {
  if (document.hidden || document.querySelector('dialog[open]') || list.contains(document.activeElement)) return;
  try {
    const answer = await fetch(window.location.href, { headers: { Accept: 'text/html' } });
    if (!answer.ok || answer.redirected) return;
    const page = new DOMParser().parseFromString(await answer.text(), 'text/html');
    const fresh = page.querySelector('[data-machine]');
    if (!fresh || list.contains(document.activeElement) || document.querySelector('dialog[open]')) return;
    list.replaceChildren(...[...fresh.childNodes].map((node) => document.importNode(node, true)));
    paintSince();
  } catch {
    // the server restarts: the next look finds it
  }
}

paintSince();
setInterval(look, EVERY);
