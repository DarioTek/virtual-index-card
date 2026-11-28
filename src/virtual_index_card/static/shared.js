// Shared (anonymous) deck page: flip + keyboard navigation only. No API calls,
// no CSRF token, no writes — the server exposes no mutating route for /s/.
document.addEventListener('click', (event) => {
  const flip = event.target.closest('.flip-button');
  if (!flip) return;
  const isFlipped = flip.getAttribute('aria-pressed') === 'true';
  flip.setAttribute('aria-pressed', String(!isFlipped));
  flip.closest('.card').classList.toggle('is-flipped', !isFlipped);
});

const nav = document.querySelector('.review-nav');
if (nav) {
  document.addEventListener('keydown', (event) => {
    if (event.target.matches('input, textarea') || event.target.isContentEditable) return;
    if (event.key === 'ArrowRight') nav.querySelector('[rel="next"]')?.click();
    if (event.key === 'ArrowLeft') nav.querySelector('[rel="prev"]')?.click();
  });
}
