'use strict';
const themeButton = document.querySelector('#theme');
let savedTheme;
try { savedTheme = localStorage.getItem('slothlab.site.theme'); } catch (_) { /* Optional browser storage. */ }
const systemTheme = window.matchMedia('(prefers-color-scheme: dark)');
function applyTheme(dark) {
  document.body.classList.toggle('dark', dark);
  themeButton.textContent = dark ? '☀ Light' : '☾ Dark';
  themeButton.setAttribute('aria-label', dark ? 'Switch to light theme' : 'Switch to dark theme');
}
applyTheme(savedTheme ? savedTheme === 'dark' : systemTheme.matches);
systemTheme.addEventListener('change', event => { if (!savedTheme) applyTheme(event.matches); });
themeButton.addEventListener('click', () => {
  const dark = !document.body.classList.contains('dark');
  applyTheme(dark); savedTheme = dark ? 'dark' : 'light';
  try { localStorage.setItem('slothlab.site.theme', savedTheme); } catch (_) { /* Theme still works in memory. */ }
});
const tabs = [...document.querySelectorAll('[role="tab"]')];
function activateTab(tab) {
  tabs.forEach(item => {
    const active = item === tab;
    item.setAttribute('aria-selected', String(active)); item.tabIndex = active ? 0 : -1;
    document.getElementById(item.dataset.panel).hidden = !active;
  });
}
tabs.forEach((tab, index) => {
  tab.addEventListener('click', () => activateTab(tab));
  tab.addEventListener('keydown', event => {
    let next;
    if (event.key === 'ArrowRight') next = (index + 1) % tabs.length;
    if (event.key === 'ArrowLeft') next = (index + tabs.length - 1) % tabs.length;
    if (event.key === 'Home') next = 0;
    if (event.key === 'End') next = tabs.length - 1;
    if (next !== undefined) { event.preventDefault(); tabs[next].focus(); activateTab(tabs[next]); }
  });
});
const phase = document.querySelector('#phase');
if (phase) {
  fetch('data/investigation.json').then(response => {
    if (!response.ok) throw new Error('Evidence file unavailable');
    return response.json();
  }).then(data => {
    function render() {
      const rows = data.rows.filter(row => phase.value === 'all' || row.phase === phase.value);
      const chart = document.querySelector('#chart'), table = document.querySelector('#rows');
      chart.replaceChildren(); table.replaceChildren();
      rows.forEach(row => {
        const line = document.createElement('div'); line.className = 'bar-row';
        const label = document.createElement('span'); label.textContent = `Seed ${row.seed}`;
        const track = document.createElement('div'); track.className = 'bar-track';
        const bar = document.createElement('span'); bar.className = 'bar';
        bar.style.width = `${Math.min(100, Math.abs(row.delta) / 0.016 * 100)}%`; track.append(bar);
        const value = document.createElement('strong'); value.textContent = row.delta.toFixed(5);
        line.append(label, track, value); chart.append(line);
        const tr = document.createElement('tr');
        [row.seed, row.phase, row.baseline.toFixed(5), row.corrected.toFixed(5), row.delta.toFixed(5)].forEach(value => {
          const td = document.createElement('td'); td.textContent = value; tr.append(td);
        }); table.append(tr);
      });
      document.querySelector('#load-status').textContent = `${rows.length} original measurements shown · recorded evidence`;
    }
    phase.addEventListener('change', render); render();
  }).catch(() => {
    document.querySelector('#load-status').textContent = 'The recorded evidence could not be loaded. Reload this page or follow the original evidence link above.';
  });
}
const plan = document.querySelector('#plan');
if (plan) plan.addEventListener('submit', event => {
  event.preventDefault();
  const seeds = Number(document.querySelector('#seeds').value), budget = Number(document.querySelector('#budget').value);
  const feedback = document.querySelector('#plan-feedback');
  if (seeds >= budget) { feedback.textContent = 'Leave room for exploration: the experiment budget must exceed the confirmation seed count.'; return; }
  const notes = {kind:'SlothLab design notes (not executable configuration)', question:document.querySelector('#question').value.trim(), competing_explanation:document.querySelector('#alternative').value.trim(), maximum_experiments:budget, reserved_confirmation_seeds:seeds};
  if (!notes.question || !notes.competing_explanation) { feedback.textContent = 'Write a question and a competing explanation first.'; return; }
  const url = URL.createObjectURL(new Blob([JSON.stringify(notes, null, 2)], {type:'application/json'}));
  const anchor = document.createElement('a'); anchor.href = url; anchor.download = 'slothlab-design-notes.json';
  document.body.append(anchor); anchor.click(); anchor.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  feedback.textContent = 'Design notes downloaded. Transfer the settings into New investigation in the local app.';
});
function loadVideo(start = 0) {
  const shell = document.querySelector('#video-player');
  const frame = document.createElement('iframe');
  frame.title = 'SlothLab live application walkthrough on YouTube';
  frame.src = `https://www.youtube-nocookie.com/embed/UV3h4IRk3go?start=${start}&autoplay=1&rel=0`;
  frame.allow = 'accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share';
  frame.allowFullscreen = true; frame.referrerPolicy = 'strict-origin-when-cross-origin';
  shell.replaceChildren(frame);
}
document.querySelector('#load-video')?.addEventListener('click', () => loadVideo());
document.querySelectorAll('[data-start]').forEach(button => button.addEventListener('click', () => {
  loadVideo(Number(button.dataset.start)); document.querySelector('#video-player').scrollIntoView({behavior:'smooth',block:'center'});
}));
