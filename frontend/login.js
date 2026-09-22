// Presentation-only entry screen. This is not authentication.
// Input values are never stored or sent to a server.
(() => {
  const form = document.getElementById('loginForm');
  const password = document.getElementById('loginPassword');
  const toggle = document.getElementById('loginPasswordToggle');
  const motionToggle = document.getElementById('loginMotionToggle');
  motionToggle.addEventListener('click', () => {
    const paused = document.querySelector('.login-story').classList.toggle('motion-paused');
    motionToggle.setAttribute('aria-pressed', String(paused));
    motionToggle.setAttribute('aria-label', paused ? 'Play diagram animation' : 'Pause diagram animation');
    motionToggle.textContent = paused ? '▷' : 'Ⅱ';
  });
  toggle.addEventListener('click', () => {
    const show = password.type === 'password';
    password.type = show ? 'text' : 'password';
    toggle.setAttribute('aria-label', show ? 'Hide password' : 'Show password');
    toggle.setAttribute('aria-pressed', String(show));
  });
  let entered = false;
  form.addEventListener('submit', async (event) => {
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
    // Preserve dependency order and the existing app's initialization.
    for (const src of ['https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2', './config.js', './app.js?v=20260918-outreach-replies-8']) {
      await new Promise((resolve) => {
        const script = document.createElement('script');
        script.src = src;
        script.onload = resolve;
        script.onerror = resolve;
        document.body.appendChild(script);
      });
    }
  });
})();
