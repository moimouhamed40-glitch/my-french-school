/**
 * live_stream.js
 * Agora RTC (video/audio/screen share) + Django Channels WebSocket (chat/polls/whiteboard)
 */

"use strict";

// ── STATE ────────────────────────────────────────────────────────────────────
let agoraClient, localAudioTrack, localVideoTrack, screenTrack;
let ws;
let isMicOn = true, isCameraOn = true, isScreenSharing = false, isWhiteboardOpen = false;
let remoteUsers = {};
let sessionStartTime = Date.now();
let chatUnread = 0;
let currentPollId = null;
let hasVoted = false;

// Whiteboard
let isDrawing = false, lastX = 0, lastY = 0;
let wbColor = '#000', wbWidth = 3;

// ── DOM REFS ─────────────────────────────────────────────────────────────────
const videoGrid       = document.getElementById('videoGrid');
const chatMessages    = document.getElementById('chatMessages');
const chatInput       = document.getElementById('chatInput');
const participantList = document.getElementById('participantsList');
const activePoll      = document.getElementById('activePoll');
const pollHistory     = document.getElementById('pollHistory');
const participantCount = document.getElementById('participantCount');
const sessionTimer    = document.getElementById('sessionTimer');
const canvas          = document.getElementById('whiteboardCanvas');
const ctx             = canvas ? canvas.getContext('2d') : null;

// ── INIT ─────────────────────────────────────────────────────────────────────
window.addEventListener('DOMContentLoaded', async () => {
  initTimer();
  initWebSocket();
  await initAgora();
  initControls();
  initWhiteboard();
});

// ── TIMER ─────────────────────────────────────────────────────────────────────
function initTimer() {
  setInterval(() => {
    const elapsed = Math.floor((Date.now() - sessionStartTime) / 1000);
    const h = String(Math.floor(elapsed / 3600)).padStart(2, '0');
    const m = String(Math.floor((elapsed % 3600) / 60)).padStart(2, '0');
    const s = String(elapsed % 60).padStart(2, '0');
    if (sessionTimer) sessionTimer.textContent = `${h}:${m}:${s}`;
  }, 1000);
}

// ── AGORA RTC ────────────────────────────────────────────────────────────────
async function initAgora() {
  agoraClient = AgoraRTC.createClient({ mode: 'rtc', codec: 'vp8' });

  agoraClient.on('user-published', async (user, mediaType) => {
    await agoraClient.subscribe(user, mediaType);
    if (mediaType === 'video') renderRemoteVideo(user);
    if (mediaType === 'audio') user.audioTrack.play();
    updateParticipantCount();
  });

  agoraClient.on('user-unpublished', (user, mediaType) => {
    if (mediaType === 'video') removeRemoteVideo(user.uid);
  });

  agoraClient.on('user-left', (user) => {
    removeRemoteVideo(user.uid);
    delete remoteUsers[user.uid];
    updateParticipantCount();
  });

  try {
    await agoraClient.join(AGORA_APP_ID, AGORA_CHANNEL, AGORA_TOKEN || null, USER_ID);
    [localAudioTrack, localVideoTrack] = await AgoraRTC.createMicrophoneAndCameraTracks();
    localVideoTrack.play('local-video');
    await agoraClient.publish([localAudioTrack, localVideoTrack]);
    updateParticipantCount();
  } catch (e) {
    console.warn('Agora not available (demo mode):', e.message);
    // Show placeholder in dev
    document.getElementById('local-video').innerHTML =
      '<div class="w-100 h-100 d-flex align-items-center justify-content-center text-muted">Caméra indisponible</div>';
  }
}

function renderRemoteVideo(user) {
  remoteUsers[user.uid] = user;
  const tile = document.createElement('div');
  tile.id = `remote-${user.uid}`;
  tile.className = 'video-tile position-relative';
  tile.style.cssText = 'width:280px; height:200px; background:#1a1a1a; border-radius:12px; overflow:hidden;';
  tile.innerHTML = `
    <div id="video-${user.uid}" class="w-100 h-100"></div>
    <div class="position-absolute bottom-0 start-0 m-2">
      <span class="badge bg-dark bg-opacity-75"><i class="bi bi-person-fill me-1"></i>Participant ${user.uid}</span>
    </div>`;
  videoGrid.appendChild(tile);
  user.videoTrack?.play(`video-${user.uid}`);
}

function removeRemoteVideo(uid) {
  document.getElementById(`remote-${uid}`)?.remove();
  updateParticipantCount();
}

function updateParticipantCount() {
  if (participantCount)
    participantCount.textContent = Object.keys(remoteUsers).length + 1;
}

// ── WEBSOCKET ─────────────────────────────────────────────────────────────────
function initWebSocket() {
  ws = new WebSocket(WS_URL);

  ws.onopen = () => console.log('WS connected');
  ws.onclose = (e) => {
    if (e.code !== 4001) {
      setTimeout(initWebSocket, 3000); // auto-reconnect
    }
  };

  ws.onmessage = ({ data }) => {
    const msg = JSON.parse(data);
    switch (msg.type) {
      case 'chat_history':    renderChatHistory(msg.messages); break;
      case 'chat_message':    appendChatMessage(msg); break;
      case 'presence':        handlePresence(msg); break;
      case 'poll_event':      handlePollEvent(msg); break;
      case 'whiteboard_op':   handleWhiteboardOp(msg.op); break;
      case 'session_end':     handleSessionEnd(msg.message); break;
      case 'error':           console.error('WS error:', msg.message); break;
    }
  };
}

function wsSend(data) {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify(data));
  }
}

// ── CHAT ─────────────────────────────────────────────────────────────────────
function renderChatHistory(messages) {
  messages.forEach(appendChatMessage);
}

function appendChatMessage(msg) {
  const isMine = msg.sender_id === USER_ID;
  const div = document.createElement('div');
  div.className = `chat-msg d-flex flex-column ${isMine ? 'align-items-end' : 'align-items-start'}`;
  div.innerHTML = `
    ${!isMine ? `<small class="text-muted mb-1" style="font-size:.7rem;">${msg.display_name}</small>` : ''}
    <div class="px-3 py-2 rounded-3" style="max-width:85%; background:${isMine ? '#0d6efd' : '#2a2a2a'}; word-break:break-word;">
      <span style="font-size:.88rem;">${escapeHtml(msg.message)}</span>
    </div>
    <small class="text-muted mt-1" style="font-size:.65rem;">${formatTime(msg.sent_at)}</small>`;
  chatMessages.appendChild(div);
  chatMessages.scrollTop = chatMessages.scrollHeight;

  // Badge if tab not active
  if (!document.getElementById('chatTab').classList.contains('active')) {
    chatUnread++;
    const badge = document.getElementById('chatBadge');
    badge.textContent = chatUnread;
    badge.classList.remove('d-none');
  }
}

// ── POLLS ─────────────────────────────────────────────────────────────────────
function handlePollEvent(msg) {
  if (msg.action === 'new_poll') renderActivePoll(msg);
  if (msg.action === 'poll_update') updatePollResults(msg.poll_id, msg.results);
  if (msg.action === 'poll_closed') closePollUI(msg.poll_id, msg.results);
}

function renderActivePoll(poll) {
  currentPollId = poll.poll_id;
  hasVoted = false;
  activePoll.classList.remove('d-none');

  let optionsHtml = '';
  if (poll.poll_type === 'yes_no') {
    optionsHtml = `
      <button class="btn btn-success w-100 mb-2" onclick="vote('yes')">✅ Oui</button>
      <button class="btn btn-danger w-100" onclick="vote('no')">❌ Non</button>`;
  } else {
    optionsHtml = (poll.options || []).map(opt =>
      `<button class="btn btn-outline-light w-100 mb-2" onclick="vote('${escapeHtml(opt)}')">${escapeHtml(opt)}</button>`
    ).join('');
  }

  activePoll.innerHTML = `
    <div class="card bg-dark border border-warning rounded-3 p-3">
      <div class="d-flex justify-content-between align-items-start mb-3">
        <h6 class="mb-0 text-warning"><i class="bi bi-bar-chart me-2"></i>Sondage en direct</h6>
        ${IS_HOST ? `<button class="btn btn-sm btn-outline-warning" onclick="closePoll()">Fermer</button>` : ''}
      </div>
      <p class="text-white mb-3">${escapeHtml(poll.question)}</p>
      <div id="pollOptions">${optionsHtml}</div>
      <div id="pollResultsBar" class="d-none mt-3"></div>
    </div>`;

  // Switch to polls tab
  document.querySelector('[data-bs-target="#pollsTab"]').click();
}

function vote(choice) {
  if (hasVoted) return;
  hasVoted = true;
  wsSend({ type: 'poll_vote', poll_id: currentPollId, choice });
  document.getElementById('pollOptions').innerHTML =
    `<p class="text-success"><i class="bi bi-check-circle me-1"></i>Vote enregistré : <strong>${escapeHtml(choice)}</strong></p>`;
}

function updatePollResults(pollId, results) {
  const bar = document.getElementById('pollResultsBar');
  if (!bar) return;
  bar.classList.remove('d-none');
  bar.innerHTML = renderResultsBars(results);
}

function closePollUI(pollId, results) {
  if (activePoll) {
    activePoll.innerHTML = `
      <div class="card bg-dark border-secondary rounded-3 p-3">
        <h6 class="text-muted mb-3">Résultats finaux</h6>
        ${renderResultsBars(results)}
      </div>`;
  }
}

function closePoll() {
  wsSend({ type: 'poll_close', poll_id: currentPollId });
}

function renderResultsBars(results) {
  const total = results.total || 1;
  return Object.entries(results)
    .filter(([k]) => k !== 'total')
    .map(([label, count]) => {
      const pct = Math.round((count / total) * 100);
      return `
        <div class="mb-2">
          <div class="d-flex justify-content-between small text-white mb-1">
            <span>${escapeHtml(label)}</span><span>${count} (${pct}%)</span>
          </div>
          <div class="progress" style="height:6px;">
            <div class="progress-bar bg-warning" style="width:${pct}%"></div>
          </div>
        </div>`;
    }).join('');
}

// ── PRESENCE ─────────────────────────────────────────────────────────────────
function handlePresence(msg) {
  if (msg.event === 'join') {
    addParticipantToList(msg);
    appendSystemMessage(`${msg.display_name} a rejoint la session.`);
  } else if (msg.event === 'leave') {
    removeParticipantFromList(msg.user_id);
    appendSystemMessage(`${msg.username} a quitté la session.`);
  } else if (msg.event === 'raise_hand') {
    appendSystemMessage(`✋ ${msg.username} lève la main.`);
  }
}

function addParticipantToList(user) {
  const li = document.createElement('li');
  li.id = `participant-${user.user_id}`;
  li.className = 'd-flex align-items-center gap-2 px-2 py-1 rounded';
  li.style.background = '#1e1e1e';
  li.innerHTML = `
    <i class="bi bi-person-circle text-muted"></i>
    <span class="text-white small flex-grow-1">${escapeHtml(user.display_name)}</span>
    ${user.role === 'teacher' ? '<span class="badge bg-primary">Enseignant</span>' : ''}`;
  participantList.appendChild(li);
}

function removeParticipantFromList(userId) {
  document.getElementById(`participant-${userId}`)?.remove();
}

function appendSystemMessage(text) {
  const div = document.createElement('div');
  div.className = 'text-center';
  div.innerHTML = `<small class="text-muted" style="font-size:.7rem;">${text}</small>`;
  chatMessages.appendChild(div);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

// ── WHITEBOARD ─────────────────────────────────────────────────────────────────
function initWhiteboard() {
  if (!canvas) return;

  const resize = () => {
    const parent = canvas.parentElement;
    canvas.width = parent.clientWidth;
    canvas.height = parent.clientHeight;
  };
  resize();
  window.addEventListener('resize', resize);

  canvas.addEventListener('mousedown', (e) => { isDrawing = true; [lastX, lastY] = [e.offsetX, e.offsetY]; });
  canvas.addEventListener('mouseup', () => { isDrawing = false; });
  canvas.addEventListener('mousemove', draw);
}

function draw(e) {
  if (!isDrawing || !ctx) return;
  ctx.beginPath();
  ctx.moveTo(lastX, lastY);
  ctx.lineTo(e.offsetX, e.offsetY);
  ctx.strokeStyle = wbColor;
  ctx.lineWidth = wbWidth;
  ctx.lineCap = 'round';
  ctx.stroke();

  // Send op to other participants
  wsSend({
    type: 'whiteboard_update',
    op: { x1: lastX, y1: lastY, x2: e.offsetX, y2: e.offsetY, color: wbColor, width: wbWidth },
  });
  [lastX, lastY] = [e.offsetX, e.offsetY];
}

function handleWhiteboardOp(op) {
  if (!ctx) return;
  ctx.beginPath();
  ctx.moveTo(op.x1, op.y1);
  ctx.lineTo(op.x2, op.y2);
  ctx.strokeStyle = op.color;
  ctx.lineWidth = op.width;
  ctx.lineCap = 'round';
  ctx.stroke();
}

// ── CONTROLS ─────────────────────────────────────────────────────────────────
function initControls() {
  // Mic toggle
  document.getElementById('toggleMic')?.addEventListener('click', async () => {
    isMicOn = !isMicOn;
    localAudioTrack?.setEnabled(isMicOn);
    const btn = document.getElementById('toggleMic');
    btn.classList.toggle('btn-danger', !isMicOn);
    btn.classList.toggle('btn-dark', isMicOn);
    btn.querySelector('i').className = `bi bi-mic${isMicOn ? '-fill' : '-mute-fill'} fs-5`;
  });

  // Camera toggle
  document.getElementById('toggleCamera')?.addEventListener('click', async () => {
    isCameraOn = !isCameraOn;
    localVideoTrack?.setEnabled(isCameraOn);
    const btn = document.getElementById('toggleCamera');
    btn.classList.toggle('btn-danger', !isCameraOn);
    btn.classList.toggle('btn-dark', isCameraOn);
  });

  // Screen share
  document.getElementById('toggleScreen')?.addEventListener('click', async () => {
    if (!isScreenSharing) {
      try {
        screenTrack = await AgoraRTC.createScreenVideoTrack();
        await agoraClient.unpublish(localVideoTrack);
        await agoraClient.publish(screenTrack);
        screenTrack.play('local-video');
        isScreenSharing = true;
      } catch (e) { console.warn('Screen share failed:', e); }
    } else {
      screenTrack?.close();
      await agoraClient.unpublish(screenTrack);
      await agoraClient.publish(localVideoTrack);
      localVideoTrack.play('local-video');
      isScreenSharing = false;
    }
    document.getElementById('toggleScreen')?.classList.toggle('btn-warning', isScreenSharing);
  });

  // Whiteboard toggle
  document.getElementById('toggleWhiteboard')?.addEventListener('click', () => {
    isWhiteboardOpen = !isWhiteboardOpen;
    document.getElementById('videoGrid').classList.toggle('d-none', isWhiteboardOpen);
    document.getElementById('whiteboardArea').classList.toggle('d-none', !isWhiteboardOpen);
    document.getElementById('toggleWhiteboard')?.classList.toggle('btn-warning', isWhiteboardOpen);
  });

  // Raise hand
  document.getElementById('raiseHandBtn')?.addEventListener('click', () => {
    wsSend({ type: 'raise_hand', raised: true });
  });

  // Chat send
  document.getElementById('sendChat')?.addEventListener('click', sendChat);
  chatInput?.addEventListener('keydown', (e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendChat(); } });

  // Clear chat badge on tab click
  document.querySelector('[data-bs-target="#chatTab"]')?.addEventListener('click', () => {
    chatUnread = 0;
    const badge = document.getElementById('chatBadge');
    badge.textContent = '0';
    badge.classList.add('d-none');
  });

  // Create poll
  document.getElementById('createPollBtn')?.addEventListener('click', () => {
    new bootstrap.Modal(document.getElementById('pollModal')).show();
  });

  document.getElementById('pollType')?.addEventListener('change', (e) => {
    document.getElementById('pollOptionsWrapper').classList.toggle('d-none', e.target.value !== 'multiple');
  });

  document.getElementById('submitPoll')?.addEventListener('click', () => {
    const question = document.getElementById('pollQuestion').value.trim();
    const poll_type = document.getElementById('pollType').value;
    const optText = document.getElementById('pollOptions')?.value || '';
    const options = optText.split('\n').map(s => s.trim()).filter(Boolean);
    if (!question) return;
    wsSend({ type: 'poll_create', question, poll_type, options });
    bootstrap.Modal.getInstance(document.getElementById('pollModal')).hide();
  });

  // End session
  document.getElementById('endSessionBtn')?.addEventListener('click', () => {
    new bootstrap.Modal(document.getElementById('endModal')).show();
  });

  document.getElementById('confirmEndBtn')?.addEventListener('click', async () => {
    wsSend({ type: 'session_end' });
    await fetch(`/live/${SESSION_UID}/end/`, { method: 'POST', headers: { 'X-CSRFToken': getCsrf() } });
    window.location.href = '/dashboard/';
  });
}

function sendChat() {
  const msg = chatInput?.value.trim();
  if (!msg) return;
  wsSend({ type: 'chat_message', message: msg });
  chatInput.value = '';
}

function handleSessionEnd(message) {
  document.body.innerHTML = `
    <div class="d-flex align-items-center justify-content-center vh-100 bg-dark text-white text-center">
      <div>
        <i class="bi bi-stop-circle-fill text-danger display-1 mb-4 d-block"></i>
        <h2>${message}</h2>
        <a href="/" class="btn btn-primary mt-4">Retour à l'accueil</a>
      </div>
    </div>`;
}

// ── UTILS ─────────────────────────────────────────────────────────────────────
function escapeHtml(str) {
  return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
function formatTime(iso) {
  return new Date(iso).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
}
function getCsrf() {
  return document.cookie.split(';').find(c => c.trim().startsWith('csrftoken='))?.split('=')[1] || '';
}
