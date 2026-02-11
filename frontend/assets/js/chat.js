const statusPill = document.getElementById("statusPill");
const userLine = document.getElementById("userLine");

const clearBtn = document.getElementById("clearBtn");
const logoutBtn = document.getElementById("logoutBtn");

const modeChat = document.getElementById("modeChat");
const modeVoice = document.getElementById("modeVoice");

const messageInput = document.getElementById("messageInput");
const sendBtn = document.getElementById("sendBtn");
const chatArea = document.getElementById("chatArea");

let currentMode = "chat"; // chat | voice
let inputFocused = false;

function setMode(mode) {
  currentMode = mode;
  modeChat.classList.toggle("active", mode === "chat");
  modeVoice.classList.toggle("active", mode === "voice");

  if (mode === "voice") {
    messageInput.value = "";
    messageInput.disabled = true;
    messageInput.placeholder = "Voice mode enabled (UI ready).";
  } else {
    messageInput.disabled = false;
    messageInput.placeholder = "Type your message…";
  }
  updateSendState();
}

function updateSendState() {
  const hasText = messageInput.value.trim().length > 0;
  const active = (currentMode === "chat") && hasText;
  sendBtn.disabled = !active;
}


async function ensureAuth() {
  try {
    const res = await fetch("/api/me", { credentials: "include" });
    if (!res.ok) throw new Error("unauthorized");
    const data = await res.json();
    const u = data.user;

    statusPill.textContent = "● Online";
    userLine.textContent = `${(u.userType || "user").toUpperCase()} • ${u.name || ""}`;
  } catch {
    window.location.href = "/login";
  }
}

function addBubble(text, who = "system") {
  const div = document.createElement("div");
  div.style.marginTop = "10px";
  div.style.maxWidth = "820px";
  div.style.padding = "10px 12px";
  div.style.borderRadius = "16px";
  div.style.border = "1px solid rgba(27,42,74,.65)";
  div.style.background = who === "user" ? "rgba(58,160,255,.10)" : "rgba(4,7,15,.35)";
  div.style.color = "rgba(233,238,252,.95)";
  div.textContent = text;
  chatArea.appendChild(div);
  chatArea.scrollTop = chatArea.scrollHeight;
}

// Initial auth guard
ensureAuth();

// Mode toggles
modeChat.addEventListener("click", () => setMode("chat"));
modeVoice.addEventListener("click", () => setMode("voice"));

// Input focus rule: send enabled only if focused + has text + chat mode
// messageInput.addEventListener("focus", () => { inputFocused = true; updateSendState(); });
// messageInput.addEventListener("blur", () => { inputFocused = false; updateSendState(); });
messageInput.addEventListener("input", updateSendState);
messageInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") {
    e.preventDefault();
    sendMessage();
  }
});


async function sendMessage() {
  const txt = messageInput.value.trim();
  if (!txt || currentMode !== "chat") return;

  addBubble(txt, "user");
  messageInput.value = "";
  updateSendState();

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ text: txt }),
    });

    const data = await res.json();

    if (!res.ok) {
      addBubble(data?.detail || "Not authenticated", "system");
      if (res.status === 401) window.location.href = "/login";
      return;
    }

    if (!data.ok) {
      addBubble(data.message || "Failed", "system");
      return;
    }

    addBubble(data.reply || "", "system");
  } catch (e) {
    addBubble("Network error while contacting chatbot API.", "system");
  }
}

sendBtn.addEventListener("click", sendMessage);

// Clear chat area (keeps the top hint optional)
clearBtn.addEventListener("click", () => {
  chatArea.innerHTML = "";
  addBubble("Cleared.", "system");
});

// Logout
logoutBtn.addEventListener("click", async () => {
  try {
    await fetch("/api/logout", { method: "POST", credentials: "include" });
  } finally {
    window.location.href = "/login";
  }
});

// Default mode
setMode("chat");
