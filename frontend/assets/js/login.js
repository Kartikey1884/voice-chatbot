const msg = document.getElementById('msg');
const loader = document.getElementById('loader');
const btn = document.getElementById('loginBtn');
const togglePassword = document.getElementById('togglePassword');

togglePassword.addEventListener('click', () => {
  const passwordInput = document.getElementById('password');
  const type = passwordInput.getAttribute('type') === 'password' ? 'text' : 'password';
  passwordInput.setAttribute('type', type);
});

btn.onclick = async () => {
  msg.textContent = 'Logging in...';
  loader.style.display = 'inline-block';
  btn.disabled = true;

  const body = {
    userName: document.getElementById('userName').value.trim(),
    password: document.getElementById('password').value,
    registrationToken: document.getElementById('registrationToken').value.trim(),
  };

  try {
    const res = await fetch('/api/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    });

    const data = await res.json().catch(() => ({
      ok: false,
      message: 'Invalid response'
    }));

    if (data.ok) {
      msg.textContent = 'Success. Redirecting...';
      msg.style.color = '#4ade80';
      window.location.href = '/chat';
    } else {
      msg.textContent = data.message || 'Login failed';
      msg.style.color = '#f87171';
    }
  } catch (err) {
    msg.textContent = 'Network error. Please try again.';
    msg.style.color = '#f87171';
  }

  loader.style.display = 'none';
  btn.disabled = false;
};