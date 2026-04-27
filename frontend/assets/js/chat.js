const chatEl = document.getElementById('chat');
const inputEl = document.getElementById('input');
const meEl = document.getElementById('me');

let mode = 'text';
let ws;
let mediaRecorder;
let chunks=[];

// function addBubble(who, text){
//   const row = document.createElement('div');
//   row.className = 'row ' + who;
//   const b = document.createElement('div');
//   b.className = 'bubble';
//   b.textContent = text;
//   row.appendChild(b);
//   chatEl.appendChild(row);
//   chatEl.scrollTop = chatEl.scrollHeight;
//   return b;
// }

let msgCounter = 0;
const audioPlayers = new Map(); // id -> Audio

function stopAllAudioExcept(id){
  for (const [k, a] of audioPlayers.entries()){
    if (k !== id && !a.paused){
      a.pause();
      a.currentTime = 0;
      const btn = document.querySelector(`button.tts-btn[data-id="${k}"]`);
      if(btn) btn.textContent = '🔊';
    }
  }
}

function addBubble(who, text, opts = {}){
  const row = document.createElement('div');
  row.className = 'row ' + who;

  const b = document.createElement('div');
  b.className = 'bubble';

  // text element (so we can stream deltas into it)
  const textEl = document.createElement('div');
  textEl.className = 'bubble-text';
  textEl.textContent = text || '';
  b.appendChild(textEl);

  let ttsBtn = null;
  let id = null;

  // Add TTS button only for assistant messages
  if(who === 'assistant'){
    id = String(++msgCounter);
    b.dataset.msgId = id;

    ttsBtn = document.createElement('button');
    ttsBtn.className = 'tts-btn';
    ttsBtn.dataset.id = id;
    ttsBtn.textContent = '🔊';
    ttsBtn.title = 'Play / Pause';
    ttsBtn.disabled = true; // enable after final text arrives

    ttsBtn.onclick = () => {
      const currentText = textEl.textContent.trim();
      if(!currentText) return;

      // If we already have audio for this message -> toggle play/pause
      const existing = audioPlayers.get(id);
      if(existing){
        if(existing.paused){
          stopAllAudioExcept(id);
          existing.play().catch(()=>{});
          ttsBtn.textContent = '⏸️';
        } else {
          existing.pause();
          ttsBtn.textContent = '🔊';
        }
        return;
      }

      // Request TTS from server (on-demand)
      ttsBtn.disabled = true;
      ttsBtn.textContent = '⏳';
      ws.send(JSON.stringify({ type: 'tts', request_id: id, text: currentText }));
    };

    b.appendChild(ttsBtn);
  }

  row.appendChild(b);
  chatEl.appendChild(row);
  chatEl.scrollTop = chatEl.scrollHeight;

  // Return refs so streaming can update the right node
  return { bubble: b, textEl, ttsBtn, id };
}


function setMode(m){
  mode = m;
  document.getElementById('modeText').classList.toggle('active', m==='text');
  document.getElementById('modeVoice').classList.toggle('active', m==='voice');

  const textControls = document.getElementById('textControls');
  const voiceControls = document.getElementById('voiceControls');

  // if(m === 'text'){
  //   textControls.style.display = 'flex';
  //   voiceControls.style.display = 'none';
  // } else {
  //   textControls.style.display = 'none';
  //   voiceControls.style.display = 'flex';
  // }
  const app = document.querySelector('.app');

  if(m === 'voice'){
    app.classList.add('voice-mode');
  } else {
    app.classList.remove('voice-mode');
  }
}

document.getElementById('modeText').onclick = ()=>setMode('text');
document.getElementById('modeVoice').onclick = ()=>setMode('voice');

async function connect(){
  const proto = location.protocol === 'https:' ? 'wss' : 'ws';
  ws = new WebSocket(`${proto}://${location.host}/ws/chat`);

  let assistantBubble = null;

  ws.onopen = ()=>{};
  ws.onmessage = (ev)=>{
    const msg = JSON.parse(ev.data);
    if(msg.type==='ready'){
      meEl.textContent = `${msg.user.name || 'User'} (${msg.user.userType || 'employee'})`;
      return;
    }
    // if(msg.type==='delta'){
    //   if(!assistantBubble) assistantBubble = addBubble('assistant','');
    //   assistantBubble.textContent += msg.text;
    //   chatEl.scrollTop = chatEl.scrollHeight;
    //   return;
    // }
    if(msg.type==='delta'){
      if(!assistantBubble) assistantBubble = addBubble('assistant','');
      assistantBubble.textEl.textContent += msg.text;
      chatEl.scrollTop = chatEl.scrollHeight;
      return;
    }
    // if(msg.type==='final'){
    //   if(!assistantBubble) assistantBubble = addBubble('assistant', msg.text);
    //   else assistantBubble.textContent = msg.text;
    //   assistantBubble = null;
    //   return;
    // }
    if(msg.type==='final'){
      if(!assistantBubble) assistantBubble = addBubble('assistant', msg.text);
      else assistantBubble.textEl.textContent = msg.text;

      // enable speaker button now that response is complete
      if(assistantBubble.ttsBtn) assistantBubble.ttsBtn.disabled = false;

      assistantBubble = null;
      return;
    }
    if(msg.type==='transcript'){
      addBubble('user', msg.text);
      return;
    }
    // if(msg.type==='audio'){
    //   if(msg.ok && msg.audio_base64){
    //     const audio = new Audio('data:audio/mpeg;base64,' + msg.audio_base64);
    //     audio.play().catch(()=>{});
    //   }
    //   return;
    // }
    if(msg.type==='audio'){
      // msg: {type:'audio', ok:true, audio_base64:'...', request_id:'...'}
      if(!msg.ok){
        // if there was a button waiting, reset it
        if(msg.request_id){
          const btn = document.querySelector(`button.tts-btn[data-id="${msg.request_id}"]`);
          if(btn){
            btn.disabled = false;
            btn.textContent = '🔊';
          }
        }
        return;
      }

      if(msg.ok && msg.audio_base64 && msg.request_id){
        const id = String(msg.request_id);
        const btn = document.querySelector(`button.tts-btn[data-id="${id}"]`);

        const audio = new Audio('data:audio/mpeg;base64,' + msg.audio_base64);
        audioPlayers.set(id, audio);

        audio.onended = () => {
          if(btn) btn.textContent = '🔊';
        };

        // auto-start once fetched (because user clicked speaker)
        stopAllAudioExcept(id);
        audio.play().catch(()=>{});

        if(btn){
          btn.disabled = false;
          btn.textContent = '⏸️';
        }
      }
      return;
    }
    
    if(msg.type==='error'){
      addBubble('assistant', '⚠️ ' + (msg.message || 'Error'));
      assistantBubble = null;
      return;
    }
  };

  ws.onclose = ()=>{ addBubble('assistant','Disconnected. Refresh to reconnect.'); };
}

connect();
setMode('text');

async function sendText(){
  const text = inputEl.value.trim();
  if(!text) return;
  addBubble('user', text);
  inputEl.value='';
  ws.send(JSON.stringify({type:'user', mode, text}));
}

document.getElementById('sendBtn').onclick = sendText;
inputEl.addEventListener('keydown', (e)=>{ if(e.key==='Enter' && !e.shiftKey){ e.preventDefault(); sendText(); }});

// Logout

document.getElementById('logoutBtn').onclick = async ()=>{
  await fetch('/api/logout', {method:'POST'}).catch(()=>{});
  window.location.href = '/login';
};

// Voice recording
async function setupRecorder(){
  const stream = await navigator.mediaDevices.getUserMedia({audio:true});
  mediaRecorder = new MediaRecorder(stream);
  mediaRecorder.ondataavailable = (e)=>{ if(e.data.size>0) chunks.push(e.data); };
  mediaRecorder.onstop = async ()=>{
    const blob = new Blob(chunks, {type: mediaRecorder.mimeType});
    chunks=[];
    const arrayBuffer = await blob.arrayBuffer();
    const bytes = new Uint8Array(arrayBuffer);
    let binary='';
    for(let i=0;i<bytes.length;i++) binary += String.fromCharCode(bytes[i]);
    const b64 = btoa(binary);
    ws.send(JSON.stringify({type:'user', mode, audio_base64: b64, audio_mime: blob.type}));
  };
}

let recording=false;
document.getElementById('recBtn').onclick = async ()=>{
  if(!mediaRecorder) await setupRecorder();
  if(!recording){
    recording=true;
    document.getElementById('recBtn').textContent='⏹️';
    mediaRecorder.start();
  } else {
    recording=false;
    document.getElementById('recBtn').textContent='🎙️';
    mediaRecorder.stop();
  }
};