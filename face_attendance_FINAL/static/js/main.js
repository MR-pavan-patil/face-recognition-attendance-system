/**
 * main.js — Global JS (Clock, Sidebar, Toast)
 */
'use strict';

function updateClock() {
  const el = document.getElementById('clockDisplay');
  if (!el) return;
  el.textContent = new Date().toLocaleTimeString('en-IN', {
    hour:'2-digit', minute:'2-digit', second:'2-digit', hour12:true
  });
}
updateClock();
setInterval(updateClock, 1000);

const sidebarToggle = document.getElementById('sidebarToggle');
const sidebar       = document.getElementById('sidebar');
if (sidebarToggle && sidebar) {
  sidebarToggle.addEventListener('click', () => sidebar.classList.toggle('open'));
  document.addEventListener('click', (e) => {
    if (window.innerWidth <= 768 &&
        !sidebar.contains(e.target) &&
        !sidebarToggle.contains(e.target)) {
      sidebar.classList.remove('open');
    }
  });
}

function showToast(message, type = 'info') {
  const colors = { success:'#2dd471', error:'#ff5c5c', info:'#5294ff', warning:'#ffb347' };
  const toast = document.createElement('div');
  toast.style.cssText = `
    position:fixed;bottom:24px;right:24px;z-index:9999;
    background:#0f1621;border:1px solid ${colors[type]}44;
    color:#edf2ff;padding:13px 20px;border-radius:12px;
    font-family:'Inter',sans-serif;font-size:13.5px;font-weight:500;
    box-shadow:0 8px 32px rgba(0,0,0,.5);
    display:flex;align-items:center;gap:10px;
    animation:fadeSlideUp .3s ease;max-width:340px;
  `;
  toast.innerHTML = `<span style="color:${colors[type]};font-size:18px;">●</span>${message}`;
  document.body.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transition = 'opacity .3s ease';
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.flash-alert').forEach(alert => {
    setTimeout(() => {
      alert.style.opacity = '0';
      alert.style.transition = 'opacity .4s ease';
      setTimeout(() => alert.remove(), 400);
    }, 5000);
  });
  console.log('%c FaceAttend Day 4 ✓', 'color:#5294ff;font-weight:bold;font-size:14px;');
});
