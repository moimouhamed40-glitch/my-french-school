/**
 * main.js — École FLE Global JavaScript
 * Exercise widgets, chatbot, grammar corrector, notifications
 */

"use strict";

// ── CSRF Helper ───────────────────────────────────────────────────────────────
function getCsrf() {
  return document.cookie.split(';')
    .find(c => c.trim().startsWith('csrftoken='))?.split('=')[1] || '';
}

// ── API Helper ────────────────────────────────────────────────────────────────
async function apiPost(url, data) {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrf() },
    body: JSON.stringify(data),
  });
  return res.json();
}

// ── EXERCISE WIDGETS ──────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  initMCQExercises();
  initFillBlankExercises();
  initOrderSentenceExercises();
  initChatbot();
  initGrammarAjax();
  initNotificationPoller();
  initProgressBars();
  initTooltips();
  initAutoSave();
});

// ── MCQ ───────────────────────────────────────────────────────────────────────
function initMCQExercises() {
  document.querySelectorAll('.exercise-mcq').forEach(widget => {
    const exerciseId = widget.dataset.exerciseId;
    const options = widget.querySelectorAll('.exercise-option');

    options.forEach(opt => {
      opt.addEventListener('click', async () => {
        if (widget.dataset.submitted === 'true') return;
        options.forEach(o => o.classList.remove('selected'));
        opt.classList.add('selected');

        const choice = opt.dataset.choice;
        widget.dataset.submitted = 'true';

        const result = await apiPost(`/courses/exercise/${exerciseId}/submit/`, { answer: choice });
        renderExerciseResult(widget, result, opt, options);
      });
    });
  });
}

// ── FILL IN THE BLANK ─────────────────────────────────────────────────────────
function initFillBlankExercises() {
  document.querySelectorAll('.exercise-fill-blank').forEach(widget => {
    const exerciseId = widget.dataset.exerciseId;
    const btn = widget.querySelector('.btn-submit-fill');

    btn?.addEventListener('click', async () => {
      if (widget.dataset.submitted === 'true') return;
      const inputs = widget.querySelectorAll('.blank-input');
      const answers = Array.from(inputs).map(i => i.value.trim());

      if (answers.some(a => !a)) {
        showToast('Remplissez tous les champs avant de valider.', 'warning');
        return;
      }

      widget.dataset.submitted = 'true';
      btn.disabled = true;

      const result = await apiPost(`/courses/exercise/${exerciseId}/submit/`, { answer: answers });
      renderFillBlankResult(widget, result, inputs);
    });
  });
}

function renderFillBlankResult(widget, result, inputs) {
  const feedback = widget.querySelector('.exercise-feedback');
  const correctAnswers = result.correct_answer?.answers || [];

  inputs.forEach((input, i) => {
    const isCorrect = input.value.trim().toLowerCase() === (correctAnswers[i] || '').toLowerCase();
    input.style.borderBottomColor = isCorrect ? '#16a34a' : '#dc2626';
    input.style.color = isCorrect ? '#16a34a' : '#dc2626';
    input.disabled = true;
    if (!isCorrect && correctAnswers[i]) {
      const hint = document.createElement('small');
      hint.className = 'text-success ms-1';
      hint.textContent = `→ ${correctAnswers[i]}`;
      input.parentNode.insertBefore(hint, input.nextSibling);
    }
  });

  showFeedback(feedback, result);
  updateScore(result.score);
}

// ── ORDER SENTENCE ────────────────────────────────────────────────────────────
function initOrderSentenceExercises() {
  document.querySelectorAll('.exercise-order').forEach(widget => {
    const exerciseId = widget.dataset.exerciseId;
    const wordBank = widget.querySelector('.word-bank');
    const answerArea = widget.querySelector('.answer-area');
    const btn = widget.querySelector('.btn-submit-order');

    // Drag and drop setup
    let dragged = null;

    widget.addEventListener('dragstart', e => {
      if (e.target.classList.contains('word-chip')) {
        dragged = e.target;
        e.target.classList.add('dragging');
        e.dataTransfer.effectAllowed = 'move';
      }
    });

    widget.addEventListener('dragend', e => {
      e.target.classList.remove('dragging');
    });

    [wordBank, answerArea].forEach(zone => {
      zone.addEventListener('dragover', e => { e.preventDefault(); e.dataTransfer.dropEffect = 'move'; });
      zone.addEventListener('drop', e => {
        e.preventDefault();
        if (dragged) zone.appendChild(dragged);
      });
    });

    // Click to move
    wordBank?.querySelectorAll('.word-chip').forEach(chip => {
      chip.addEventListener('click', () => {
        if (!widget.dataset.submitted) answerArea.appendChild(chip);
      });
    });

    answerArea?.querySelectorAll('.word-chip').forEach(chip => {
      chip.addEventListener('click', () => {
        if (!widget.dataset.submitted) wordBank.appendChild(chip);
      });
    });

    btn?.addEventListener('click', async () => {
      if (widget.dataset.submitted === 'true') return;
      const chips = answerArea.querySelectorAll('.word-chip');
      const order = Array.from(chips).map(c => c.dataset.word);

      if (!order.length) { showToast('Placez les mots dans l\'ordre avant de valider.', 'warning'); return; }

      widget.dataset.submitted = 'true';
      btn.disabled = true;

      const result = await apiPost(`/courses/exercise/${exerciseId}/submit/`, { answer: order });
      renderOrderResult(widget, result, chips);
    });
  });
}

function renderOrderResult(widget, result, chips) {
  const correctOrder = result.correct_answer?.order || [];
  chips.forEach((chip, i) => {
    const isCorrect = chip.dataset.word === correctOrder[i];
    chip.style.background = isCorrect ? '#dcfce7' : '#fee2e2';
    chip.style.color = isCorrect ? '#166534' : '#991b1b';
    chip.style.border = `2px solid ${isCorrect ? '#16a34a' : '#dc2626'}`;
    chip.setAttribute('draggable', 'false');
  });

  const feedback = widget.querySelector('.exercise-feedback');
  if (!result.is_correct && correctOrder.length) {
    const correctDisplay = document.createElement('div');
    correctDisplay.className = 'mt-2 p-2 bg-light rounded small';
    correctDisplay.innerHTML = `<strong>Ordre correct :</strong> ${correctOrder.join(' ')}`;
    feedback.parentNode.insertBefore(correctDisplay, feedback);
  }

  showFeedback(feedback, result);
  updateScore(result.score);
}

// ── EXERCISE RESULT RENDERING ─────────────────────────────────────────────────
function renderExerciseResult(widget, result, selectedOpt, allOptions) {
  const correctChoice = result.correct_answer?.choice;
  allOptions.forEach(opt => {
    const isSelected = opt === selectedOpt;
    const isCorrect = opt.dataset.choice === correctChoice;
    opt.classList.remove('selected');
    if (isCorrect) opt.classList.add('correct');
    else if (isSelected && !isCorrect) opt.classList.add('incorrect');
    opt.style.pointerEvents = 'none';
  });

  widget.classList.add(result.is_correct ? 'correct' : 'incorrect');
  const feedback = widget.querySelector('.exercise-feedback');
  showFeedback(feedback, result);
  updateScore(result.score);
}

function showFeedback(feedbackEl, result) {
  if (!feedbackEl) return;
  feedbackEl.classList.remove('d-none', 'alert-success', 'alert-danger', 'alert-info');
  const cls = result.is_correct === true ? 'alert-success'
    : result.is_correct === false ? 'alert-danger' : 'alert-info';
  feedbackEl.classList.add('alert', cls);
  const icon = result.is_correct ? '✅' : result.is_correct === false ? '❌' : 'ℹ️';
  feedbackEl.innerHTML = `<strong>${icon} ${result.is_correct ? 'Bonne réponse !' : result.is_correct === false ? 'Incorrect.' : 'Enregistré.'}</strong>
    ${result.feedback ? `<p class="mb-0 mt-1">${result.feedback}</p>` : ''}
    ${result.score ? `<small class="d-block mt-1 text-muted">+${result.score} points</small>` : ''}`;
  feedbackEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function updateScore(points) {
  if (!points) return;
  const scoreEl = document.getElementById('studentScore');
  if (scoreEl) {
    scoreEl.textContent = parseInt(scoreEl.textContent || 0) + points;
    scoreEl.classList.add('text-success', 'fw-bold');
  }
  showToast(`+${points} points !`, 'success');
}

// ── CHATBOT ───────────────────────────────────────────────────────────────────
function initChatbot() {
  const chatForm = document.getElementById('chatbotForm');
  if (!chatForm) return;

  const input = document.getElementById('chatbotInput');
  const messages = document.getElementById('chatbotMessages');
  let sessionId = chatForm.dataset.sessionId || null;
  let isStreaming = false;

  // Use WebSocket for streaming if available
  const sessionIdInt = parseInt(sessionId);
  let streamWs = null;
  if (sessionId && !isNaN(sessionIdInt)) {
    const wsUrl = `ws://${window.location.host}/ws/chatbot/${sessionId}/`;
    try {
      streamWs = new WebSocket(wsUrl);
      setupStreamWs(streamWs, messages);
    } catch (e) { streamWs = null; }
  }

  chatForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const msg = input.value.trim();
    if (!msg || isStreaming) return;

    appendUserMessage(messages, msg);
    input.value = '';
    input.disabled = true;
    isStreaming = true;

    if (streamWs && streamWs.readyState === WebSocket.OPEN) {
      // Streaming mode
      showTypingIndicator(messages);
      streamWs.send(JSON.stringify({ message: msg }));
    } else {
      // Fallback AJAX
      const typingId = showTypingIndicator(messages);
      const result = await apiPost('/ai/chatbot/message/', { message: msg, session_id: sessionId });
      removeTypingIndicator(typingId, messages);

      if (result.session_id) {
        sessionId = result.session_id;
        chatForm.dataset.sessionId = sessionId;
      }

      if (result.response) appendAssistantMessage(messages, result.response);
      else appendAssistantMessage(messages, `Erreur : ${result.error || 'Connexion impossible.'}`);

      isStreaming = false;
      input.disabled = false;
      input.focus();
    }
  });

  input.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); chatForm.dispatchEvent(new Event('submit')); }
  });
}

function setupStreamWs(ws, messages) {
  let assistantDiv = null;
  let typingId = null;

  ws.onmessage = ({ data }) => {
    const msg = JSON.parse(data);
    if (msg.type === 'typing') {
      typingId = showTypingIndicator(messages);
    } else if (msg.type === 'stream_chunk') {
      if (!assistantDiv) {
        removeTypingIndicator(typingId, messages);
        assistantDiv = createAssistantBubble(messages);
      }
      assistantDiv.innerHTML += escapeHtml(msg.chunk);
      messages.scrollTop = messages.scrollHeight;
    } else if (msg.type === 'stream_done') {
      if (assistantDiv) renderMarkdown(assistantDiv);
      assistantDiv = null;
      const input = document.getElementById('chatbotInput');
      if (input) { input.disabled = false; input.focus(); }
    }
  };
}

function appendUserMessage(container, text) {
  const div = document.createElement('div');
  div.className = 'chatbot-msg user p-3 mb-3';
  div.textContent = text;
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
}

function createAssistantBubble(container) {
  const div = document.createElement('div');
  div.className = 'chatbot-msg assistant p-3 mb-3';
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
  return div;
}

function appendAssistantMessage(container, text) {
  const div = createAssistantBubble(container);
  div.innerHTML = renderMarkdownText(text);
  container.scrollTop = container.scrollHeight;
}

function showTypingIndicator(container) {
  const id = 'typing-' + Date.now();
  const div = document.createElement('div');
  div.id = id;
  div.className = 'chatbot-msg assistant p-3 mb-3 typing-indicator';
  div.innerHTML = '<span></span><span></span><span></span>';
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
  return id;
}

function removeTypingIndicator(id, container) {
  if (id) document.getElementById(id)?.remove();
}

function renderMarkdown(el) {
  el.innerHTML = renderMarkdownText(el.textContent);
}

function renderMarkdownText(text) {
  return text
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/`(.*?)`/g, '<code>$1</code>')
    .replace(/\n/g, '<br>');
}

// ── GRAMMAR CORRECTOR AJAX ────────────────────────────────────────────────────
function initGrammarAjax() {
  const form = document.getElementById('grammarForm');
  if (!form) return;

  const liveToggle = document.getElementById('liveGrammarToggle');
  const textarea = document.getElementById('id_text');
  let debounceTimer = null;

  if (liveToggle && textarea) {
    liveToggle.addEventListener('change', () => {
      if (liveToggle.checked) {
        textarea.addEventListener('input', onLiveInput);
      } else {
        textarea.removeEventListener('input', onLiveInput);
        clearGrammarHighlights();
      }
    });
  }

  function onLiveInput() {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(async () => {
      const text = textarea.value.trim();
      if (text.length < 20) return;
      const result = await apiPost('/ai/grammar/ajax/', { text });
      renderLiveErrors(result, textarea);
    }, 800);
  }

  function clearGrammarHighlights() {
    document.getElementById('grammarOverlay')?.remove();
  }

  function renderLiveErrors(result, textarea) {
    const errBadge = document.getElementById('liveErrorCount');
    if (errBadge) {
      errBadge.textContent = result.error_count || 0;
      errBadge.className = `badge ${result.error_count ? 'bg-danger' : 'bg-success'}`;
    }
  }
}

// ── NOTIFICATION POLLER ───────────────────────────────────────────────────────
function initNotificationPoller() {
  if (!document.body.dataset.userAuthenticated) return;

  setInterval(async () => {
    try {
      const res = await fetch('/api/accounts/notifications/');
      if (!res.ok) return;
      const data = await res.json();
      const unread = data.results?.filter(n => !n.is_read).length || 0;
      const badge = document.querySelector('.navbar .badge.bg-danger');
      if (badge) {
        badge.textContent = unread;
        badge.style.display = unread ? '' : 'none';
      }
    } catch (e) { /* silent fail */ }
  }, 60000); // every 60s
}

// ── PROGRESS BARS ─────────────────────────────────────────────────────────────
function initProgressBars() {
  document.querySelectorAll('.progress-bar[data-width]').forEach(bar => {
    setTimeout(() => {
      bar.style.width = bar.dataset.width + '%';
    }, 200);
  });
}

// ── TOOLTIPS ──────────────────────────────────────────────────────────────────
function initTooltips() {
  const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
  tooltipTriggerList.forEach(el => new bootstrap.Tooltip(el));
}

// ── AUTO-SAVE DRAFT ───────────────────────────────────────────────────────────
function initAutoSave() {
  const draftForms = document.querySelectorAll('form[data-autosave]');
  draftForms.forEach(form => {
    const key = form.dataset.autosave;
    // Restore draft
    const saved = localStorage.getItem(`draft_${key}`);
    if (saved) {
      try {
        const data = JSON.parse(saved);
        Object.entries(data).forEach(([name, val]) => {
          const field = form.querySelector(`[name="${name}"]`);
          if (field && field.tagName === 'TEXTAREA') field.value = val;
        });
      } catch (e) {}
    }
    // Save on input
    form.addEventListener('input', () => {
      const data = {};
      form.querySelectorAll('textarea[name]').forEach(f => { data[f.name] = f.value; });
      localStorage.setItem(`draft_${key}`, JSON.stringify(data));
    });
    // Clear on submit
    form.addEventListener('submit', () => localStorage.removeItem(`draft_${key}`));
  });
}

// ── TOAST ─────────────────────────────────────────────────────────────────────
function showToast(message, type = 'info') {
  let container = document.getElementById('toastContainer');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toastContainer';
    container.className = 'toast-container position-fixed bottom-0 end-0 p-3';
    container.style.zIndex = '9999';
    document.body.appendChild(container);
  }

  const iconMap = { success: 'check-circle-fill', danger: 'x-circle-fill', warning: 'exclamation-triangle-fill', info: 'info-circle-fill' };
  const toastEl = document.createElement('div');
  toastEl.className = `toast align-items-center text-bg-${type} border-0 show`;
  toastEl.setAttribute('role', 'alert');
  toastEl.innerHTML = `
    <div class="d-flex">
      <div class="toast-body">
        <i class="bi bi-${iconMap[type] || 'info-circle-fill'} me-2"></i>${message}
      </div>
      <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
    </div>`;

  container.appendChild(toastEl);
  const toast = new bootstrap.Toast(toastEl, { delay: 3500 });
  toast.show();
  toastEl.addEventListener('hidden.bs.toast', () => toastEl.remove());
}

// ── HELPERS ───────────────────────────────────────────────────────────────────
function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// Expose globally for inline use
window.showToast = showToast;
window.getCsrf = getCsrf;
