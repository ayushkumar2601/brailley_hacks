/**
 * demo.js — Hackathon Demo Mode (fully isolated)
 *
 * This module is completely separate from the production OCR pipeline.
 * It provides a polished, scripted demo experience for judges.
 */

'use strict';

// ── Demo State ───────────────────────────────────────────────────────────────
let isDemoMode       = false;
let demoInProgress   = false;
let demoUtterance    = null;
let demoSpeechSynth  = window.speechSynthesis;

// ── Demo Constants ───────────────────────────────────────────────────────────
const DEMO_IMAGE_URL = '/static/demo_braille.png';
const DEMO_RESULT_TEXT = `Mary had a little lamb,\nIts fleece was white as snow.\nAnd everywhere that Mary went,\nThe lamb was sure to go.`;

const DEMO_SCAN_STEPS = [
  { text: 'Detecting Braille…',         icon: '🔍', duration: 900 },
  { text: 'Reconstructing Grid…',       icon: '🧩', duration: 800 },
  { text: 'Translating Characters…',    icon: '✨', duration: 900 },
  { text: 'Applying AI Correction…',    icon: '🤖', duration: 500 },
];

const DEMO_TOTAL_DURATION = DEMO_SCAN_STEPS.reduce((a, s) => a + s.duration, 0);

// ── DOM helpers ──────────────────────────────────────────────────────────────
function _el(id) { return document.getElementById(id); }

// ── Stop browser camera if active ────────────────────────────────────────────
function _stopBrowserCamera() {
  if (typeof browserStream !== 'undefined' && browserStream) {
    browserStream.getTracks().forEach(t => t.stop());
    browserStream = null;
  }
  if (typeof browserLoopId !== 'undefined' && browserLoopId) {
    cancelAnimationFrame(browserLoopId);
    browserLoopId = null;
  }
  if (typeof browserCameraActive !== 'undefined') {
    browserCameraActive = false;
  }
}

// ── Create or get demo overlay element ───────────────────────────────────────
function _getDemoOverlay() {
  let overlay = _el('demo-scan-overlay');
  if (!overlay) {
    overlay = document.createElement('div');
    overlay.id = 'demo-scan-overlay';
    overlay.className = 'demo-scan-overlay';
    overlay.innerHTML = `
      <div class="demo-scan-content">
        <div class="demo-scan-ring"></div>
        <div class="demo-scan-step-icon" id="demo-step-icon">🔍</div>
        <div class="demo-scan-step-text" id="demo-step-text">Initializing…</div>
        <div class="demo-scan-progress-wrap">
          <div class="demo-scan-progress-bar" id="demo-progress-bar"></div>
        </div>
        <div class="demo-scan-pct" id="demo-scan-pct">0%</div>
      </div>
    `;
    document.querySelector('.camera-wrap').appendChild(overlay);
  }
  return overlay;
}

// ── Create or get demo mode badge ────────────────────────────────────────────
function _getDemoBadge() {
  let badge = _el('demo-mode-badge');
  if (!badge) {
    badge = document.createElement('div');
    badge.id = 'demo-mode-badge';
    badge.className = 'demo-mode-badge';
    badge.innerHTML = '⚡ Demo Mode';
    document.querySelector('.camera-wrap').appendChild(badge);
  }
  return badge;
}

// ── Create demo TTS controls ─────────────────────────────────────────────────
function _getDemoTTSControls() {
  let controls = _el('demo-tts-controls');
  if (!controls) {
    controls = document.createElement('div');
    controls.id = 'demo-tts-controls';
    controls.className = 'demo-tts-controls';
    controls.innerHTML = `
      <button class="btn btn-primary demo-tts-btn" id="demo-tts-play" onclick="demoTTSPlay()" title="Play">
        <span class="demo-tts-btn-icon">▶</span> Play
      </button>
      <button class="btn btn-secondary demo-tts-btn" id="demo-tts-pause" onclick="demoTTSPause()" title="Pause">
        <span class="demo-tts-btn-icon">⏸</span> Pause
      </button>
      <button class="btn btn-secondary demo-tts-btn" id="demo-tts-replay" onclick="demoTTSReplay()" title="Replay">
        <span class="demo-tts-btn-icon">🔁</span> Replay
      </button>
    `;
    // Insert after the last-text-box
    const lastTextBox = document.querySelector('.last-text-box');
    if (lastTextBox && lastTextBox.parentNode) {
      lastTextBox.parentNode.insertBefore(controls, lastTextBox.nextSibling);
    }
  }
  return controls;
}

// ── Main Demo Entry Point ────────────────────────────────────────────────────
async function startHackathonDemo() {
  if (demoInProgress) return;
  demoInProgress = true;
  isDemoMode = true;

  // Show toast
  if (typeof showToast === 'function') {
    showToast('🚀 Starting Demo Mode…');
  }

  // Show exit demo button
  const exitBtn = _el('btn-exit-demo');
  if (exitBtn) exitBtn.style.display = '';

  // 1. Stop browser camera
  _stopBrowserCamera();

  // 2. Show demo image
  const camImg     = _el('camera-img');
  const noCamera   = _el('no-camera');
  const demoBadge  = _getDemoBadge();

  // Preload image
  const img = new Image();
  img.src = DEMO_IMAGE_URL;
  await new Promise((resolve) => {
    img.onload = resolve;
    img.onerror = resolve; // proceed even on error
  });

  camImg.src = DEMO_IMAGE_URL;
  camImg.style.display = 'block';
  camImg.style.objectFit = 'contain';
  noCamera.style.display = 'none';
  demoBadge.style.display = 'flex';

  // 3. Short delay, then start scanning animation
  await _sleep(400);
  await _runScanAnimation();

  // 4. Display result
  _displayDemoResult();

  // 5. Auto-play TTS
  await _sleep(300);
  demoTTSPlay();

  demoInProgress = false;
}

// ── Scanning Animation ───────────────────────────────────────────────────────
function _runScanAnimation() {
  return new Promise(async (resolve) => {
    const overlay   = _getDemoOverlay();
    const stepIcon  = _el('demo-step-icon');
    const stepText  = _el('demo-step-text');
    const bar       = _el('demo-progress-bar');
    const pctLabel  = _el('demo-scan-pct');

    overlay.style.display = 'flex';
    overlay.classList.add('active');

    let elapsed = 0;

    for (const step of DEMO_SCAN_STEPS) {
      stepIcon.textContent = step.icon;
      stepText.textContent = step.text;

      // Animate progress within this step
      const startPct = (elapsed / DEMO_TOTAL_DURATION) * 100;
      const endPct   = ((elapsed + step.duration) / DEMO_TOTAL_DURATION) * 100;

      await _animateProgress(bar, pctLabel, startPct, endPct, step.duration);
      elapsed += step.duration;
    }

    // Complete
    stepIcon.textContent = '✅';
    stepText.textContent = 'Translation Complete!';
    bar.style.width = '100%';
    pctLabel.textContent = '100%';

    await _sleep(500);

    overlay.classList.remove('active');
    overlay.style.display = 'none';
    resolve();
  });
}

function _animateProgress(bar, pctLabel, from, to, duration) {
  return new Promise((resolve) => {
    const startTime = performance.now();
    function tick(now) {
      const t = Math.min((now - startTime) / duration, 1);
      const eased = t < 0.5
        ? 2 * t * t
        : 1 - Math.pow(-2 * t + 2, 2) / 2; // ease-in-out quad
      const pct = from + (to - from) * eased;
      bar.style.width = pct + '%';
      pctLabel.textContent = Math.round(pct) + '%';
      if (t < 1) {
        requestAnimationFrame(tick);
      } else {
        resolve();
      }
    }
    requestAnimationFrame(tick);
  });
}

// ── Display Demo Result ──────────────────────────────────────────────────────
function _displayDemoResult() {
  const lastTextEl    = _el('last-text');
  const aiBadge       = _el('ai-badge');
  const confFill      = _el('conf-fill');
  const confPct       = _el('conf-pct');
  const historyList   = _el('history-list');
  const historyCountEl = _el('history-count');

  // Update detected text
  lastTextEl.textContent = DEMO_RESULT_TEXT;
  lastTextEl.classList.add('flash');
  setTimeout(() => lastTextEl.classList.remove('flash'), 800);

  // Show AI badge
  aiBadge.style.display = 'inline-flex';
  aiBadge.textContent = '⚡ AI Demo Result';

  // Update confidence to 97%
  const pct = 97;
  confFill.style.width = pct + '%';
  confPct.textContent  = pct + '%';
  confFill.className   = 'conf-fill high';

  // Update quality indicators
  const qQuality = _el('q-quality');
  const qDots    = _el('q-dots');
  if (qQuality) { qQuality.textContent = '✓ Scanning'; qQuality.style.color = 'var(--green)'; }
  if (qDots)    { qDots.textContent = '142'; }

  // Also update global state so existing code doesn't overwrite
  if (typeof lastText !== 'undefined') {
    lastText = DEMO_RESULT_TEXT;
  }

  // Add to history panel
  const now = new Date();
  const time = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  historyList.innerHTML = `
    <li class="history-item demo-history-item" onclick="demoTTSReplay()" title="Click to replay audio">
      <div style="flex:1">
        <div class="history-item-text">${DEMO_RESULT_TEXT.replace(/\n/g, '<br>')}</div>
        <div class="history-item-meta">${time} · 97%</div>
      </div>
      <span class="history-item-source demo">demo</span>
    </li>
  `;
  historyCountEl.textContent = '1 item';

  // Show TTS controls
  const ttsControls = _getDemoTTSControls();
  ttsControls.style.display = 'flex';

  // Update status badge
  const statusBadge = _el('status-badge');
  if (statusBadge) {
    statusBadge.textContent = '⚡ Demo Complete';
    statusBadge.className = 'badge badge-ok';
  }

  if (typeof showToast === 'function') {
    showToast('✅ Braille translated successfully!');
  }
}

// ── TTS Controls (Web Speech API) ────────────────────────────────────────────
function demoTTSPlay() {
  if (!demoSpeechSynth) return;

  // Cancel any existing speech
  demoSpeechSynth.cancel();

  demoUtterance = new SpeechSynthesisUtterance(DEMO_RESULT_TEXT);
  demoUtterance.rate   = 0.9;
  demoUtterance.pitch  = 1.0;
  demoUtterance.volume = 1.0;

  // Try to pick a clear English voice
  const voices = demoSpeechSynth.getVoices();
  const preferred = voices.find(v =>
    v.lang.startsWith('en') && (v.name.includes('Samantha') || v.name.includes('Google') || v.name.includes('Daniel'))
  ) || voices.find(v => v.lang.startsWith('en'));

  if (preferred) {
    demoUtterance.voice = preferred;
  }

  // UI state
  _updateTTSButtons('playing');

  demoUtterance.onend = () => _updateTTSButtons('stopped');
  demoUtterance.onerror = () => _updateTTSButtons('stopped');

  demoSpeechSynth.speak(demoUtterance);

  if (typeof showToast === 'function') {
    showToast('🔊 Reading braille translation aloud…');
  }
}

function demoTTSPause() {
  if (!demoSpeechSynth) return;
  if (demoSpeechSynth.speaking && !demoSpeechSynth.paused) {
    demoSpeechSynth.pause();
    _updateTTSButtons('paused');
  } else if (demoSpeechSynth.paused) {
    demoSpeechSynth.resume();
    _updateTTSButtons('playing');
  }
}

function demoTTSReplay() {
  demoTTSPlay();
}

function _updateTTSButtons(state) {
  const playBtn  = _el('demo-tts-play');
  const pauseBtn = _el('demo-tts-pause');
  if (!playBtn || !pauseBtn) return;

  if (state === 'playing') {
    playBtn.innerHTML  = '<span class="demo-tts-btn-icon">🔊</span> Playing…';
    playBtn.disabled   = true;
    pauseBtn.innerHTML = '<span class="demo-tts-btn-icon">⏸</span> Pause';
    pauseBtn.disabled  = false;
  } else if (state === 'paused') {
    playBtn.innerHTML  = '<span class="demo-tts-btn-icon">▶</span> Play';
    playBtn.disabled   = false;
    pauseBtn.innerHTML = '<span class="demo-tts-btn-icon">▶</span> Resume';
    pauseBtn.disabled  = false;
  } else {
    playBtn.innerHTML  = '<span class="demo-tts-btn-icon">▶</span> Play';
    playBtn.disabled   = false;
    pauseBtn.innerHTML = '<span class="demo-tts-btn-icon">⏸</span> Pause';
    pauseBtn.disabled  = true;
  }
}

// ── Exit Demo Mode ───────────────────────────────────────────────────────────
function exitDemoMode() {
  isDemoMode = false;

  // Cancel speech
  if (demoSpeechSynth) demoSpeechSynth.cancel();

  // Hide demo elements
  const badge = _el('demo-mode-badge');
  if (badge) badge.style.display = 'none';

  const ttsControls = _el('demo-tts-controls');
  if (ttsControls) ttsControls.style.display = 'none';

  // Hide exit demo button
  const exitBtn = _el('btn-exit-demo');
  if (exitBtn) exitBtn.style.display = 'none';

  // Reset text
  const lastTextEl = _el('last-text');
  if (lastTextEl) lastTextEl.textContent = 'Waiting for braille…';

  const aiBadge = _el('ai-badge');
  if (aiBadge) aiBadge.style.display = 'none';

  // Reset confidence
  const confFill = _el('conf-fill');
  const confPct  = _el('conf-pct');
  if (confFill) { confFill.style.width = '0%'; }
  if (confPct)  { confPct.textContent = '0%'; }

  // Re-show no camera
  const camImg   = _el('camera-img');
  const noCamera = _el('no-camera');
  if (camImg)   { camImg.src = ''; camImg.style.display = 'none'; }
  if (noCamera) { noCamera.style.display = 'flex'; }

  if (typeof showToast === 'function') {
    showToast('Demo mode ended — ready for live scanning');
  }
}

// ── Utility ──────────────────────────────────────────────────────────────────
function _sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

// ── Preload voices (needed for some browsers) ────────────────────────────────
if (demoSpeechSynth) {
  demoSpeechSynth.getVoices(); // trigger load
  if (demoSpeechSynth.onvoiceschanged !== undefined) {
    demoSpeechSynth.onvoiceschanged = () => demoSpeechSynth.getVoices();
  }
}
