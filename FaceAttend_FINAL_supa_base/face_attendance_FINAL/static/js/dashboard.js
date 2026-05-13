/**
 * dashboard.js — Counter animations & stats refresh
 */
'use strict';

function animateCounter(el, target, suffix = '', duration = 1400) {
  const startTime = performance.now();
  function update(now) {
    const progress = Math.min((now - startTime) / duration, 1);
    const eased    = 1 - Math.pow(1 - progress, 3);
    el.textContent = Math.round(target * eased) + suffix;
    if (progress < 1) requestAnimationFrame(update);
    else el.textContent = target + suffix;
  }
  requestAnimationFrame(update);
}

function initCounters() {
  document.querySelectorAll('.stat-value[data-target]').forEach(el => {
    animateCounter(el, parseFloat(el.dataset.target), el.dataset.suffix || '');
  });
}

function initProgressBars() {
  document.querySelectorAll('.progress-bar[data-width]').forEach(bar => {
    setTimeout(() => { bar.style.width = bar.dataset.width + '%'; }, 300);
  });
}

async function refreshStats() {
  const icon = document.getElementById('refreshIcon');
  if (icon) icon.style.animation = 'spin .8s linear infinite';
  try {
    const res  = await fetch('/api/stats');
    const data = await res.json();
    const vals = [data.total_students, data.present_today, data.absent_today, data.dataset_ready || 0];
    document.querySelectorAll('.stat-value[data-target]').forEach((el, i) => {
      animateCounter(el, vals[i], el.dataset.suffix || '', 800);
    });
    showToast('Stats refreshed!', 'success');
  } catch {
    showToast('Refresh failed. Check server.', 'error');
  } finally {
    if (icon) setTimeout(() => icon.style.animation = '', 800);
  }
}

const spinStyle = document.createElement('style');
spinStyle.textContent = '@keyframes spin{from{transform:rotate(0)}to{transform:rotate(360deg)}}';
document.head.appendChild(spinStyle);

document.addEventListener('DOMContentLoaded', () => {
  setTimeout(initCounters,     400);
  setTimeout(initProgressBars, 500);
});
