const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || '';

async function apiRequest(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      'X-CSRF-Token': csrfToken,
      ...(options.headers || {}),
    },
  });
  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const body = await response.json();
      if (body.detail) message = body.detail;
    } catch (_) {
      // Keep the generic message.
    }
    throw new Error(message);
  }
  return response.status === 204 ? null : response.json();
}

function showError(element, message) {
  if (!element) return;
  element.textContent = message;
  element.hidden = false;
}

function reloadAfter(promise) {
  promise.then(() => window.location.reload()).catch((error) => window.alert(error.message));
}

document.getElementById('create-form')?.addEventListener('submit', (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const payload = {
    front: form.elements.front.value,
    back: form.elements.back.value,
  };
  reloadAfter(apiRequest('/api/cards', { method: 'POST', body: JSON.stringify(payload) }));
});

document.getElementById('shuffle-btn')?.addEventListener('click', () => {
  reloadAfter(apiRequest('/api/deck/shuffle', { method: 'POST' }));
});

document.querySelectorAll('.edit-form').forEach((form) => {
  form.addEventListener('submit', (event) => {
    event.preventDefault();
    const card = form.closest('.card');
    const payload = {
      front: form.elements.front.value,
      back: form.elements.back.value,
    };
    reloadAfter(
      apiRequest(`/api/cards/${card.dataset.cardId}`, {
        method: 'PATCH',
        body: JSON.stringify(payload),
      })
    );
  });
});

document.addEventListener('click', (event) => {
  const flip = event.target.closest('.flip-button');
  if (flip) {
    const isFlipped = flip.getAttribute('aria-pressed') === 'true';
    flip.setAttribute('aria-pressed', String(!isFlipped));
    flip.closest('.card').classList.toggle('is-flipped', !isFlipped);
    return;
  }

  const edit = event.target.closest('.edit-btn');
  if (edit) {
    const card = edit.closest('.card');
    card.querySelector('.edit-form').hidden = false;
    card.querySelector('.flip-button').hidden = true;
    return;
  }

  const cancel = event.target.closest('.cancel-edit');
  if (cancel) {
    const card = cancel.closest('.card');
    card.querySelector('.edit-form').hidden = true;
    card.querySelector('.flip-button').hidden = false;
    return;
  }

  const remove = event.target.closest('.delete-btn');
  if (remove && window.confirm('Delete this card?')) {
    const card = remove.closest('.card');
    reloadAfter(apiRequest(`/api/cards/${card.dataset.cardId}`, { method: 'DELETE' }));
  }
});

const reviewNext = document.getElementById('review-next');
const reviewPrev = document.getElementById('review-prev');
if (reviewNext || reviewPrev) {
  document.addEventListener('keydown', (event) => {
    if (event.target.matches('input, textarea')) return;
    if (event.key === 'ArrowRight' && reviewNext) reviewNext.click();
    if (event.key === 'ArrowLeft' && reviewPrev) reviewPrev.click();
  });
}
