/** The Git tab opened for one pull request: its copy is brought into view (D-086). */

const wanted = document.getElementById('wanted-copy');
if (wanted) {
  wanted.scrollIntoView({ block: 'center' });
  wanted.focus({ preventScroll: true });
}
