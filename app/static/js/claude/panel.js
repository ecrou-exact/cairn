/** The dock's frame (D-063): tells the page around it what happens in the terminal. */

const tell = (what) => window.parent.postMessage(what, window.location.origin);

document.addEventListener('cn-terminal-end', () => tell('cn-dock-ended'));
document.addEventListener(
  'keydown',
  (event) => {
    if (event.altKey && !event.ctrlKey && !event.metaKey && event.key.toLowerCase() === 'j') {
      event.preventDefault();
      event.stopPropagation(); // not a key for the terminal
      tell('cn-dock-toggle');
    }
  },
  true,
);
