/**
 * GOOGLE ASSISTANT STYLE VOICE INTERACTION
 * 
 * Features:
 * - Continuous listening with Voice Activity Detection (VAD)
 * - Automatic turn-taking (no button holding needed)
 * - Real-time visual feedback
 * - Barge-in support (interrupt assistant while speaking)
 * - Natural conversation flow
 */

// ========================================
// Voice Interaction States
// ========================================
const VoiceState = {
    IDLE: 'idle',                    // Not active
    LISTENING: 'listening',          // Listening for speech
    PROCESSING: 'processing',        // Processing input
    SPEAKING: 'speaking',            // Assistant speaking
    WAITING: 'waiting'               // Waiting for user to finish
};

// ========================================
// Global State
// ========================================
let currentState = VoiceState.IDLE;
let voiceWs = null;
let textWs = null;

let sessionId = crypto.randomUUID();
let currentMode = 'text';

// Audio recording
let mediaStream = null;
let audioContext = null;
let analyser = null;
let scriptProcessor = null;
let audioChunks = [];
let isRecording = false;

// Voice Activity Detection
let vadActive = false;
let speechDetected = false;
let silenceStart = null;
let lastSoundTime = null;
const SILENCE_THRESHOLD = 1.5;  // seconds of silence to stop
const SPEECH_THRESHOLD = 0.02;  // amplitude threshold for speech
const MIN_SPEECH_DURATION = 0.3; // minimum speech duration in seconds

// UI state
let currentBotMessage = null;
let currentAudioElement = null;
let isPlayingAudio = false;

// ========================================
// DOM Elements
// ========================================
const statusEl = document.getElementById("status");
const statusBadgeEl = document.getElementById("statusBadge");
const messagesEl = document.getElementById("messages");
const voiceBtn = document.getElementById("voiceBtn");
const textInput = document.getElementById("textInput");
const sendBtn = document.getElementById("sendBtn");
const textModeEl = document.getElementById("textMode");
const visualizerCanvas = document.getElementById("visualizer");
const visualizerCtx = visualizerCanvas?.getContext("2d");

// ========================================
// Mode Switching
// ========================================
function switchMode(mode, btn) {
    const previousMode = currentMode;
    currentMode = mode;

    document.querySelectorAll('.mode-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');

    if (mode === 'voice') {
        textModeEl.classList.add('hidden');
        voiceBtn.classList.remove('hidden');

        if (textWs && textWs.readyState === WebSocket.OPEN) {
            textWs.close();
        }

        connectVoiceWebSocket();

        if (previousMode === 'text') {
            addMessage("system", "🎤 Voice mode activated - Say something!");
        }
    } else {
        textModeEl.classList.remove('hidden');
        voiceBtn.classList.add('hidden');

        if (voiceWs && voiceWs.readyState === WebSocket.OPEN) {
            voiceWs.close();
        }

        stopVoiceInteraction();
        connectTextWebSocket();

        if (previousMode === 'voice') {
            addMessage("system", "💬 Text mode activated");
        }
    }
}

// ========================================
// Text Chat WebSocket
// ========================================
function connectTextWebSocket() {
    if (textWs && textWs.readyState === WebSocket.OPEN) return;

    setStatus("Connecting...");
    updateBadge("Connecting", "rgba(255,165,0,0.2)");

    textWs = new WebSocket("ws://localhost:8000/ws/text");

    textWs.onopen = () => {
        setStatus("Ready to chat");
        updateBadge("Connected", "rgba(76,175,80,0.2)");
        console.log("📝 Text mode connected:", sessionId);
    };

    textWs.onmessage = handleTextMessage;

    textWs.onerror = (error) => {
        console.error("❌ Text WebSocket error:", error);
        setStatus("Connection error");
        updateBadge("Error", "rgba(244,67,54,0.2)");
    };

    textWs.onclose = () => {
        setStatus("Disconnected");
        updateBadge("Disconnected", "rgba(158,158,158,0.2)");
    };
}

function handleTextMessage(event) {
    const data = JSON.parse(event.data);

    if (data.type === "text_chunk") {
        if (!currentBotMessage) {
            currentBotMessage = addMessage("bot", "", true);
        }
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

function sendTextMessage() {
    const text = textInput.value.trim();
    if (!text) return;

    if (!textWs || textWs.readyState !== WebSocket.OPEN) {
        setStatus("Not connected");
        return;
    }

    addMessage("user", text);
    textInput.value = "";
    setStatus("Thinking...");

    textWs.send(JSON.stringify({
        type: "text",
        text: text,
        session_id: sessionId
    }));
}

function handleKeyPress(event) {
    if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        sendTextMessage();
    }
}

// ========================================
// Voice Chat WebSocket
// ========================================
function connectVoiceWebSocket() {
    if (voiceWs && voiceWs.readyState === WebSocket.OPEN) return;

    setStatus("Connecting to voice...");
    updateBadge("Connecting", "rgba(255,165,0,0.2)");

    voiceWs = new WebSocket("ws://localhost:8000/ws/voice");

    voiceWs.onopen = () => {
        setStatus("Connected");
        updateBadge("Connected", "rgba(76,175,80,0.2)");
        console.log("🎤 Voice mode connected:", sessionId);

        // Activate voice mode
        voiceWs.send(JSON.stringify({
            type: "activate",
            session_id: sessionId
        }));
    };

    voiceWs.onmessage = handleVoiceMessage;

    voiceWs.onerror = (error) => {
        console.error("❌ Voice WebSocket error:", error);
        setStatus("Voice connection error");
        updateBadge("Error", "rgba(244,67,54,0.2)");
    };

    voiceWs.onclose = () => {
        setStatus("Voice disconnected");
        updateBadge("Disconnected", "rgba(158,158,158,0.2)");
        stopVoiceInteraction();
    };
}

function handleVoiceMessage(event) {
    const data = JSON.parse(event.data);

    // State change
    if (data.type === "state_change") {
        handleStateChange(data.state, data.message);
    }

    // Transcription (final)
    if (data.type === "transcription" && data.is_final) {
        addMessage("user", data.text);
        setStatus("Processing...");
    }

    // Interim transcription (real-time)
    if (data.type === "interim_transcript") {
        // Show real-time transcription in UI
        setStatus(`Hearing: "${data.text}"`);
    }

    // Text streaming from LLM
    if (data.type === "text_chunk") {
        if (!currentBotMessage) {
            currentBotMessage = addMessage("bot", "", true);
        }
        currentBotMessage.textContent += data.text;
        messagesEl.scrollTop = messagesEl.scrollHeight;
    }

    if (data.type === "text_complete") {
        currentBotMessage = null;
    }

    // Audio response
    if (data.type === "audio_response") {
        if (currentBotMessage) {
            currentBotMessage.textContent = data.text;
            currentBotMessage = null;
        } else {
            addMessage("bot", data.text);
        }

        playAudioResponse(data.audio);
    }

    // Text only (if TTS failed)
    if (data.type === "text_only") {
        if (currentBotMessage) {
            currentBotMessage.textContent = data.text;
            currentBotMessage = null;
        } else {
            addMessage("bot", data.text);
        }

        // Go back to listening
        if (voiceWs && voiceWs.readyState === WebSocket.OPEN) {
            voiceWs.send(JSON.stringify({
                type: "audio_playback_finished"
            }));
        }
    }

    // Interrupt playback command
    if (data.type === "interrupt_playback") {
        if (currentAudioElement) {
            currentAudioElement.pause();
            currentAudioElement = null;
            isPlayingAudio = false;
        }
    }

    // Timeout warning
    if (data.type === "timeout_warning") {
        setStatus(`⏱️ Session ending in ${data.seconds_remaining}s...`);
    }

    // Session end
    if (data.type === "session_end") {
        handleSessionEnd(data.reason);
    }

    // Error
    if (data.type === "error") {
        setStatus("Error: " + data.message);
        addMessage("system", "⚠️ " + data.message);
    }

    // Pong
    if (data.type === "pong") {
        // Heartbeat response
    }
}

function handleStateChange(state, message) {
    currentState = state;

    // Update UI based on state
    switch (state) {
        case VoiceState.IDLE:
            setStatus("Click microphone to start");
            updateBadge("Idle", "rgba(158,158,158,0.2)");
            voiceBtn.classList.remove("listening", "processing", "speaking");
            voiceBtn.textContent = "🎤";
            break;

        case VoiceState.LISTENING:
            setStatus(message || "I'm listening...");
            updateBadge("Listening", "rgba(33,150,243,0.2)");
            voiceBtn.classList.add("listening");
            voiceBtn.classList.remove("processing", "speaking");
            voiceBtn.textContent = "🎤";
            
            // Start recording if not already
            if (!isRecording) {
                startContinuousListening();
            }
            break;

        case VoiceState.PROCESSING:
            setStatus(message || "Processing...");
            updateBadge("Processing", "rgba(255,152,0,0.2)");
            voiceBtn.classList.add("processing");
            voiceBtn.classList.remove("listening", "speaking");
            voiceBtn.textContent = "⏳";
            
            // Stop recording
            if (isRecording) {
                stopRecording();
            }
            break;

        case VoiceState.SPEAKING:
            setStatus(message || "Speaking...");
            updateBadge("Speaking", "rgba(156,39,176,0.2)");
            voiceBtn.classList.add("speaking");
            voiceBtn.classList.remove("listening", "processing");
            voiceBtn.textContent = "🔊";
            break;

        case VoiceState.WAITING:
            setStatus(message || "Waiting...");
            updateBadge("Waiting", "rgba(255,193,7,0.2)");
            break;
    }
}

function playAudioResponse(audioBase64) {
    isPlayingAudio = true;

    const audio = new Audio("data:audio/mp3;base64," + audioBase64);
    currentAudioElement = audio;

    audio.onended = () => {
        isPlayingAudio = false;
        currentAudioElement = null;

        // Notify backend that audio finished
        if (voiceWs && voiceWs.readyState === WebSocket.OPEN) {
            voiceWs.send(JSON.stringify({
                type: "audio_playback_finished"
            }));
        }

        console.log("🔊 Audio finished");
    };

    audio.onerror = (error) => {
        console.error("❌ Audio playback error:", error);
        isPlayingAudio = false;
        currentAudioElement = null;

        if (voiceWs && voiceWs.readyState === WebSocket.OPEN) {
            voiceWs.send(JSON.stringify({
                type: "audio_playback_finished"
            }));
        }
    };

    audio.play().catch(err => {
        console.error("❌ Audio play error:", err);
        isPlayingAudio = false;
        currentAudioElement = null;
    });
}

function handleSessionEnd(reason) {
    stopVoiceInteraction();

    if (reason === "timeout") {
        addMessage("system", "⏱️ Session ended due to inactivity");
    } else {
        addMessage("system", "Session ended");
    }

    setStatus("Session ended");
    updateBadge("Ended", "rgba(244,67,54,0.2)");

    currentState = VoiceState.IDLE;
    sessionId = crypto.randomUUID();

    setTimeout(() => {
        addMessage("system", "💬 Click microphone to start a new conversation");
    }, 1000);
}

// ========================================
// Voice Interaction - Continuous Listening
// ========================================
async function startContinuousListening() {
    if (isRecording) {
        console.log("⚠️ Already recording");
        return;
    }

    try {
        // Get microphone access
        mediaStream = await navigator.mediaDevices.getUserMedia({
            audio: {
                echoCancellation: true,
                noiseSuppression: true,
                autoGainControl: true,
                sampleRate: 16000
            }
        });

        console.log("🎤 Started continuous listening");

        audioContext = new (window.AudioContext || window.webkitAudioContext)({
            sampleRate: 16000
        });

        const source = audioContext.createMediaStreamSource(mediaStream);
        analyser = audioContext.createAnalyser();
        analyser.fftSize = 2048;
        analyser.smoothingTimeConstant = 0.8;

        scriptProcessor = audioContext.createScriptProcessor(4096, 1, 1);

        source.connect(analyser);
        analyser.connect(scriptProcessor);
        scriptProcessor.connect(audioContext.destination);

        isRecording = true;
        vadActive = true;
        audioChunks = [];

        // Voice Activity Detection
        scriptProcessor.onaudioprocess = (e) => {
            if (!vadActive) return;

            const inputData = e.inputBuffer.getChannelData(0);
            audioChunks.push(new Float32Array(inputData));

            // Calculate RMS (Root Mean Square) for volume detection
            let sum = 0;
            for (let i = 0; i < inputData.length; i++) {
                sum += inputData[i] * inputData[i];
            }
            const rms = Math.sqrt(sum / inputData.length);

            // Detect speech
            const now = Date.now();
            if (rms > SPEECH_THRESHOLD) {
                lastSoundTime = now;

                if (!speechDetected) {
                    speechDetected = true;
                    console.log("🗣️ Speech detected");

                    // Notify backend
                    if (voiceWs && voiceWs.readyState === WebSocket.OPEN) {
                        voiceWs.send(JSON.stringify({
                            type: "speech_detected"
                        }));
                    }
                }
            }

            // Detect silence after speech
            if (speechDetected && lastSoundTime) {
                const silenceDuration = (now - lastSoundTime) / 1000;

                if (silenceDuration >= SILENCE_THRESHOLD) {
                    console.log("🛑 Silence detected, stopping");

                    // Notify backend
                    if (voiceWs && voiceWs.readyState === WebSocket.OPEN) {
                        voiceWs.send(JSON.stringify({
                            type: "speech_ended"
                        }));
                    }

                    // Send recorded audio
                    sendRecordedAudio();

                    // Reset for next utterance
                    speechDetected = false;
                    lastSoundTime = null;
                    audioChunks = [];
                }
            }

            // Update visualizer
            updateVisualizer();
        };

        voiceBtn.classList.add("listening");

    } catch (error) {
        console.error("❌ Microphone error:", error);
        setStatus("Microphone access denied");
        addMessage("system", "⚠️ Please allow microphone access");
    }
}

function stopRecording() {
    if (!isRecording) return;

    console.log("🛑 Stopping recording");

    vadActive = false;
    isRecording = false;

    if (scriptProcessor) {
        scriptProcessor.disconnect();
        scriptProcessor = null;
    }

    if (analyser) {
        analyser.disconnect();
        analyser = null;
    }

    if (audioContext) {
        audioContext.close();
        audioContext = null;
    }

    if (mediaStream) {
        mediaStream.getTracks().forEach(track => track.stop());
        mediaStream = null;
    }

    audioChunks = [];
    speechDetected = false;
    lastSoundTime = null;

    voiceBtn.classList.remove("listening");
}

function sendRecordedAudio() {
    if (audioChunks.length === 0) {
        console.log("⚠️ No audio to send");
        return;
    }

    try {
        // Combine audio chunks
        const totalLength = audioChunks.reduce((acc, chunk) => acc + chunk.length, 0);
        const combinedAudio = new Float32Array(totalLength);
        let offset = 0;
        for (const chunk of audioChunks) {
            combinedAudio.set(chunk, offset);
            offset += chunk.length;
        }

        // Convert to WAV
        const wavBlob = floatTo16BitPCM(combinedAudio);
        
        // Convert to base64
        const reader = new FileReader();
        reader.onload = () => {
            const base64Audio = reader.result.split(',')[1];

            if (voiceWs && voiceWs.readyState === WebSocket.OPEN) {
                voiceWs.send(JSON.stringify({
                    type: "audio",
                    audio: base64Audio
                }));

                console.log("📤 Sent audio:", wavBlob.size, "bytes");
            }
        };
        reader.readAsDataURL(wavBlob);

    } catch (error) {
        console.error("❌ Error sending audio:", error);
    }
}

function floatTo16BitPCM(float32Array) {
    const buffer = new ArrayBuffer(44 + float32Array.length * 2);
    const view = new DataView(buffer);
    
    // WAV header
    const writeString = (offset, string) => {
        for (let i = 0; i < string.length; i++) {
            view.setUint8(offset + i, string.charCodeAt(i));
        }
    };
    
    const sampleRate = 16000;
    const numChannels = 1;
    const bitsPerSample = 16;
    
    writeString(0, 'RIFF');
    view.setUint32(4, 36 + float32Array.length * 2, true);
    writeString(8, 'WAVE');
    writeString(12, 'fmt ');
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true);
    view.setUint16(22, numChannels, true);
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, sampleRate * numChannels * bitsPerSample / 8, true);
    view.setUint16(32, numChannels * bitsPerSample / 8, true);
    view.setUint16(34, bitsPerSample, true);
    writeString(36, 'data');
    view.setUint32(40, float32Array.length * 2, true);
    
    // Convert float to 16-bit PCM
    let offset = 44;
    for (let i = 0; i < float32Array.length; i++) {
        const sample = Math.max(-1, Math.min(1, float32Array[i]));
        view.setInt16(offset, sample < 0 ? sample * 0x8000 : sample * 0x7FFF, true);
        offset += 2;
    }
    
    return new Blob([buffer], { type: 'audio/wav' });
}

function updateVisualizer() {
    if (!analyser || !visualizerCanvas) return;

    const bufferLength = analyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);
    analyser.getByteTimeDomainData(dataArray);

    visualizerCtx.fillStyle = 'rgb(245, 245, 245)';
    visualizerCtx.fillRect(0, 0, visualizerCanvas.width, visualizerCanvas.height);

    visualizerCtx.lineWidth = 2;
    visualizerCtx.strokeStyle = speechDetected ? 'rgb(76, 175, 80)' : 'rgb(33, 150, 243)';

    visualizerCtx.beginPath();

    const sliceWidth = visualizerCanvas.width / bufferLength;
    let x = 0;

    for (let i = 0; i < bufferLength; i++) {
        const v = dataArray[i] / 128.0;
        const y = v * visualizerCanvas.height / 2;

        if (i === 0) {
            visualizerCtx.moveTo(x, y);
        } else {
            visualizerCtx.lineTo(x, y);
        }

        x += sliceWidth;
    }

    visualizerCtx.lineTo(visualizerCanvas.width, visualizerCanvas.height / 2);
    visualizerCtx.stroke();
}

function stopVoiceInteraction() {
    stopRecording();

    if (currentAudioElement) {
        currentAudioElement.pause();
        currentAudioElement = null;
        isPlayingAudio = false;
    }

    currentState = VoiceState.IDLE;
}

// ========================================
// Voice Button Click Handler
// ========================================
function toggleVoice() {
    if (currentState === VoiceState.SPEAKING && isPlayingAudio) {
        // Barge-in - interrupt the assistant
        console.log("⚡ Barge-in!");

        if (voiceWs && voiceWs.readyState === WebSocket.OPEN) {
            voiceWs.send(JSON.stringify({
                type: "barge_in"
            }));
        }

        if (currentAudioElement) {
            currentAudioElement.pause();
            currentAudioElement = null;
            isPlayingAudio = false;
        }

        return;
    }

    if (currentState === VoiceState.IDLE) {
        // Wake up
        if (voiceWs && voiceWs.readyState === WebSocket.OPEN) {
            voiceWs.send(JSON.stringify({
                type: "wake_up"
            }));
        }
    } else if (currentState === VoiceState.LISTENING) {
        // Stop listening
        if (voiceWs && voiceWs.readyState === WebSocket.OPEN) {
            voiceWs.send(JSON.stringify({
                type: "stop_listening"
            }));
        }
        stopRecording();
    }
}

// ========================================
// UI Helpers
// ========================================
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
    sessionId = crypto.randomUUID();

    currentBotMessage = null;
    stopVoiceInteraction();

    if (currentMode === 'text') {
        if (textWs) textWs.close();
        connectTextWebSocket();
    } else {
        if (voiceWs) voiceWs.close();
        connectVoiceWebSocket();
    }

    setStatus("New conversation started");
    addMessage("system", "🔄 Chat cleared");
}

function setStatus(text) {
    statusEl.textContent = text;
}

function updateBadge(text, color) {
    statusBadgeEl.textContent = text;
    statusBadgeEl.style.background = color;
}

// ========================================
// Initialize
// ========================================
window.addEventListener("load", () => {
    connectTextWebSocket();
    setStatus("Ready to chat");
    console.log("🚀 Session started:", sessionId);

    // Setup visualizer if canvas exists
    if (visualizerCanvas) {
        visualizerCanvas.width = visualizerCanvas.offsetWidth;
        visualizerCanvas.height = visualizerCanvas.offsetHeight;
    }
});

window.addEventListener("beforeunload", () => {
    if (textWs) textWs.close();
    if (voiceWs) voiceWs.close();
    stopVoiceInteraction();
});