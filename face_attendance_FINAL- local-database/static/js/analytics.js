/**
 * analytics.js — Advanced Analytics Charts (Chart.js 4)
 */
'use strict';

const chartColors = {
  accent: '#5294ff', green: '#2dd471', red: '#ff5c5c',
  amber: '#ffb347', purple: '#a78bfa', text: '#94a3c0',
  grid: 'rgba(255,255,255,0.04)', bg: '#0f1621'
};

const chartDefaults = {
  responsive: true,
  plugins: { legend: { labels: { color: chartColors.text, font: { size: 11 } } } },
  scales: {
    x: { ticks: { color: '#4e6080', font: { size: 10 } }, grid: { color: chartColors.grid } },
    y: { ticks: { color: '#4e6080', font: { size: 10 } }, grid: { color: chartColors.grid }, beginAtZero: true }
  }
};

let trendChart, statusChart, deptChart, monthlyChart, timeChart;

function getDept() {
  const el = document.getElementById('deptFilter');
  return el ? el.value : 'all';
}
function getDays() {
  const el = document.getElementById('periodFilter');
  return el ? el.value : '30';
}

// ── 1. Attendance Trend ────────────────────────────────────
async function loadTrend() {
  const dept = getDept(), days = getDays();
  const res = await fetch(`/analytics/api/trends?dept=${dept}&days=${days}`);
  const d = await res.json();
  const ctx = document.getElementById('trendChart');
  if (!ctx) return;
  if (trendChart) trendChart.destroy();
  trendChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: d.data.map(x => x.date),
      datasets: [{
        label: 'Attendance %', data: d.data.map(x => x.pct),
        borderColor: chartColors.green, backgroundColor: 'rgba(45,212,113,0.08)',
        fill: true, tension: 0.4, pointRadius: 2, pointBackgroundColor: chartColors.green,
        borderWidth: 2
      }]
    },
    options: {
      ...chartDefaults,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: ctx => `${ctx.parsed.y}% (${d.data[ctx.dataIndex].present}/${d.total})`
          }
        }
      },
      scales: {
        ...chartDefaults.scales,
        y: { ...chartDefaults.scales.y, max: 100, ticks: { ...chartDefaults.scales.y.ticks, callback: v => v + '%' } }
      }
    }
  });
  const label = document.getElementById('trendPeriodLabel');
  if (label) label.textContent = days + ' Days';
}

// ── 2. Status Distribution (Doughnut) ──────────────────────
async function loadStatus() {
  const res = await fetch(`/analytics/api/status-distribution?dept=${getDept()}`);
  const d = await res.json();
  const ctx = document.getElementById('statusChart');
  if (!ctx) return;
  if (statusChart) statusChart.destroy();
  statusChart = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: ['Good (≥75%)', 'Low (50-74%)', 'Critical (<50%)'],
      datasets: [{
        data: [d.good, d.low, d.critical],
        backgroundColor: [chartColors.green, chartColors.amber, chartColors.red],
        borderColor: chartColors.bg, borderWidth: 3, hoverOffset: 8
      }]
    },
    options: {
      responsive: true, cutout: '62%',
      plugins: {
        legend: { position: 'bottom', labels: { color: chartColors.text, font: { size: 11 }, padding: 16 } }
      }
    }
  });
}

// ── 3. Department Comparison ────────────────────────────────
async function loadDept() {
  const res = await fetch('/analytics/api/department');
  const d = await res.json();
  const ctx = document.getElementById('deptChart');
  if (!ctx) return;
  if (deptChart) deptChart.destroy();
  deptChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: d.map(x => x.department),
      datasets: [{
        label: 'Attendance %', data: d.map(x => x.pct),
        backgroundColor: d.map(x => x.pct >= 75 ? 'rgba(45,212,113,0.7)' : x.pct >= 50 ? 'rgba(255,179,71,0.7)' : 'rgba(255,92,92,0.7)'),
        borderRadius: 6, barThickness: 28
      }]
    },
    options: {
      ...chartDefaults, indexAxis: 'y',
      plugins: { legend: { display: false } },
      scales: {
        x: { ...chartDefaults.scales.x, max: 100, ticks: { ...chartDefaults.scales.x.ticks, callback: v => v + '%' } },
        y: { ...chartDefaults.scales.y, ticks: { color: '#94a3c0', font: { size: 12 } } }
      }
    }
  });
}

// ── 4. Monthly Averages ─────────────────────────────────────
async function loadMonthly() {
  const res = await fetch(`/analytics/api/monthly-avg?dept=${getDept()}`);
  const d = await res.json();
  const ctx = document.getElementById('monthlyChart');
  if (!ctx) return;
  if (monthlyChart) monthlyChart.destroy();
  monthlyChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: d.map(x => x.month_short),
      datasets: [{
        label: 'Avg %', data: d.map(x => x.pct),
        backgroundColor: 'rgba(82,148,255,0.6)', borderColor: chartColors.accent,
        borderWidth: 1, borderRadius: 6, barThickness: 32
      }]
    },
    options: {
      ...chartDefaults,
      plugins: { legend: { display: false } },
      scales: {
        ...chartDefaults.scales,
        y: { ...chartDefaults.scales.y, max: 100, ticks: { ...chartDefaults.scales.y.ticks, callback: v => v + '%' } }
      }
    }
  });
}

// ── 5. Top/Bottom Students ──────────────────────────────────
async function loadTopBottom() {
  const res = await fetch(`/analytics/api/top-students?dept=${getDept()}`);
  const d = await res.json();
  const topEl = document.getElementById('topStudentsList');
  const botEl = document.getElementById('bottomStudentsList');
  if (!topEl || !botEl) return;

  function renderList(container, students, colorVar) {
    container.innerHTML = students.map(s => `
      <div style="display:flex;align-items:center;gap:12px;padding:8px 0;border-bottom:1px solid var(--border-subtle)">
        <div class="student-avatar" style="width:32px;height:32px;font-size:13px">${s.name[0]}</div>
        <div style="flex:1;min-width:0">
          <div style="font-weight:600;font-size:13px;color:var(--text-primary);white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${s.name}</div>
          <div style="font-size:11px;color:var(--text-muted)">${s.roll_number} · ${s.department}</div>
        </div>
        <div style="text-align:right">
          <span style="font-weight:800;font-size:15px;color:var(${colorVar})">${s.pct}%</span>
          <div style="font-size:10px;color:var(--text-muted)">${s.days_present}/${d.working_days}d</div>
        </div>
      </div>
    `).join('');
    if (!students.length) container.innerHTML = '<p style="color:var(--text-muted);font-size:13px">No data</p>';
  }
  renderList(topEl, d.top, '--green');
  renderList(botEl, d.bottom, '--red');
}

// ── 6. Time Distribution ────────────────────────────────────
async function loadTime() {
  const res = await fetch(`/analytics/api/time-distribution?dept=${getDept()}`);
  const d = await res.json();
  const ctx = document.getElementById('timeChart');
  if (!ctx) return;
  if (timeChart) timeChart.destroy();
  const colors = ['rgba(45,212,113,0.8)', 'rgba(82,148,255,0.8)', 'rgba(167,139,250,0.8)', 'rgba(255,179,71,0.8)', 'rgba(255,92,92,0.8)'];
  timeChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: d.map(x => x.label),
      datasets: [{
        label: 'Students', data: d.map(x => x.count),
        backgroundColor: colors, borderRadius: 6, barThickness: 28
      }]
    },
    options: { ...chartDefaults, plugins: { legend: { display: false } } }
  });
}

// ── 7. Heatmap ──────────────────────────────────────────────
async function loadHeatmap() {
  const res = await fetch(`/analytics/api/heatmap?dept=${getDept()}`);
  const d = await res.json();
  const container = document.getElementById('heatmapContainer');
  if (!container) return;

  const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
  const slots = ['early', 'morning', 'afternoon', 'late'];
  const slotLabels = { early: 'Before 9', morning: '9-11 AM', afternoon: '11-2 PM', late: 'After 2' };

  let html = '<div class="heatmap-row heatmap-header"><div class="heatmap-label"></div>';
  slots.forEach(s => { html += `<div class="heatmap-slot-label">${slotLabels[s]}</div>`; });
  html += '</div>';

  const lookup = {};
  d.forEach(item => { lookup[`${item.day}-${item.slot}`] = item; });

  days.forEach(day => {
    html += `<div class="heatmap-row"><div class="heatmap-label">${day}</div>`;
    slots.forEach(slot => {
      const item = lookup[`${day}-${slot}`] || { count: 0, intensity: 0 };
      const intensity = Math.min(item.intensity * 1.5, 1);
      const bg = intensity > 0.6 ? `rgba(45,212,113,${0.3 + intensity * 0.7})` :
                 intensity > 0.2 ? `rgba(45,212,113,${0.1 + intensity * 0.5})` :
                 'rgba(82,148,255,0.06)';
      html += `<div class="heatmap-cell" style="background:${bg}" title="${day} ${slotLabels[slot]}: ${item.count}">
        <span>${item.count || ''}</span></div>`;
    });
    html += '</div>';
  });
  container.innerHTML = html;
}

// ── Load All ────────────────────────────────────────────────
function loadAll() {
  loadTrend(); loadStatus(); loadDept(); loadMonthly();
  loadTopBottom(); loadTime(); loadHeatmap();
}

document.addEventListener('DOMContentLoaded', () => {
  loadAll();
  const deptEl = document.getElementById('deptFilter');
  const periodEl = document.getElementById('periodFilter');
  if (deptEl) deptEl.addEventListener('change', loadAll);
  if (periodEl) periodEl.addEventListener('change', loadAll);
});
