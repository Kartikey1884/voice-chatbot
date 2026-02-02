/**
 * script.js
 * ─────────
 * Dual-WebSocket chat client.
 *
 * Key behaviours (matching the sample's logic):
 *   • ONE sessionId for the whole page — shared between text & voice sockets.
 *   • Voice recording auto-stops after 1 s of silence (analyser-based).
 *   • Raw audio is converted to WAV before sending (Whisper-friendly; also
 *     works fine if you swap to a server-side STT later).
 *   • After the bot finishes speaking, recording auto-restarts (ChatGPT style).
 *   • Barge-in: starting the mic while the bot is speaking sends
 *     "user_speaking" → server echoes "interrupt_audio" → client pauses audio.
 *   • Idle timeouts (follow-up at 12 s, goodbye at 20 s) are handled server-
 *     side; the client just reacts to "session_end".
 *   • Clear chat generates a NEW sessionId and reconnects.
 */

/* ── globals ───────────────────────────────────────────────── */
let textWs  = null;
let voiceWs = null;

let mediaRecorder   = null;
let audioChunks     = [];
let isRecording     = false;
let audioContext    = null;
let analyser        = null;
let silenceTimer    = null;

let sessionId       = crypto.randomUUID();   // shared across both sockets
let currentMode     = "text";
let currentBotMessage = null;                // bubble element being streamed into
let isPlayingAudio  = false;
let currentAudio    = null;                  // <Audio> element currently playing
let autoStartEnabled = true;                 // controls mic auto-restart

/* ── DOM refs ──────────────────────────────────────────────── */
const statusEl      = document.getElementById("status");
const statusBadge   = document.getElementById("statusBadge");
const messagesEl    = document.getElementById("messages");
const voiceBtnEl    = document.getElementById("voiceBtn");
const textInputEl   = document.getElementById("textInput");
const sendBtnEl     = document.getElementById("sendBtn");
const textModeEl    = document.getElementById("textMode");

/* ════════════════════════════════════════════════════════════
   MODE SWITCH
   ════════════════════════════════════════════════════════════ */
function switchMode(mode, btn) {
    const prev = currentMode;
    currentMode = mode;

    document.querySelectorAll(".mode-btn").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");

    if (mode === "voice") {
        textModeEl.classList.add("hidden");
        voiceBtnEl.classList.remove("hidden");

        if (textWs && textWs.readyState === WebSocket.OPEN) { textWs.close(); textWs = null; }
        connectVoiceWS();
        if (prev === "text") addMessage("system", "🎤 Switched to voice mode — your conversation continues");
        setStatus("Connecting to voice chat…");
    } else {
        textModeEl.classList.remove("hidden");
        voiceBtnEl.classList.add("hidden");

        if (isRecording) stopRecording();
        if (currentAudio) { currentAudio.pause(); currentAudio = null; isPlayingAudio = false; }
        if (voiceWs && voiceWs.readyState === WebSocket.OPEN) { voiceWs.close(); voiceWs = null; }

        connectTextWS();
        if (prev === "voice") addMessage("system", "💬 Switched to text mode — your conversation continues");
        setStatus("Type your message and press Send");
    }
}

/* ════════════════════════════════════════════════════════════
   TEXT WEBSOCKET
   ════════════════════════════════════════════════════════════ */
function connectTextWS() {
    if (textWs && textWs.readyState === WebSocket.OPEN) return;

    setStatus("Connecting…");
    updateBadge("Connecting", "rgba(66,133,244,0.2)");

    textWs = new WebSocket(`ws://${location.host}/ws/text`);

    textWs.onopen = () => {
        setStatus("Connected! Ready to chat");
        updateBadge("Connected", "rgba(66,133,244,0.2)");
    };

    textWs.onmessage  = handleTextMsg;

    textWs.onerror = () => {
        setStatus("Text connection error");
        updateBadge("Error", "rgba(239,68,68,0.2)");
        addMessage("system", "⚠️ Text connection error. Is the server running?");
    };

    textWs.onclose = () => {
        setStatus("Text chat disconnected");
        updateBadge("Disconnected", "rgba(158,158,158,0.2)");
    };
}

function sendTextMessage() {
    const text = textInputEl.value.trim();
    if (!text) return;
    if (!textWs || textWs.readyState !== WebSocket.OPEN) {
        setStatus("Not connected"); updateBadge("Disconnected", "rgba(239,68,68,0.2)"); return;
    }

    addMessage("user", text);
    textInputEl.value = "";
    setStatus("Thinking…");

    textWs.send(JSON.stringify({ type: "text", text, session_id: sessionId }));
}

function handleTextMsg(evt) {
    const d = JSON.parse(evt.data);

    if (d.type === "text_chunk") {
        if (!currentBotMessage) currentBotMessage = addMessage("bot", "", true);
        currentBotMessage.textContent += d.text;
        messagesEl.scrollTop = messagesEl.scrollHeight;
    }
    if (d.type === "text_complete") {
        currentBotMessage = null;
        setStatus("Type your message");
    }
    if (d.type === "error") {
        setStatus("Error: " + d.message);
        addMessage("system", "⚠️ " + d.message);
    }
}

function handleKeyPress(e) {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendTextMessage(); }
}

/* ════════════════════════════════════════════════════════════
   VOICE WEBSOCKET
   ════════════════════════════════════════════════════════════ */
function connectVoiceWS() {
    if (voiceWs && voiceWs.readyState === WebSocket.OPEN) return;

    setStatus("Connecting to voice chat…");
    updateBadge("Connecting", "rgba(66,133,244,0.2)");

    voiceWs = new WebSocket(`ws://${location.host}/ws/voice`);

    voiceWs.onopen = () => {
        setStatus("Connecting…");
        updateBadge("Connected", "rgba(66,133,244,0.2)");
        // Request greeting with the shared session so history carries over
        voiceWs.send(JSON.stringify({ type: "greet", session_id: sessionId }));
    };

    voiceWs.onmessage = handleVoiceMsg;

    voiceWs.onerror = () => {
        setStatus("Voice connection error");
        updateBadge("Error", "rgba(239,68,68,0.2)");
        addMessage("system", "⚠️ Voice connection error. Is the server running?");
    };

    voiceWs.onclose = () => {
        setStatus("Voice chat disconnected");
        updateBadge("Disconnected", "rgba(158,158,158,0.2)");
    };
}

/* ════════════════════════════════════════════════════════════
   VOICE RECORDING  (mic → silence detection → WAV → send)
   ════════════════════════════════════════════════════════════ */
async function toggleVoice() {
    if (isPlayingAudio) { setStatus("Please wait for the assistant to finish…"); return; }
    if (!isRecording) { autoStartEnabled = true;  startRecording(); }
    else              { autoStartEnabled = false; stopRecording(); }
}

async function startRecording() {
    if (isRecording) return;

    // Notify server so it can pause idle timers & interrupt audio
    if (voiceWs && voiceWs.readyState === WebSocket.OPEN)
        voiceWs.send(JSON.stringify({ type: "user_speaking" }));

    try {
        const stream = await navigator.mediaDevices.getUserMedia({
            audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true }
        });

        audioContext = new AudioContext();
        const source = audioContext.createMediaStreamSource(stream);
        analyser     = audioContext.createAnalyser();
        analyser.fftSize = 2048;
        source.connect(analyser);

        mediaRecorder = new MediaRecorder(stream);
        audioChunks   = [];
        mediaRecorder.ondataavailable = e => audioChunks.push(e.data);
        mediaRecorder.start();

        isRecording = true;
        voiceBtnEl.classList.add("recording");
        voiceBtnEl.textContent = "⏹";
        setStatus("Listening… (auto-stops on silence)");

        detectSilence();
    } catch (err) {
        let msg = "Microphone access denied";
        if (err.name === "NotAllowedError") msg = "⚠️ Mic permission denied. Allow it in browser settings.";
        else if (err.name === "NotFoundError") msg = "⚠️ No microphone found.";
        else if (err.name === "NotReadableError") msg = "⚠️ Mic is in use by another app.";
        setStatus(msg);
        addMessage("system", msg);
    }
}

function detectSilence() {
    const buf = new Uint8Array(analyser.fftSize);

    (function check() {
        analyser.getByteTimeDomainData(buf);

        let max = 0;
        for (let i = 0; i < buf.length; i++) {
            const v = Math.abs(buf[i] - 128);
            if (v > max) max = v;
        }

        if (max < 5) {
            if (!silenceTimer) silenceTimer = setTimeout(() => stopRecording(), 1000);
        } else {
            clearTimeout(silenceTimer);
            silenceTimer = null;
        }

        if (isRecording) requestAnimationFrame(check);
    })();
}

async function stopRecording() {
    if (!mediaRecorder || mediaRecorder.state === "inactive") return;
    mediaRecorder.stop();
    isRecording = false;

    mediaRecorder.onstop = async () => {
        const blob     = new Blob(audioChunks, { type: mediaRecorder.mimeType || "audio/webm" });
        const ctx      = audioContext;
        const stream   = mediaRecorder.stream;

        try {
            // Convert to WAV for maximum compatibility
            if (ctx && ctx.state !== "closed") {
                const ab        = await blob.arrayBuffer();
                const decoded   = await ctx.decodeAudioData(ab);
                const wavBlob   = audioBufferToWav(decoded);

                const reader = new FileReader();
                reader.onloadend = () => {
                    if (voiceWs && voiceWs.readyState === WebSocket.OPEN) {
                        voiceWs.send(JSON.stringify({
                            type: "audio",
                            audio: reader.result.split(",")[1],
                            session_id: sessionId
                        }));
                        setStatus("Processing your voice…");
                    } else {
                        setStatus("Not connected to voice chat");
                        addMessage("system", "⚠️ Voice connection lost.");
                    }
                };
                reader.readAsDataURL(wavBlob);
            } else {
                throw new Error("AudioContext unavailable");
            }
        } catch (err) {
            // Fallback: send original blob
            const reader = new FileReader();
            reader.onloadend = () => {
                if (voiceWs && voiceWs.readyState === WebSocket.OPEN) {
                    voiceWs.send(JSON.stringify({
                        type: "audio",
                        audio: reader.result.split(",")[1],
                        session_id: sessionId
                    }));
                    setStatus("Processing your voice…");
                }
            };
            reader.readAsDataURL(blob);
        }

        // Cleanup
        if (stream)  stream.getTracks().forEach(t => t.stop());
        if (ctx && ctx.state !== "closed") ctx.close();
        audioContext = null;
    };

    voiceBtnEl.classList.remove("recording");
    voiceBtnEl.textContent = "🎤";
    clearTimeout(silenceTimer);
    silenceTimer = null;
}

/* ════════════════════════════════════════════════════════════
   VOICE MESSAGES FROM SERVER
   ════════════════════════════════════════════════════════════ */
function handleVoiceMsg(evt) {
    const d = JSON.parse(evt.data);

    // ── transcript bubble ─────────────────────────────────
    if (d.type === "transcription") {
        addMessage("user", d.text);
        setStatus("Assistant thinking…");
    }

    // ── streaming text tokens ─────────────────────────────
    if (d.type === "text_chunk") {
        if (!currentBotMessage) currentBotMessage = addMessage("bot", "", true);
        currentBotMessage.textContent += d.text;
        messagesEl.scrollTop = messagesEl.scrollHeight;
    }

    if (d.type === "text_complete") {
        currentBotMessage = null;
    }

    // ── full audio response ───────────────────────────────
    if (d.type === "audio") {
        // Finalise / create bubble
        if (currentBotMessage) {
            currentBotMessage.textContent = d.text;
            currentBotMessage.classList.remove("streaming-text");
            currentBotMessage = null;
        } else {
            addMessage("bot", d.text);
        }

        // Play audio
        isPlayingAudio = true;
        const audio = new Audio("data:audio/mp3;base64," + d.audio);
        currentAudio  = audio;

        audio.onended = () => {
            isPlayingAudio = false;
            currentAudio   = null;
            setStatus("Listening… (auto-stops on silence)");

            // Tell server audio finished so idle timer can start
            if (voiceWs && voiceWs.readyState === WebSocket.OPEN)
                voiceWs.send(JSON.stringify({ type: "audio_finished" }));

            // Auto-restart mic after a short pause
            autoStartEnabled = true;
            setTimeout(() => {
                if (!isRecording && !isPlayingAudio && currentMode === "voice"
                    && voiceWs && voiceWs.readyState === WebSocket.OPEN && autoStartEnabled)
                    startRecording();
            }, 500);
        };

        audio.onerror = () => {
            isPlayingAudio = false;
            currentAudio   = null;
            setStatus("Audio playback failed");
            if (voiceWs && voiceWs.readyState === WebSocket.OPEN)
                voiceWs.send(JSON.stringify({ type: "audio_finished" }));
        };

        audio.play().catch(() => { isPlayingAudio = false; currentAudio = null; setStatus("Could not play audio"); });
        setStatus("Assistant speaking…");
    }

    // ── text-only fallback (TTS failed server-side) ──────
    if (d.type === "text_only") {
        addMessage("bot", d.text);
        setStatus("(Audio unavailable — text only)");
    }

    // ── barge-in interrupt ────────────────────────────────
    if (d.type === "interrupt_audio") {
        if (currentAudio) {
            currentAudio.pause();
            currentAudio.currentTime = 0;
            currentAudio  = null;
            isPlayingAudio = false;
            setStatus("Listening…");

            if (voiceWs && voiceWs.readyState === WebSocket.OPEN)
                voiceWs.send(JSON.stringify({ type: "audio_finished" }));
        }
    }

    // ── status updates ────────────────────────────────────
    if (d.type === "status") setStatus(d.message);

    // ── session ended (idle timeout) ──────────────────────
    if (d.type === "session_end") {
        setStatus("Session ended. Click the mic to start again.");
        updateBadge("Session Ended", "rgba(255,152,0,0.2)");

        if (voiceWs) { voiceWs.close(); voiceWs = null; }

        sessionId = crypto.randomUUID();   // fresh session for next conversation
        setTimeout(() => addMessage("system", "💬 Session ended. Click 🎤 to start a new conversation."), 1000);
    }

    if (d.type === "error") {
        setStatus("Error: " + d.message);
        addMessage("system", "⚠️ " + d.message);
    }
}

/* ════════════════════════════════════════════════════════════
   UI HELPERS
   ════════════════════════════════════════════════════════════ */
function addMessage(role, text, streaming = false) {
    const row    = document.createElement("div");
    row.className = `msg ${role}`;

    // Avatar only for bot messages
    if (role === "bot") {
        const av       = document.createElement("div");
        av.className   = "avatar";
        av.textContent = "✦";
        row.appendChild(av);
    }

    const bubble = document.createElement("div");
    bubble.className = "bubble" + (streaming ? " streaming-text" : "");
    bubble.textContent = text;
    row.appendChild(bubble);

    messagesEl.appendChild(row);
    messagesEl.scrollTop = messagesEl.scrollHeight;

    return bubble;   // caller can keep appending tokens to this element
}

function clearChat() {
    messagesEl.innerHTML = "";

    const old = sessionId;
    sessionId = crypto.randomUUID();

    currentBotMessage = null;
    if (currentAudio)  { currentAudio.pause(); currentAudio = null; isPlayingAudio = false; }

    // Reconnect with new session
    if (currentMode === "text") { if (textWs)  textWs.close();  connectTextWS(); }
    else                        { if (voiceWs) voiceWs.close(); connectVoiceWS(); }

    setStatus("Chat cleared — fresh conversation started.");
    addMessage("system", "🔄 New conversation started");
}

function setStatus(text) {
    // Show waveform dots while processing
    const showWave = /thinking|processing|speaking|listening/i.test(text);
    statusEl.innerHTML = showWave
        ? `<span class="waveform"><span></span><span></span><span></span><span></span><span></span></span> ${text}`
        : text;
}

function updateBadge(text, bg) {
    statusBadge.textContent = text;
    statusBadge.style.background = bg;
}

/* ════════════════════════════════════════════════════════════
   WAV ENCODER  (AudioBuffer → WAV Blob)
   ════════════════════════════════════════════════════════════ */
function audioBufferToWav(buffer) {
    const ch       = buffer.numberOfChannels;
    const rate     = buffer.sampleRate;
    const len      = buffer.length;
    const bps      = 2;                          // 16-bit
    const dataSize = len * ch * bps;
    const ab       = new ArrayBuffer(44 + dataSize);
    const v        = new DataView(ab);

    const str = (off, s) => { for (let i = 0; i < s.length; i++) v.setUint8(off + i, s.charCodeAt(i)); };

    str(0,  "RIFF");  v.setUint32(4,  ab.byteLength - 8, true);
    str(8,  "WAVE");  str(12, "fmt ");
    v.setUint32(16, 16, true);                   // chunk size
    v.setUint16(20,  1, true);                   // PCM
    v.setUint16(22, ch, true);
    v.setUint32(24, rate, true);
    v.setUint32(28, rate * ch * bps, true);      // byte rate
    v.setUint16(32, ch * bps, true);             // block align
    v.setUint16(34, 16, true);                   // bits/sample
    str(36, "data"); v.setUint32(40, dataSize, true);

    let off = 44;
    for (let i = 0; i < len; i++) {
        for (let c = 0; c < ch; c++) {
            const s = Math.max(-1, Math.min(1, buffer.getChannelData(c)[i]));
            v.setInt16(off, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
            off += 2;
        }
    }
    return new Blob([ab], { type: "audio/wav" });
}

/* ════════════════════════════════════════════════════════════
   INIT  &  CLEANUP
   ════════════════════════════════════════════════════════════ */
window.addEventListener("load", () => {
    connectTextWS();
    setStatus("Connected! Type your message…");
});

window.addEventListener("beforeunload", () => {
    if (textWs)  textWs.close();
    if (voiceWs) voiceWs.close();
    if (isRecording) stopRecording();
    if (currentAudio) { currentAudio.pause(); currentAudio = null; }
});
