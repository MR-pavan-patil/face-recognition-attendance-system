/**
 * capture.js — Webcam Dataset Capture
 * Manual + Auto capture, base64 → Flask backend
 */
'use strict';

const video          = document.getElementById('videoFeed');
const captureBtn     = document.getElementById('captureBtn');
const autoCaptureChk = document.getElementById('autoCapture');
const captureCount   = document.getElementById('captureCount');
const progressBar    = document.getElementById('captureProgress');
const progressPct    = document.getElementById('progressPct');
const progressTag    = document.getElementById('progressTag');
const statusMsg      = document.getElementById('statusMsg');
const markDoneBtn    = document.getElementById('markDoneBtn');
const resetBtn       = document.getElementById('resetBtn');
const flipBtn        = document.getElementById('flipBtn');
const captureFlash   = document.getElementById('captureFlash');
const camStatusDot   = document.getElementById('camStatusDot');
const camStatusText  = document.getElementById('camStatusText');
const captureTip     = document.getElementById('captureTip');
const noCamera       = document.getElementById('noCamera');

const studentId    = document.getElementById('studentId').value;
const studentName  = document.getElementById('studentName').value;
let   totalCaptured = parseInt(document.getElementById('existingCount').value) || 0;

const TARGET_PHOTOS = 30;
const AUTO_INTERVAL = 1200;
let stream      = null;
let autoTimer   = null;
let facingMode  = 'user';
let isCapturing = false;

const TIPS = [
  "Look straight at the camera",
  "Slowly turn your head left",
  "Slowly turn your head right",
  "Tilt head slightly up",
  "Tilt head slightly down",
  "Keep a neutral expression",
  "Try a slight smile",
  "Remove glasses for a few shots",
  "Ensure face is well lit",
  "Keep background simple",
];
let tipIndex = 0;
setInterval(() => {
  tipIndex = (tipIndex + 1) % TIPS.length;
  if (captureTip) captureTip.textContent = TIPS[tipIndex];
}, 3500);


async function startCamera() {
  try {
    if (stream) stream.getTracks().forEach(t => t.stop());
    stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode, width: { ideal: 640 }, height: { ideal: 480 } },
      audio: false,
    });
    video.srcObject = stream;
    video.onloadedmetadata = () => {
      setCamStatus('online', 'Camera ready — position your face');
      captureBtn.disabled = false;
    };
  } catch (err) {
    setCamStatus('offline', 'Camera access denied');
    noCamera.style.display = 'flex';
    video.style.display    = 'none';
    showToast('Allow camera permission in browser settings', 'error');
  }
}

function setCamStatus(state, text) {
  camStatusText.textContent = text;
  camStatusDot.className    = 'cam-status-dot ' + state;
}


async function capturePhoto() {
  if (isCapturing || !stream) return;
  if (totalCaptured >= TARGET_PHOTOS) {
    showToast('30 photos already captured!', 'warning'); return;
  }
  isCapturing = true;

  captureFlash.classList.add('flash-active');
  setTimeout(() => captureFlash.classList.remove('flash-active'), 200);

  const canvas  = document.createElement('canvas');
  canvas.width  = video.videoWidth  || 640;
  canvas.height = video.videoHeight || 480;
  const ctx = canvas.getContext('2d');
  if (facingMode === 'user') { ctx.translate(canvas.width, 0); ctx.scale(-1, 1); }
  ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

  const imageData = canvas.toDataURL('image/jpeg', 0.88);

  try {
    const response = await fetch('/capture/save', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ student_id: studentId, image: imageData }),
    });
    const result = await response.json();
    if (result.success) {
      totalCaptured = result.total;
      updateProgress();
      setCamStatus('online', `Photo ${totalCaptured} saved ✓`);
    } else {
      showToast('Save failed: ' + result.error, 'error');
    }
  } catch (err) {
    showToast('Network error — is server running?', 'error');
  } finally {
    isCapturing = false;
  }
}


function updateProgress() {
  const pct = Math.min(Math.round((totalCaptured / TARGET_PHOTOS) * 100), 100);
  captureCount.textContent = totalCaptured;
  progressBar.style.width  = pct + '%';
  progressPct.textContent  = pct + '% complete';
  progressTag.textContent  = `${totalCaptured} / ${TARGET_PHOTOS}`;
  const remaining = TARGET_PHOTOS - totalCaptured;
  if (totalCaptured >= TARGET_PHOTOS) {
    statusMsg.innerHTML = `<i class="bi bi-check-circle-fill text-success me-2"></i><strong>Dataset complete!</strong> Click "Mark Dataset Ready".`;
    markDoneBtn.disabled = false;
    stopAutoCapture();
    setCamStatus('online', '✓ All 30 photos captured!');
    showToast(`All ${TARGET_PHOTOS} photos done for ${studentName}!`, 'success');
  } else {
    statusMsg.innerHTML = `<i class="bi bi-camera me-2 text-accent"></i>${remaining} more photo${remaining!==1?'s':''} needed.`;
  }
}


function startAutoCapture() {
  if (autoTimer) return;
  setCamStatus('online', 'Auto-capture running...');
  autoTimer = setInterval(() => {
    if (totalCaptured < TARGET_PHOTOS) capturePhoto();
    else stopAutoCapture();
  }, AUTO_INTERVAL);
}

function stopAutoCapture() {
  if (autoTimer) { clearInterval(autoTimer); autoTimer = null; }
  if (autoCaptureChk) autoCaptureChk.checked = false;
}


markDoneBtn.addEventListener('click', async () => {
  markDoneBtn.disabled = true;
  markDoneBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Saving...';
  try {
    const res    = await fetch(`/capture/${studentId}/done`, { method: 'POST' });
    const result = await res.json();
    if (result.success) {
      showToast(`✓ Dataset marked ready for ${studentName}!`, 'success');
      setTimeout(() => { window.location.href = '/students/'; }, 1500);
    } else {
      showToast('Error: ' + result.error, 'error');
      markDoneBtn.disabled = false;
      markDoneBtn.innerHTML = '<i class="bi bi-check-circle-fill me-2"></i>Mark Dataset Ready';
    }
  } catch {
    showToast('Network error', 'error');
    markDoneBtn.disabled = false;
    markDoneBtn.innerHTML = '<i class="bi bi-check-circle-fill me-2"></i>Mark Dataset Ready';
  }
});

resetBtn.addEventListener('click', async () => {
  if (!confirm(`Reset all photos for "${studentName}"? Cannot be undone.`)) return;
  try {
    const res    = await fetch(`/capture/${studentId}/reset`, { method: 'POST' });
    const result = await res.json();
    if (result.success) {
      totalCaptured = 0; updateProgress();
      markDoneBtn.disabled = true;
      showToast('Dataset reset. Start capturing again.', 'info');
    }
  } catch { showToast('Reset failed', 'error'); }
});

captureBtn.addEventListener('click', capturePhoto);

autoCaptureChk.addEventListener('change', () => {
  if (autoCaptureChk.checked) { startAutoCapture(); showToast('Auto-capture ON — every 1.2s', 'info'); }
  else { stopAutoCapture(); setCamStatus('online', 'Auto-capture stopped'); }
});

flipBtn.addEventListener('click', () => {
  facingMode = facingMode === 'user' ? 'environment' : 'user';
  startCamera();
});

document.addEventListener('keydown', (e) => {
  if (e.code === 'Space' && !e.target.matches('input, textarea')) {
    e.preventDefault(); capturePhoto();
  }
});

video.style.transform = 'scaleX(-1)';

document.addEventListener('DOMContentLoaded', () => {
  updateProgress();
  startCamera();
});
