// CommonGround · workspace site core. Shared by every site design (mockup/site/<design>/):
// accounts, the SpacetimeDB connection (../live.mjs), hash routing, actions with friendly errors,
// formatting and the SVG city map. A design only renders `core.view()` and calls `core.act.*`.
//
//   import { createCore } from '../shared/core.js';
//   const core = createCore({ onRender: (core) => render(core), onToast: (msg, kind) => ... });
//
// Routes (hash): #/ home · #/w/<id> workspace · #/w/<id>/people · #/w/<id>/p/<planId> plan · #/join/<code>
import { connectLive } from '../live.mjs';

// ───────────────────────── accounts ─────────────────────────
// Several people can use one browser (handy for demos): each account is its own SpacetimeDB identity.
// ?acct=<slot> picks one for this tab; otherwise the last one used.
const ACCTS_KEY = 'hp-accounts', ACTIVE_KEY = 'hp-acct';
const ls = {
  get: (k) => { try { return localStorage.getItem(k); } catch (_) { return null; } },
  set: (k, v) => { try { v == null ? localStorage.removeItem(k) : localStorage.setItem(k, v); } catch (_) { /* blocked */ } },
};
const ss = {
  get: (k) => { try { return sessionStorage.getItem(k); } catch (_) { return null; } },
  set: (k, v) => { try { sessionStorage.setItem(k, v); } catch (_) { /* blocked */ } },
};
export const PALETTE = ['#3b82f6', '#f97316', '#10b981', '#a855f7', '#ef4444', '#eab308', '#14b8a6', '#ec4899'];
export const tokenKey = (slot) => (slot === 'main' ? 'commonground-token' : `commonground-token:${slot}`);
function loadAccounts() {
  try { const a = JSON.parse(ls.get(ACCTS_KEY) || '[]'); if (Array.isArray(a)) return a; } catch (_) { /* corrupt */ }
  return [];
}
function saveAccounts(a) { ls.set(ACCTS_KEY, JSON.stringify(a)); }
function activeSlot() {
  const q = new URLSearchParams(location.search).get('acct');
  const s = q || ss.get(ACTIVE_KEY) || ls.get(ACTIVE_KEY) || 'main';
  ss.set(ACTIVE_KEY, s); ls.set(ACTIVE_KEY, s);
  return s;
}

// ───────────────────────── formatting ─────────────────────────
export const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
export function money(v, { sign = true, unit = '/yr' } = {}) {
  if (v == null || !isFinite(v)) return '—';
  const a = Math.abs(v), s = v < 0 ? '−' : sign && v > 0 ? '+' : '';
  const n = a >= 1e9 ? `${(a / 1e9).toFixed(1)}B` : a >= 1e6 ? `${(a / 1e6).toFixed(a >= 1e7 ? 1 : 2)}M` : a >= 1e3 ? `${Math.round(a / 1e3)}k` : `${Math.round(a)}`;
  return `${s}$${n}${unit}`;
}
export function num(v, { sign = true } = {}) {
  if (v == null || !isFinite(v)) return '—';
  const a = Math.abs(v), s = v < 0 ? '−' : sign && v > 0 ? '+' : '';
  return s + (a >= 1e6 ? `${(a / 1e6).toFixed(1)}M` : a >= 1e4 ? `${Math.round(a / 1e3)}k` : Math.round(a).toLocaleString('en-US'));
}
export function ago(d) {
  if (!d) return '';
  const s = Math.max(0, (Date.now() - d.getTime()) / 1000);
  if (s < 45) return 'just now';
  if (s < 3600) return `${Math.round(s / 60)}m ago`;
  if (s < 86400) return `${Math.round(s / 3600)}h ago`;
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}
export const initials = (n) => String(n || '?').trim().split(/\s+/).slice(0, 2).map((w) => w[0]).join('').toUpperCase() || '?';
export const STAGES = [
  { key: 'draft', label: 'Draft', hint: 'Being sketched' },
  { key: 'review', label: 'In review', hint: 'Ready for the team to look at' },
  { key: 'approved', label: 'Approved', hint: 'The team backs it' },
  { key: 'archived', label: 'Archived', hint: 'Parked' },
];
export const ROLES = [
  { key: 'admin', label: 'Admin', hint: 'Manages people, invites and the workspace' },
  { key: 'editor', label: 'Editor', hint: 'Edits plans in the simulator' },
  { key: 'viewer', label: 'Viewer', hint: 'Watches plans live, can’t edit' },
];
export const stageLabel = (k) => STAGES.find((s) => s.key === k)?.label ?? k;
export const roleLabel = (k) => ROLES.find((r) => r.key === k)?.label ?? k;
// What the engine is doing with a plan, in words.
export function planStatus(p) {
  if (!p) return { key: 'none', label: '' };
  if (p.status === 'error') return { key: 'error', label: 'Engine error', detail: p.error };
  if (p.status === 'computing') return { key: 'busy', label: 'Simulating…' };
  if (p.status === 'pending') return { key: 'busy', label: p.resultVersion ? 'Re-simulating…' : 'Queued' };
  return { key: 'ready', label: 'Simulated' };
}
// A plan's city value for display: '—' before the first result, 'Same as today' with no edits.
export function valueLabel(p) {
  if (!p || !p.value || !p.resultVersion) return '—';
  if (!p.streets && !p.blocks) return 'Same as today';
  return money(p.value.total);
}
export function editsSummary(p) {
  const parts = [];
  if (p.streets) parts.push(`${p.streets} car-free segment${p.streets === 1 ? '' : 's'}`);
  if (p.blocks) parts.push(`${p.blocks} building edit${p.blocks === 1 ? '' : 's'}`);
  return parts.join(' · ') || 'No edits yet (same as today)';
}

// Replace el's HTML, but keep whatever the person is typing: live updates re-render the page often.
// Inputs keep their value and caret when they have an id.
export function paint(el, html) {
  if (!el || el.__html === html) return;
  const a = document.activeElement;
  const keep = a && el.contains(a) && a.id ? { id: a.id, v: a.value, s: a.selectionStart, e: a.selectionEnd } : null;
  const vals = [...el.querySelectorAll('input[id],textarea[id]')].filter((i) => i.type !== 'checkbox' && i.type !== 'radio').map((i) => [i.id, i.value]);
  el.innerHTML = html; el.__html = html;
  for (const [id, v] of vals) { const i = el.querySelector(`#${CSS.escape(id)}`); if (i && !i.hasAttribute('data-fresh')) i.value = v; }
  if (keep) { const i = el.querySelector(`#${CSS.escape(keep.id)}`); if (i) { i.focus(); try { i.value = keep.v; i.setSelectionRange(keep.s, keep.e); } catch (_) { /* not a text input */ } } }
  else el.querySelector('[data-autofocus]')?.focus();
}

// ───────────────────────── city map (SVG) ─────────────────────────
let CITY = null, cityLoading = null;
export function loadCity() {
  if (CITY) return Promise.resolve(CITY);
  if (!cityLoading) cityLoading = fetch(new URL('./city.json', import.meta.url)).then((r) => r.json()).then((c) => (CITY = c)).catch(() => null);
  return cityLoading;
}
const MAJOR = /motorway|trunk|primary|secondary/;
const pathOf = (pts) => 'M' + pts.map((p) => p.join(' ')).join('L');
const layerCache = new Map();
function layers(c) {
  if (layerCache.has(c)) return layerCache.get(c);
  const major = [], minor = [], bld = [], tall = [];
  c.edges.forEach(([cls, , p]) => (MAJOR.test(cls) ? major : minor).push(pathOf(p)));
  c.buildings.forEach(([h, , p]) => (h > 60 ? tall : bld).push(pathOf(p) + 'Z'));
  const l = { major: major.join(''), minor: minor.join(''), bld: bld.join(''), tall: tall.join('') };
  layerCache.set(c, l);
  return l;
}
// cityMap({ streets: Set|array of car-free edge ids, colors: { bg, minor, major, bld, tall, edit }, buildings, crop })
// crop: 'fit' (whole area) or 'edits' (zoom to the edited streets).
export function cityMap(opts = {}) {
  const c = CITY;
  const col = { bg: 'transparent', minor: '#cbd5e1', major: '#94a3b8', bld: '#e2e8f0', tall: '#cbd5e1', edit: '#22c55e', ...(opts.colors || {}) };
  if (!c) return `<svg class="hp-map" viewBox="0 0 100 60" preserveAspectRatio="xMidYMid slice"><rect width="100" height="60" fill="${col.bg}"/></svg>`;
  const L = layers(c);
  const ids = [...(opts.streets || [])].filter((i) => c.edges[i]);
  let [x0, z0, x1, z1] = c.view || c.bbox;
  if (opts.crop === 'edits' && ids.length) {
    const xs = [], zs = [];
    for (const i of ids) for (const [x, z] of c.edges[i][2]) { xs.push(x); zs.push(z); }
    const pad = 420, cx = (Math.min(...xs) + Math.max(...xs)) / 2, cz = (Math.min(...zs) + Math.max(...zs)) / 2;
    const w = Math.max(Math.max(...xs) - Math.min(...xs) + pad * 2, 1400), h = Math.max(Math.max(...zs) - Math.min(...zs) + pad * 2, 900);
    x0 = cx - w / 2; x1 = cx + w / 2; z0 = cz - h / 2; z1 = cz + h / 2;
  }
  const w = x1 - x0, h = z1 - z0, sw = Math.max(w, h) / (opts.thin ? 900 : 600);
  const edit = ids.map((i) => pathOf(c.edges[i][2])).join('');
  return `<svg class="hp-map" viewBox="${x0} ${z0} ${w} ${h}" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
    <rect x="${x0}" y="${z0}" width="${w}" height="${h}" fill="${col.bg}"/>
    ${opts.buildings !== false ? `<path d="${L.bld}" fill="${col.bld}"/><path d="${L.tall}" fill="${col.tall}"/>` : ''}
    <path d="${L.minor}" fill="none" stroke="${col.minor}" stroke-width="${sw * 1.6}" stroke-linecap="round" stroke-linejoin="round"/>
    <path d="${L.major}" fill="none" stroke="${col.major}" stroke-width="${sw * 2.6}" stroke-linecap="round" stroke-linejoin="round"/>
    ${edit ? `<path d="${edit}" fill="none" stroke="${col.edit}" stroke-width="${sw * 7}" stroke-linecap="round" stroke-linejoin="round" opacity=".28"/><path d="${edit}" fill="none" stroke="${col.edit}" stroke-width="${sw * 3}" stroke-linecap="round" stroke-linejoin="round"/>` : ''}
  </svg>`;
}
export const heroStreets = () => CITY?.hero ?? [];

// ───────────────────────── core ─────────────────────────
export function createCore({ onRender = () => {}, onToast = () => {} } = {}) {
  const slot = activeSlot();
  const accounts = loadAccounts();
  if (!accounts.find((a) => a.slot === slot)) { accounts.push({ slot, name: '', color: PALETTE[accounts.length % PALETTE.length] }); saveAccounts(accounts); }
  const account = () => loadAccounts().find((a) => a.slot === slot) || { slot, name: '', color: PALETTE[0] };

  const params = new URLSearchParams(location.search);
  const engine = (params.get('api') || `${location.protocol === 'https:' ? 'https' : 'http'}://${location.hostname || 'localhost'}:8787`).replace(/\/$/, '');
  const simBase = new URL('../../cities/sf/index.html', import.meta.url);

  let st = { connected: false, ready: false, me: null, workspaces: [], engine: 'probing' };
  let live = null, liveError = '', offline = false;
  let route = parseRoute();
  let pendingNav = null; // { kind, before, until } — open a workspace/plan once it shows up
  const ui = {}; // free-form per-design UI state (open modals, tabs); persists across renders

  let rafQueued = false;
  const render = () => { if (rafQueued) return; rafQueued = true; requestAnimationFrame(() => { rafQueued = false; try { onRender(core); } catch (e) { console.error(e); } }); };
  const toast = (msg, kind = 'info') => { try { onToast(msg, kind); } catch (_) { /* design without toasts */ } };

  function parseRoute() {
    const h = (location.hash || '#/').replace(/^#/, '');
    const seg = h.split('/').filter(Boolean);
    if (seg[0] === 'join' && seg[1]) return { name: 'join', code: decodeURIComponent(seg[1]) };
    if (seg[0] === 'w' && seg[1]) {
      if (seg[2] === 'p' && seg[3]) return { name: 'plan', wsId: seg[1], planId: +seg[3] };
      if (seg[2] === 'people') return { name: 'people', wsId: seg[1] };
      if (seg[2] === 'settings') return { name: 'settings', wsId: seg[1] };
      return { name: 'workspace', wsId: seg[1] };
    }
    if (seg[0] === 'workspaces') return { name: 'workspaces' };
    return { name: 'home' };
  }
  function go(hash) { if (location.hash !== hash) location.hash = hash; else { route = parseRoute(); afterRoute(); } }
  window.addEventListener('hashchange', () => { route = parseRoute(); afterRoute(); });
  function afterRoute() {
    if (live && st.ready) live.setPresence(route.wsId || 0, 0).catch(() => {});
    if (route.name === 'join') tryJoin();
    window.scrollTo?.(0, 0);
    render();
  }

  // ── connection ──
  function connect() {
    try {
      live = connectLive({
        tokenKey: tokenKey(slot),
        engine,
        name: account().name || undefined,
        color: account().name ? account().color : undefined,
        onChange: (s, table) => {
          const first = !st.ready && s.ready;
          const dropped = st.connected && !s.connected;
          st = s;
          if (first) { offline = false; retries = 0; live.setPresence(route.wsId || 0, 0).catch(() => {}); if (route.name === 'join') tryJoin(); }
          if (dropped) reconnect();
          checkPendingNav();
          render();
        },
        onError: (e) => { const m = String(e?.message ?? e); if (/connect|websocket|network/i.test(m) && !st.connected) { offline = true; liveError = m; render(); reconnect(); } },
      });
    } catch (e) { offline = true; liveError = String(e?.message ?? e); }
    setTimeout(() => { if (!st.connected) { offline = true; render(); reconnect(); } }, 4000);
  }
  // The live server restarted or the network blipped: try again with backoff, keeping the page as it is.
  let retries = 0, retryTimer = null;
  function reconnect() {
    if (retryTimer) return;
    retryTimer = setTimeout(() => {
      retryTimer = null; retries++;
      try { live?.disconnect(); } catch (_) { /* already closed */ }
      st = { ...st, connected: false, ready: false, stale: st.ready }; // keep showing the last data meanwhile
      connect();
    }, Math.min(10000, 1000 * 2 ** Math.min(retries, 3)));
  }

  function checkPendingNav() {
    const p = pendingNav;
    if (!p) return;
    if (Date.now() > p.until) { pendingNav = null; return; }
    if (p.kind === 'workspace') {
      const w = st.workspaces.find((x) => !p.before.has(x.id));
      if (w) { pendingNav = null; go(`#/w/${w.id}`); if (p.msg) toast(p.msg(w), 'good'); }
    } else if (p.kind === 'plan') {
      const w = st.workspaces.find((x) => x.id === p.wsId);
      const pl = w?.plans.find((x) => !p.before.has(x.id));
      if (pl) { pendingNav = null; if (p.open) go(`#/w/${w.id}/p/${pl.id}`); toast(`Created ${pl.name}`, 'good'); }
    }
  }

  // Run a reducer; show its error as a toast. Returns true on success.
  async function run(fn, okMsg) {
    if (!live || !st.ready) { toast(st.stale ? 'Reconnecting to the live server… try again in a moment.' : 'Not connected to the live server yet.', 'bad'); return false; }
    try { await fn(); if (okMsg) toast(okMsg, 'good'); return true; } catch (e) {
      const m = String(e?.message ?? e).replace(/^.*SenderError:?\s*/i, '');
      toast(m || 'That didn’t work.', 'bad'); return false;
    }
  }

  let joining = '';
  async function tryJoin() {
    const code = route.code;
    if (!code || !st.ready || joining === code) return;
    if (!account().name) { ui.needName = true; render(); return; } // the design asks for a name, then calls act.join
    joining = code;
    const before = new Set(st.workspaces.map((w) => w.id));
    pendingNav = { kind: 'workspace', before, until: Date.now() + 6000, msg: (w) => `You joined ${w.name}` };
    const ok = await run(() => live.join(code));
    if (!ok) { pendingNav = null; go('#/'); }
    else setTimeout(() => { if (pendingNav && route.name === 'join') { pendingNav = null; toast('You’re already in that workspace.'); go('#/'); } }, 2500);
    joining = '';
  }

  // ── actions ──
  const act = {
    setProfile: async (name, color) => {
      const clean = String(name || '').trim().slice(0, 24);
      if (!clean) { toast('Pick a name first.', 'bad'); return false; }
      const all = loadAccounts(); const a = all.find((x) => x.slot === slot);
      if (a) { a.name = clean; a.color = color || a.color; saveAccounts(all); }
      ui.needName = false;
      if (live && st.ready) { await run(() => live.setName(clean)); if (color) await run(() => live.setColor(color)); }
      if (route.name === 'join') tryJoin();
      render();
      return true;
    },
    // Demo helper: a second person in this browser. Opens a new tab signed in as them.
    newAccount: (name = '') => {
      const all = loadAccounts(); const n = all.length + 1;
      const s = `p${Date.now().toString(36)}`;
      all.push({ slot: s, name, color: PALETTE[(n - 1) % PALETTE.length] }); saveAccounts(all);
      return switchUrl(s);
    },
    switchAccount: (s) => switchUrl(s),
    createWorkspace: async (name, description) => {
      const before = new Set(st.workspaces.map((w) => w.id));
      pendingNav = { kind: 'workspace', before, until: Date.now() + 6000, msg: (w) => `Created ${w.name}` };
      const ok = await run(() => live.createWorkspace(name, description));
      if (!ok) pendingNav = null;
      return ok;
    },
    updateWorkspace: (wsId, name, description) => run(() => live.updateWorkspace(wsId, name, description), 'Saved'),
    deleteWorkspace: async (wsId) => { const ok = await run(() => live.deleteWorkspace(wsId), 'Workspace deleted'); if (ok) go('#/'); return ok; },
    createInvite: (wsId, role) => run(() => live.createInvite(wsId, role), `New ${roleLabel(role).toLowerCase()} link created`),
    revokeInvite: (code) => run(() => live.revokeInvite(code), 'Link revoked'),
    join: (code) => { route = { name: 'join', code }; tryJoin(); },
    setRole: (wsId, memberId, role) => run(() => live.setRole(wsId, memberId, role), 'Role updated'),
    removeMember: (wsId, memberId) => run(() => live.removeMember(wsId, memberId), 'Removed'),
    leave: async (wsId) => { const ok = await run(() => live.leave(wsId), 'You left the workspace'); if (ok) go('#/'); return ok; },
    createPlan: async (wsId, name, description = '', copyFrom = 0, open = true) => {
      const w = st.workspaces.find((x) => x.id === wsId);
      pendingNav = { kind: 'plan', wsId, before: new Set((w?.plans || []).map((p) => p.id)), until: Date.now() + 6000, open };
      const ok = await run(() => live.createPlan(wsId, name, description, copyFrom));
      if (!ok) pendingNav = null;
      return ok;
    },
    updatePlan: (planId, name, description) => run(() => live.updatePlan(planId, name, description), 'Saved'),
    setStage: (planId, stage) => run(() => live.setStage(planId, stage)),
    deletePlan: async (planId) => { const wsId = route.wsId; const ok = await run(() => live.deletePlan(planId), 'Plan deleted'); if (ok && route.name === 'plan') go(`#/w/${wsId}`); return ok; },
    resetPlan: (planId) => run(() => live.reset(planId), 'Plan reset to today'),
    recompute: (planId) => run(() => live.recompute(planId), 'Re-simulating'),
    // A one-click demo edit: make 2nd Street car-free in this plan.
    tryHeroEdit: (planId) => run(() => live.setPedestrian(planId, heroStreets(), true), 'Made 2nd Street car-free'),
    copy: async (text, msg = 'Copied') => {
      try { await navigator.clipboard.writeText(text); toast(msg, 'good'); } catch (_) { window.prompt('Copy this link', text); }
    },
  };
  function switchUrl(s) {
    const u = new URL(location.href); u.searchParams.set('acct', s);
    return u.href;
  }

  // ── derived view for designs ──
  function view() {
    const ws = route.wsId ? st.workspaces.find((w) => w.id === route.wsId) || null : null;
    const plan = ws && route.planId ? ws.plans.find((p) => p.id === route.planId) || null : null;
    const ps = plan && live ? live.planState(plan.id) : null;
    const can = {
      edit: !!ws && ws.myRole !== 'viewer',
      admin: !!ws && ws.myRole === 'admin',
    };
    return {
      route, st, ws, plan, ps, can, ui,
      me: st.me, account: account(), accounts: loadAccounts(), slot,
      connecting: !st.ready && !st.stale && !offline, offline: offline && !st.ready && !st.stale, liveError,
      reconnecting: !!st.stale && !st.ready,
      engine: st.engine,
      needName: (!!ui.needName || (st.ready && !account().name)),
    };
  }

  const core = {
    view, act, go, render, toast, ui,
    inviteUrl: (code) => `${location.origin}${location.pathname}#/join/${code}`,
    // The 3D simulator is Maximilian Thiersch's (mockup/cities/); the site only links to it.
    simUrl: () => {
      const u = new URL(simBase);
      if (params.get('api')) u.searchParams.set('api', params.get('api'));
      return u.href;
    },
    planState: (id) => (live ? live.planState(id) : null),
    live: () => live,
  };
  loadCity().then(render);
  connect();
  setInterval(render, 30000); // keep "5m ago" labels fresh
  render();
  return core;
}
