/**
 * ui.js — shared UI helpers: toast notifications, the "growing circle"
 * pregnancy-week ring renderer, disclaimer snippet, and small formatting utils.
 */

const DISCLAIMER_TEXT = "This assistant provides educational information only and is not a substitute for professional medical advice. Always consult a qualified healthcare professional before making medical decisions.";

function renderDisclaimer(el) {
  if (el) el.innerHTML = `<div class="disclaimer-box">${DISCLAIMER_TEXT}</div>`;
}

function ensureToastRoot() {
  let root = document.getElementById('toast-root');
  if (!root) {
    root = document.createElement('div');
    root.id = 'toast-root';
    root.style.cssText = 'position:fixed;top:1.25rem;right:1.25rem;z-index:1080;display:flex;flex-direction:column;gap:0.6rem;';
    document.body.appendChild(root);
  }
  return root;
}

function toast(message, type = 'info') {
  const colors = {
    info: { bg: '#fff', border: 'var(--color-border)', text: 'var(--color-ink)' },
    success: { bg: 'var(--color-success-bg)', border: 'var(--color-success)', text: '#1E7A45' },
    error: { bg: 'var(--color-danger-bg)', border: 'var(--color-danger)', text: '#A83431' },
  };
  const c = colors[type] || colors.info;
  const root = ensureToastRoot();
  const el = document.createElement('div');
  el.textContent = message;
  el.style.cssText = `background:${c.bg};border:1.5px solid ${c.border};color:${c.text};padding:0.75rem 1.1rem;border-radius:12px;box-shadow:var(--shadow-md);font-size:0.875rem;font-weight:600;max-width:340px;animation:toast-in 200ms ease;`;
  root.appendChild(el);
  setTimeout(() => {
    el.style.transition = 'opacity 200ms ease';
    el.style.opacity = '0';
    setTimeout(() => el.remove(), 200);
  }, 4000);
}

const nutrimamaToastStyle = document.createElement('style');
nutrimamaToastStyle.textContent = '@keyframes toast-in { from { opacity:0; transform:translateX(20px); } to { opacity:1; transform:translateX(0); } }';
document.head.appendChild(nutrimamaToastStyle);

/**
 * Renders the "growing circle" — a 3-arc ring (one arc per trimester) showing
 * pregnancy week progress out of 40. Returns an SVG string.
 */
function renderGrowingCircle({ week = 0, size = 160, strokeWidth = 12 } = {}) {
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const totalWeeks = 40;
  const clampedWeek = Math.max(0, Math.min(totalWeeks, week));

  // Each trimester gets an equal arc segment of the circle; fill proportionally
  // to how far into (or past) that trimester the current week is.
  const segments = [13, 14, 13]; // weeks per trimester (T1, T2, T3)
  const colors = ['ring-t1', 'ring-t2', 'ring-t3'];
  let cursor = 0;
  let remainingWeeks = clampedWeek;
  const arcs = [];

  segments.forEach((segWeeks, i) => {
    const segFraction = segWeeks / totalWeeks;
    const segLength = circumference * segFraction;
    const filledWeeks = Math.max(0, Math.min(segWeeks, remainingWeeks));
    const filledLength = segLength * (filledWeeks / segWeeks);
    remainingWeeks -= segWeeks;

    arcs.push(`<circle class="${colors[i]}" cx="${size/2}" cy="${size/2}" r="${radius}"
      stroke-width="${strokeWidth}"
      stroke-dasharray="${filledLength} ${circumference}"
      stroke-dashoffset="${-cursor}" />`);
    cursor += segLength;
  });

  return `
    <div class="growing-circle" style="width:${size}px;height:${size}px;">
      <svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">
        <circle class="ring-bg" cx="${size/2}" cy="${size/2}" r="${radius}" stroke-width="${strokeWidth}" />
        ${arcs.join('')}
      </svg>
      <div class="ring-label">
        <span class="week-num">${clampedWeek}</span>
        <span class="week-sub">of 40 weeks</span>
      </div>
    </div>`;
}

function formatDate(dateStr) {
  if (!dateStr) return '—';
  const d = new Date(dateStr);
  if (isNaN(d)) return dateStr;
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
}

function trimesterLabel(t) {
  if (t === 1) return 'First Trimester';
  if (t === 2) return 'Second Trimester';
  if (t === 3) return 'Third Trimester';
  return 'Not set';
}

function skeletonBlock(height = '1rem', width = '100%') {
  return `<div class="skeleton" style="height:${height};width:${width};"></div>`;
}

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str ?? '';
  return div.innerHTML;
}
