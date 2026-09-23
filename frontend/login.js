// Presentation-only entry screen. This is not authentication.
// Input values are never stored or sent to a server.
(() => {
  const form = document.getElementById('loginForm');
  const password = document.getElementById('loginPassword');
  const toggle = document.getElementById('loginPasswordToggle');
  toggle.addEventListener('click', () => {
    const show = password.type === 'password';
    password.type = show ? 'text' : 'password';
    toggle.setAttribute('aria-label', show ? 'Hide password' : 'Show password');
    toggle.setAttribute('aria-pressed', String(show));
  });
  let entered = false;
  window.addEventListener('linkedin-ops:logout', () => {
    entered = false;
    form.reset();
    password.type = 'password';
    toggle.setAttribute('aria-label', 'Show password');
    toggle.setAttribute('aria-pressed', 'false');
  });
  form.addEventListener('submit', (event) => {
    event.preventDefault();
    if (entered) return;
    entered = true;
    form.reset();
    document.getElementById('loginScreen').hidden = true;
    const workspace = document.getElementById('loginWorkspace');
    workspace.hidden = false;
    workspace.inert = false;
    document.body.classList.remove('login-mode');
    const heading = workspace.querySelector('h1, h2');
    if (heading) { heading.tabIndex = -1; heading.focus(); }
  });
})();
