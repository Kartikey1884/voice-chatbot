const form = document.getElementById("loginForm");
const statusEl = document.getElementById("status");
const errorBox = document.getElementById("errorBox");
const loginBtn = document.getElementById("loginBtn");

function setStatus(text) { statusEl.textContent = text; }
function setError(text) { errorBox.textContent = text || ""; }

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  setError("");

  const userName = document.getElementById("userName").value.trim();
  const password = document.getElementById("password").value.trim();
  const registrationToken = document.getElementById("registrationToken").value.trim();

  if (!userName || !password || !registrationToken) {
    setError("All fields are required.");
    return;
  }

  loginBtn.disabled = true;
  setStatus("Logging in...");

  try {
    const res = await fetch("/api/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ userName, password, registrationToken })
    });

    const data = await res.json();

    if (!data.ok) {
      setStatus("Failed");
      setError(data.message || "Login failed.");
      loginBtn.disabled = false;
      return;
    }

    setStatus("Success");
    window.location.href = "/chat";
  } catch (err) {
    setStatus("Error");
    setError("Network error. Check server and try again.");
    loginBtn.disabled = false;
  }
});
