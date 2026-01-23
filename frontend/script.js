let textWs = null;
let voiceWs = null;

let mediaRecorder = null;
let audioChunks = [];
let isRecording = false;
let sessionId = crypto.randomUUID();
let currentBotMessage = null;
let currentMode = 'text';

const statusEl = document.getElementById("status");
const statusBadgeEl = document.getElementById("statusBadge");
const messagesEl = document.getElementById("messages");
const voiceBtnEl = document.getElementById("voiceBtn");
const textInputEl = document.getElementById("textInput");
const sendBtnEl = document.getElementById("sendBtn");
const textModeEl = document.getElementById("textMode");

/* -------- START TEXT SOCKET -------- */
connectTextWebSocket();

/* -------- MODE SWITCH -------- */
function switchMode(mode, btn) {
    currentMode = mode;

    document.querySelectorAll('.mode-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');

    if (mode === 'voice') {
        textModeEl.classList.add('hidden');
        voiceBtnEl.classList.remove('hidden');
        connectVoiceWebSocket();
        setStatus("Click the microphone to start");
    } else {
        textModeEl.classList.remove('hidden');
        voiceBtnEl.classList.add('hidden');
        connectTextWebSocket();
        setStatus("Type your message and press Send");
    }
}

/* -------- TEXT SOCKET -------- */
function connectTextWebSocket() {
    if (textWs && textWs.readyState === WebSocket.OPEN) return;

    setStatus("Connecting to text chat...");
    updateBadge("Connecting", "rgba(255,165,0,0.2)");

    textWs = new WebSocket("ws://localhost:8000/ws/text");

    textWs.onopen = () => {
        setStatus("Connected! Ready to chat");
        updateBadge("Connected", "rgba(76,175,80,0.2)");
    };

    textWs.onmessage = handleTextMessage;
    textWs.onerror = () => setStatus("Text chat connection error");
}

/* -------- VOICE SOCKET -------- */
function connectVoiceWebSocket() {
    if (voiceWs && voiceWs.readyState === WebSocket.OPEN) return;

    setStatus("Connecting to voice chat...");
    updateBadge("Connecting", "rgba(255,165,0,0.2)");

    voiceWs = new WebSocket("ws://localhost:8000/ws/voice");

    voiceWs.onopen = () => {
        setStatus("Click the microphone to start");
        updateBadge("Connected", "rgba(76,175,80,0.2)");
    };

    voiceWs.onmessage = handleVoiceMessage;
}

/* -------- TEXT -------- */
function sendTextMessage() {
    const text = textInputEl.value.trim();
    if (!text) return;

    if (!textWs || textWs.readyState !== WebSocket.OPEN) {
        setStatus("Not connected to server");
        return;
    }

    addMessage("user", text);
    textInputEl.value = "";
    setStatus("Assistant thinking...");

    textWs.send(JSON.stringify({
        type: "text",
        text: text,
        session_id: sessionId
    }));
}

function handleTextMessage(event) {
    const data = JSON.parse(event.data);

    if (data.type === "text_chunk") {
        if (!currentBotMessage) currentBotMessage = addMessage("bot", "", true);
        currentBotMessage.textContent += data.text;
    }

    if (data.type === "text_complete") {
        currentBotMessage = null;
        setStatus("Type your message");
    }
}

function handleKeyPress(event) {
    if (event.key === "Enter") sendTextMessage();
}

/* -------- VOICE -------- */
async function toggleVoice() {
    if (!isRecording) startRecording();
    else stopRecording();
}

async function startRecording() {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder = new MediaRecorder(stream);
    audioChunks = [];

    mediaRecorder.ondataavailable = e => audioChunks.push(e.data);
    mediaRecorder.start();

    isRecording = true;
    voiceBtnEl.classList.add("recording");
    voiceBtnEl.textContent = "⏹";
}

async function stopRecording() {
    mediaRecorder.stop();
    isRecording = false;

    mediaRecorder.onstop = () => {
        const blob = new Blob(audioChunks, { type: "audio/wav" });
        const reader = new FileReader();
        reader.onloadend = () => {
            voiceWs.send(JSON.stringify({
                type: "audio",
                audio: reader.result.split(",")[1],
                session_id: sessionId
            }));
        };
        reader.readAsDataURL(blob);
    };

    voiceBtnEl.classList.remove("recording");
    voiceBtnEl.textContent = "🎤";
}

/* -------- VOICE MESSAGE -------- */
function handleVoiceMessage(event) {
    const data = JSON.parse(event.data);

    if (data.type === "transcription") {
        addMessage("user", data.text);
    }

    if (data.type === "audio") {
        addMessage("bot", data.text);
        const audio = new Audio("data:audio/mp3;base64," + data.audio);
        audio.play();
    }
}

/* -------- UI -------- */
function addMessage(role, text, streaming = false) {
    const row = document.createElement("div");
    row.className = `msg ${role}`;

    const bubble = document.createElement("div");
    bubble.className = "bubble";
    if (streaming) bubble.classList.add("streaming-text");
    bubble.textContent = text;

    row.appendChild(bubble);
    messagesEl.appendChild(row);
    return bubble;
}

function clearChat() {
    messagesEl.innerHTML = "";
    sessionId = crypto.randomUUID();
}

function setStatus(text) {
    statusEl.textContent = text;
}

function updateBadge(text, color) {
    statusBadgeEl.textContent = text;
    statusBadgeEl.style.background = color;
}
