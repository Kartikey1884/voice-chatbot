let audioContext;
let analyser;
let silenceTimer = null;

let textWs = null;
let voiceWs = null;

let mediaRecorder = null;
let audioChunks = [];
let isRecording = false;
let sessionId = crypto.randomUUID(); // ONE session ID for entire page session
let currentBotMessage = null;
let currentMode = 'text';
let isPlayingAudio = false;
let currentAudioElement = null; // Track current audio element
let autoStartEnabled = true; // Flag to control auto-start after bot responses

const statusEl = document.getElementById("status");
const statusBadgeEl = document.getElementById("statusBadge");
const messagesEl = document.getElementById("messages");
const voiceBtnEl = document.getElementById("voiceBtn");
const textInputEl = document.getElementById("textInput");
const sendBtnEl = document.getElementById("sendBtn");
const textModeEl = document.getElementById("textMode");

/* -------- MODE SWITCH -------- */
function switchMode(mode, btn) {
    const previousMode = currentMode;
    currentMode = mode;

    document.querySelectorAll('.mode-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');

    if (mode === 'voice') {
        textModeEl.classList.add('hidden');
        voiceBtnEl.classList.remove('hidden');

        // Close text websocket if open
        if (textWs && textWs.readyState === WebSocket.OPEN) {
            textWs.close();
            textWs = null;
        }

        connectVoiceWebSocket();

        // Show mode switch message
        if (previousMode === 'text') {
            addMessage("system", "🎤 Switched to voice mode - Your conversation continues");
        }
        setStatus("Connecting to voice chat...");
    } else {
        textModeEl.classList.remove('hidden');
        voiceBtnEl.classList.add('hidden');

        // Close voice websocket if open
        if (voiceWs && voiceWs.readyState === WebSocket.OPEN) {
            voiceWs.close();
            voiceWs = null;
        }

        // Stop any ongoing recording
        if (isRecording) {
            stopRecording();
        }

        // Stop any playing audio
        if (currentAudioElement) {
            currentAudioElement.pause();
            currentAudioElement = null;
            isPlayingAudio = false;
        }

        connectTextWebSocket();

        // Show mode switch message
        if (previousMode === 'voice') {
            addMessage("system", "💬 Switched to text mode - Your conversation continues");
        }
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
        console.log("📝 Text mode connected with session:", sessionId);
    };

    textWs.onmessage = handleTextMessage;

    textWs.onerror = (error) => {
        console.error("❌ Text WebSocket error:", error);
        console.error("WebSocket state:", textWs.readyState);
        setStatus("Text chat connection error");
        updateBadge("Error", "rgba(244,67,54,0.2)");
        addMessage("system", "⚠️ Text connection error. Please check if the server is running.");
    };

    textWs.onclose = () => {
        setStatus("Text chat disconnected");
        updateBadge("Disconnected", "rgba(158,158,158,0.2)");
    };
}

/* -------- VOICE SOCKET -------- */
function connectVoiceWebSocket() {
    if (voiceWs && voiceWs.readyState === WebSocket.OPEN) return;

    setStatus("Connecting to voice chat...");
    updateBadge("Connecting", "rgba(255,165,0,0.2)");

    voiceWs = new WebSocket("ws://localhost:8000/ws/voice");

    voiceWs.onopen = () => {
        setStatus("Connecting...");
        updateBadge("Connected", "rgba(76,175,80,0.2)");
        console.log("🎤 Voice mode connected with session:", sessionId);

        // 👋 Send greeting request with SAME session ID
        voiceWs.send(JSON.stringify({
            type: "greet",
            session_id: sessionId
        }));
    };

    voiceWs.onmessage = handleVoiceMessage;

    voiceWs.onerror = (error) => {
        console.error("❌ Voice WebSocket error:", error);
        console.error("WebSocket state:", voiceWs.readyState);
        setStatus("Voice chat connection error");
        updateBadge("Error", "rgba(244,67,54,0.2)");
        addMessage("system", "⚠️ Voice connection error. Please check if the server is running.");
    };

    voiceWs.onclose = () => {
        setStatus("Voice chat disconnected");
        updateBadge("Disconnected", "rgba(158,158,158,0.2)");
    };
}

/* -------- TEXT -------- */
function sendTextMessage() {
    const text = textInputEl.value.trim();
    if (!text) return;

    if (!textWs || textWs.readyState !== WebSocket.OPEN) {
        setStatus("Not connected to server");
        updateBadge("Disconnected", "rgba(244,67,54,0.2)");
        return;
    }

    addMessage("user", text);
    textInputEl.value = "";
    setStatus("Assistant thinking...");

    // Send with shared session ID
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
        messagesEl.scrollTop = messagesEl.scrollHeight;
    }

    if (data.type === "text_complete") {
        currentBotMessage = null;
        setStatus("Type your message");
    }

    if (data.type === "error") {
        setStatus("Error: " + data.message);
        addMessage("system", "⚠️ " + data.message);
    }
}

function handleKeyPress(event) {
    if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        sendTextMessage();
    }
}

/* -------- VOICE -------- */
async function toggleVoice() {
    // Don't allow starting recording while audio is playing
    if (isPlayingAudio) {
        setStatus("Please wait for the assistant to finish speaking");
        return;
    }

    if (!isRecording) {
        autoStartEnabled = true; // Enable auto-start when user manually starts
        startRecording();
    } else {
        autoStartEnabled = false; // Disable auto-start when user manually stops
        stopRecording();
    }
}

async function startRecording() {
    // Prevent double-recording
    if (isRecording) {
        console.log("⚠️ Already recording, ignoring start request");
        return;
    }

    try {
        // 🎯 Notify backend that user started speaking (reset timer & interrupt audio)
        if (voiceWs && voiceWs.readyState === WebSocket.OPEN) {
            voiceWs.send(JSON.stringify({
                type: "user_speaking"
            }));
            console.log("🎤 User started speaking - backend notified");
        } else {
            console.warn("⚠️ Voice WebSocket not connected, cannot notify backend");
        }

        const stream = await navigator.mediaDevices.getUserMedia({
            audio: {
                echoCancellation: true,
                noiseSuppression: true,
                autoGainControl: true
            }
        });

        audioContext = new AudioContext();
        const source = audioContext.createMediaStreamSource(stream);

        analyser = audioContext.createAnalyser();
        analyser.fftSize = 2048;

        source.connect(analyser);

        mediaRecorder = new MediaRecorder(stream);
        audioChunks = [];

        mediaRecorder.ondataavailable = e => audioChunks.push(e.data);
        mediaRecorder.start();

        isRecording = true;
        voiceBtnEl.classList.add("recording");
        voiceBtnEl.textContent = "⏹";
        setStatus("Listening... (auto-stops on silence)");

        detectSilence();
    } catch (error) {
        console.error("❌ Error starting recording:", error);
        console.error("Error details:", {
            name: error.name,
            message: error.message,
            stack: error.stack
        });

        let errorMessage = "Microphone access denied";
        if (error.name === "NotAllowedError") {
            errorMessage = "⚠️ Microphone permission denied. Please allow microphone access in your browser settings.";
        } else if (error.name === "NotFoundError") {
            errorMessage = "⚠️ No microphone found. Please connect a microphone and try again.";
        } else if (error.name === "NotReadableError") {
            errorMessage = "⚠️ Microphone is being used by another application. Please close other apps using the microphone.";
        } else {
            errorMessage = `⚠️ Error accessing microphone: ${error.message}`;
        }

        setStatus(errorMessage);
        addMessage("system", errorMessage);
    }
}

function detectSilence() {
    const buffer = new Uint8Array(analyser.fftSize);

    function check() {
        analyser.getByteTimeDomainData(buffer);

        let max = 0;
        for (let i = 0; i < buffer.length; i++) {
            const v = Math.abs(buffer[i] - 128);
            if (v > max) max = v;
        }

        // Silence threshold - adjust if needed (lower = more sensitive)
        if (max < 5) {
            if (!silenceTimer) {
                silenceTimer = setTimeout(() => {
                    console.log("🔇 Silence detected - stopping recording");
                    stopRecording();
                }, 1000); // 1 second of silence (as per requirements)
            }
        } else {
            clearTimeout(silenceTimer);
            silenceTimer = null;
        }

        if (isRecording) requestAnimationFrame(check);
    }

    check();
}

async function stopRecording() {
    if (!mediaRecorder || mediaRecorder.state === "inactive") return;

    mediaRecorder.stop();
    isRecording = false;

    mediaRecorder.onstop = async () => {
        const blob = new Blob(audioChunks, { type: mediaRecorder.mimeType || "audio/webm" });
        const contextToUse = audioContext; // Store reference before cleanup
        const streamToStop = mediaRecorder.stream;

        // Convert to WAV format for better compatibility with Whisper
        try {
            if (contextToUse && contextToUse.state !== 'closed') {
                const arrayBuffer = await blob.arrayBuffer();
                const audioBuffer = await contextToUse.decodeAudioData(arrayBuffer);
                const wavBlob = audioBufferToWav(audioBuffer);

                const reader = new FileReader();
                reader.onloadend = () => {
                    if (voiceWs && voiceWs.readyState === WebSocket.OPEN) {
                        // Send with shared session ID
                        voiceWs.send(JSON.stringify({
                            type: "audio",
                            audio: reader.result.split(",")[1],
                            session_id: sessionId
                        }));
                        setStatus("Processing your voice...");
                        console.log("📤 Audio sent to backend (WAV format)");
                    } else {
                        setStatus("Not connected to voice chat");
                        addMessage("system", "⚠️ Voice connection lost. Please reconnect.");
                    }
                };
                reader.readAsDataURL(wavBlob);
            } else {
                throw new Error("AudioContext not available");
            }
        } catch (error) {
            console.error("❌ Error converting audio to WAV:", error);
            console.error("Error details:", {
                name: error.name,
                message: error.message,
                contextState: contextToUse ? contextToUse.state : "null"
            });

            // Fallback: send original blob (Whisper can handle various formats)
            try {
                const reader = new FileReader();
                reader.onloadend = () => {
                    if (voiceWs && voiceWs.readyState === WebSocket.OPEN) {
                        voiceWs.send(JSON.stringify({
                            type: "audio",
                            audio: reader.result.split(",")[1],
                            session_id: sessionId
                        }));
                        setStatus("Processing your voice...");
                        console.log("📤 Audio sent to backend (original format - fallback)");
                    } else {
                        console.error("❌ Voice WebSocket not connected");
                        setStatus("Connection lost. Please reconnect.");
                    }
                };
                reader.onerror = (err) => {
                    console.error("❌ FileReader error:", err);
                    setStatus("Error reading audio file");
                };
                reader.readAsDataURL(blob);
            } catch (fallbackError) {
                console.error("❌ Fallback also failed:", fallbackError);
                setStatus("Error processing audio. Please try again.");
                addMessage("system", "⚠️ Error processing audio. Please try recording again.");
            }
        }

        // Clean up audio resources
        if (streamToStop) {
            streamToStop.getTracks().forEach(track => track.stop());
        }
        if (contextToUse && contextToUse.state !== 'closed') {
            contextToUse.close();
        }
        audioContext = null;
    };

    voiceBtnEl.classList.remove("recording");
    voiceBtnEl.textContent = "🎤";
    clearTimeout(silenceTimer);
    silenceTimer = null;
}

/* -------- VOICE MESSAGE -------- */
function handleVoiceMessage(event) {
    const data = JSON.parse(event.data);

    if (data.type === "transcription") {
        addMessage("user", data.text);
        setStatus("Assistant thinking...");
    }

    // Handle streaming text chunks during voice responses
    if (data.type === "text_chunk") {
        if (!currentBotMessage) {
            currentBotMessage = addMessage("bot", "", true);
        }
        currentBotMessage.textContent += data.text;
        messagesEl.scrollTop = messagesEl.scrollHeight;
    }

    if (data.type === "text_complete") {
        // Text streaming complete, audio will follow
        currentBotMessage = null;
    }

    if (data.type === "audio") {
        // If we have a streaming message, update it with final text, otherwise create new
        if (currentBotMessage) {
            currentBotMessage.textContent = data.text;
            currentBotMessage = null;
        } else {
            addMessage("bot", data.text);
        }

        // Play audio response
        isPlayingAudio = true;
        const audio = new Audio("data:audio/mp3;base64," + data.audio);
        currentAudioElement = audio; // Store reference

        audio.onended = () => {
            isPlayingAudio = false;
            currentAudioElement = null;
            setStatus("Listening... (auto-stops on silence)");

            // 🎯 Notify backend that audio finished playing
            if (voiceWs && voiceWs.readyState === WebSocket.OPEN) {
                voiceWs.send(JSON.stringify({
                    type: "audio_finished"
                }));
                console.log("🔊 Audio playback finished");
            }

            // Auto-start recording after bot finishes speaking (ChatGPT-style)
            // Re-enable auto-start after bot responds (natural conversation flow)
            autoStartEnabled = true;

            // Wait a bit longer to ensure audio is fully stopped and user can process the response
            setTimeout(() => {
                // Only auto-start if:
                // 1. Not already recording
                // 2. Not playing audio
                // 3. Still in voice mode
                // 4. WebSocket is connected
                // 5. Auto-start is enabled
                if (!isRecording && !isPlayingAudio && currentMode === 'voice' &&
                    voiceWs && voiceWs.readyState === WebSocket.OPEN && autoStartEnabled) {
                    console.log("🎤 Auto-starting recording after bot response");
                    startRecording();
                }
            }, 500); // Small delay to ensure audio is fully stopped
        };

        audio.onerror = (error) => {
            console.error("Audio playback error:", error);
            isPlayingAudio = false;
            currentAudioElement = null;
            setStatus("Audio playback failed");

            // Even on error, notify backend
            if (voiceWs && voiceWs.readyState === WebSocket.OPEN) {
                voiceWs.send(JSON.stringify({
                    type: "audio_finished"
                }));
            }
        };

        audio.play().catch(err => {
            console.error("Audio play error:", err);
            isPlayingAudio = false;
            currentAudioElement = null;
            setStatus("Could not play audio");
        });
        setStatus("Assistant speaking...");
    }

    // ⭐ NEW: Handle interrupt_audio from backend
    if (data.type === "interrupt_audio") {
        if (currentAudioElement) {
            console.log("🔇 Bot audio interrupted by user");
            currentAudioElement.pause();
            currentAudioElement.currentTime = 0;
            currentAudioElement = null;
            isPlayingAudio = false;
            setStatus("Listening...");

            // Notify backend that audio was interrupted
            if (voiceWs && voiceWs.readyState === WebSocket.OPEN) {
                voiceWs.send(JSON.stringify({
                    type: "audio_finished"
                }));
            }
        }
    }

    if (data.type === "status") {
        setStatus(data.message);
    }

    if (data.type === "session_end") {
        setStatus("Session ended. Click microphone to start again.");
        updateBadge("Session Ended", "rgba(255,152,0,0.2)");

        // Close voice websocket
        if (voiceWs) {
            voiceWs.close();
            voiceWs = null;
        }

        // Create NEW session ID for next conversation
        sessionId = crypto.randomUUID();
        console.log("🔄 New session created:", sessionId);

        // Show reconnect message after a delay
        setTimeout(() => {
            addMessage("system", "💬 Session ended. Click the microphone to start a new conversation.");
        }, 1000);
    }

    if (data.type === "error") {
        setStatus("Error: " + data.message);
        addMessage("system", "⚠️ " + data.message);
    }

    if (data.type === "pong") {
        // Keep-alive response
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
    messagesEl.scrollTop = messagesEl.scrollHeight;

    return bubble;
}

function clearChat() {
    messagesEl.innerHTML = "";

    // Generate NEW session ID
    const oldSessionId = sessionId;
    sessionId = crypto.randomUUID();

    console.log(`🗑️ Chat cleared. Old session: ${oldSessionId.substring(0, 8)}... → New session: ${sessionId.substring(0, 8)}...`);

    currentBotMessage = null;

    // Stop any playing audio
    if (currentAudioElement) {
        currentAudioElement.pause();
        currentAudioElement = null;
        isPlayingAudio = false;
    }

    // Reconnect to current mode with new session
    if (currentMode === 'text') {
        if (textWs) textWs.close();
        connectTextWebSocket();
    } else {
        if (voiceWs) voiceWs.close();
        connectVoiceWebSocket();
    }

    setStatus("Chat cleared. Starting fresh conversation...");
    addMessage("system", "🔄 New conversation started");
}

function setStatus(text) {
    statusEl.textContent = text;
}

function updateBadge(text, color) {
    statusBadgeEl.textContent = text;
    statusBadgeEl.style.background = color;
}

// 🔥 Auto-start text chat when page loads
window.addEventListener("load", () => {
    connectTextWebSocket();
    setStatus("Connected! Type your message...");
    console.log("🚀 Session started:", sessionId);
});

// Helper function to convert AudioBuffer to WAV
function audioBufferToWav(buffer) {
    const length = buffer.length;
    const numberOfChannels = buffer.numberOfChannels;
    const sampleRate = buffer.sampleRate;
    const bytesPerSample = 2;
    const blockAlign = numberOfChannels * bytesPerSample;
    const byteRate = sampleRate * blockAlign;
    const dataSize = length * blockAlign;
    const bufferSize = 44 + dataSize;
    const arrayBuffer = new ArrayBuffer(bufferSize);
    const view = new DataView(arrayBuffer);

    // WAV header
    const writeString = (offset, string) => {
        for (let i = 0; i < string.length; i++) {
            view.setUint8(offset + i, string.charCodeAt(i));
        }
    };

    writeString(0, 'RIFF');
    view.setUint32(4, bufferSize - 8, true);
    writeString(8, 'WAVE');
    writeString(12, 'fmt ');
    view.setUint32(16, 16, true); // fmt chunk size
    view.setUint16(20, 1, true); // audio format (PCM)
    view.setUint16(22, numberOfChannels, true);
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, byteRate, true);
    view.setUint16(32, blockAlign, true);
    view.setUint16(34, 16, true); // bits per sample
    writeString(36, 'data');
    view.setUint32(40, dataSize, true);

    // Convert float samples to 16-bit PCM
    let offset = 44;
    for (let i = 0; i < length; i++) {
        for (let channel = 0; channel < numberOfChannels; channel++) {
            const sample = Math.max(-1, Math.min(1, buffer.getChannelData(channel)[i]));
            view.setInt16(offset, sample < 0 ? sample * 0x8000 : sample * 0x7FFF, true);
            offset += 2;
        }
    }

    return new Blob([arrayBuffer], { type: 'audio/wav' });
}

// Cleanup on page unload
window.addEventListener("beforeunload", () => {
    if (textWs) textWs.close();
    if (voiceWs) voiceWs.close();
    if (isRecording) stopRecording();
    if (currentAudioElement) {
        currentAudioElement.pause();
        currentAudioElement = null;
    }
});
