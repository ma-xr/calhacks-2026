// CommonGround · Live multiplayer (SpacetimeDB on :3000, client backend/live/client/dist/live.mjs).
// Classic script, no imports. Defines window.HPLive = { mount(host, opts) }.
// The ES-module client is loaded lazily with import(opts.liveUrl || './live.mjs'), resolved against the page URL.
//
// Host API (docs/fully-functional-spec.md §2) plus these live-only callbacks:
//   host.showCursors([{ id, name, color, x, z }])   other players' cursors in world metres ([] clears them)
//   host.loadLivePlan({ planId, edits, result })    optional: the shared plan settled; load GET /scenario/{planId}.
//                                                   Without it the module calls host.applyEdits(edits, 'Live plan').
//   host.onLiveChange(on: boolean)                  optional: route local edits through the handle while on
//   host.onLiveAvailable(ok: boolean)               optional: :3000 reachable or not (hide your own button if false)
// Handle methods for the host: setPedestrian(ids, on), setBlock(ids, scale, zone), reset(), cursor(x, z), setName(n).
// Each returns false when not live, so the host can run its local path instead.
(() => {
  if (window.HPLive) return;

  // ── shared look (identical block in hp-ask / hp-policy / hp-live; injected once) ──
  const BASE_CSS = `
.hpx{--hpx-glass:rgba(16,32,60,.84);--hpx-glass-strong:rgba(14,28,54,.94);--hpx-line:rgba(255,255,255,.08);--hpx-line-hi:rgba(255,255,255,.16);
--hpx-fill:rgba(255,255,255,.055);--hpx-fill-hi:rgba(255,255,255,.10);--hpx-sunk:rgba(4,12,28,.28);--hpx-hi:#7fd3ff;--hpx-accent:#3b9cff;
--hpx-fg:#f3f7fc;--hpx-dim:#a9bad1;--hpx-mute:#7b8fab;--hpx-good:#4fdc7a;--hpx-bad:#ff5d5d;--hpx-warn:#ffd23a;--hpx-edit:#b46cff;--hpx-social:#ff4fa3;
--hpx-r-xs:6px;--hpx-r-sm:8px;--hpx-r-md:12px;--hpx-r-lg:16px;--hpx-sh:0 10px 30px rgba(9,24,50,.26),0 1px 3px rgba(9,24,50,.18);
font-family:"Inter","SF Pro Text",system-ui,-apple-system,"Segoe UI",sans-serif;font-size:13px;line-height:1.4;color:var(--hpx-fg);
font-variant-numeric:tabular-nums;-webkit-font-smoothing:antialiased;letter-spacing:-.005em;box-sizing:border-box}
.hpx *,.hpx *::before,.hpx *::after{box-sizing:border-box}
.hpx [hidden]{display:none!important}
.hpx :where(button){font:inherit;color:inherit;background:none;border:0;cursor:pointer;padding:0;letter-spacing:inherit}
.hpx :where(button):disabled{opacity:.45;cursor:default}
.hpx button:focus-visible,.hpx input:focus-visible,.hpx textarea:focus-visible,.hpx select:focus-visible{outline:2px solid var(--hpx-hi);outline-offset:2px}
.hpx-panel{position:absolute;z-index:6;display:flex;flex-direction:column;background:var(--hpx-glass);border-radius:var(--hpx-r-lg);box-shadow:var(--hpx-sh);
backdrop-filter:blur(18px) saturate(1.4);-webkit-backdrop-filter:blur(18px) saturate(1.4);overflow:hidden;pointer-events:auto;
transition:opacity .18s,transform .18s}
.hpx-panel.hpx-closed{opacity:0;transform:translateY(8px);pointer-events:none;visibility:hidden}
.hpx-head{display:flex;align-items:center;gap:8px;padding:12px 12px 10px 14px;border-bottom:1px solid var(--hpx-line);flex:none}
.hpx-head h3{margin:0;font-size:14px;font-weight:700;letter-spacing:-.01em;flex:1;display:flex;align-items:center;gap:8px;min-width:0}
.hpx-tag{font-size:10px;font-weight:700;letter-spacing:.04em;text-transform:uppercase;color:var(--hpx-hi);background:rgba(127,211,255,.12);padding:2px 6px;border-radius:var(--hpx-r-xs)}
.hpx-x{width:28px;height:28px;border-radius:var(--hpx-r-sm);display:grid;place-items:center;color:var(--hpx-dim)}
.hpx-x:hover{background:var(--hpx-fill-hi);color:#fff}
.hpx-x svg{width:16px;height:16px;fill:none;stroke:currentColor;stroke-width:2;stroke-linecap:round}
.hpx-body{flex:1;overflow:auto;padding:12px 14px;min-height:0}
.hpx-body::-webkit-scrollbar{width:8px}.hpx-body::-webkit-scrollbar-thumb{background:rgba(255,255,255,.12);border-radius:8px}
.hpx-btn{display:inline-flex;align-items:center;justify-content:center;gap:6px;height:30px;padding:0 12px;border-radius:var(--hpx-r-sm);font-weight:600;font-size:12.5px;background:var(--hpx-fill);white-space:nowrap;transition:background .15s}
.hpx-btn:hover:not(:disabled){background:var(--hpx-fill-hi)}
.hpx-btn.hpx-primary{background:var(--hpx-accent);color:#fff;box-shadow:0 2px 10px rgba(59,156,255,.35)}
.hpx-btn.hpx-primary:hover:not(:disabled){background:#4ea8ff}
.hpx-btn.hpx-good{background:rgba(79,220,122,.18);color:#8ff0ae}.hpx-btn.hpx-good:hover:not(:disabled){background:rgba(79,220,122,.28)}
.hpx-btn.hpx-bad{background:rgba(255,93,93,.14);color:#ffb0b0}.hpx-btn.hpx-bad:hover:not(:disabled){background:rgba(255,93,93,.24)}
.hpx-btn.hpx-sm{height:26px;padding:0 9px;font-size:11.5px}
.hpx-field{width:100%;background:var(--hpx-sunk);border:1px solid var(--hpx-line);border-radius:var(--hpx-r-sm);color:var(--hpx-fg);font:inherit;padding:7px 10px;outline:none}
.hpx-field::placeholder{color:var(--hpx-mute)}
.hpx-field:focus{border-color:rgba(127,211,255,.4)}
select.hpx-field{appearance:none;-webkit-appearance:none;padding-right:26px;background-image:linear-gradient(45deg,transparent 50%,#a9bad1 50%),linear-gradient(135deg,#a9bad1 50%,transparent 50%);
background-position:calc(100% - 14px) 50%,calc(100% - 9px) 50%;background-size:5px 5px;background-repeat:no-repeat}
select.hpx-field option{background:#13233f;color:#f3f7fc}
.hpx input[type=range]{width:100%;accent-color:var(--hpx-accent)}
.hpx-muted{color:var(--hpx-mute)}.hpx-dim{color:var(--hpx-dim)}
.hpx-up{color:#7deda0}.hpx-down{color:#ff9a9a}
.hpx-card{background:var(--hpx-fill);border-radius:var(--hpx-r-md);padding:11px 12px}
.hpx-card+.hpx-card{margin-top:8px}
.hpx-eyebrow{font-size:10.5px;font-weight:600;text-transform:uppercase;letter-spacing:.06em;color:var(--hpx-mute);margin:0 0 6px}
.hpx-offline{display:flex;flex-direction:column;align-items:flex-start;gap:8px;padding:14px;border-radius:var(--hpx-r-md);background:var(--hpx-fill);border:1px dashed var(--hpx-line-hi)}
.hpx-offline b{font-size:13px}.hpx-offline p{margin:0;color:var(--hpx-dim);font-size:12px}
.hpx-offline code{font-size:11px;background:var(--hpx-sunk);padding:1px 5px;border-radius:4px;color:var(--hpx-hi)}
.hpx-spin{width:12px;height:12px;border-radius:50%;border:2px solid rgba(127,211,255,.25);border-top-color:var(--hpx-hi);animation:hpx-spin .8s linear infinite;flex:none;display:inline-block}
@keyframes hpx-spin{to{transform:rotate(360deg)}}
.hpx-pill{display:inline-flex;align-items:center;gap:5px;height:20px;padding:0 8px;border-radius:999px;font-size:11px;font-weight:600;background:var(--hpx-fill-hi);color:var(--hpx-dim)}
.hpx-pre{margin:6px 0 0;padding:8px 10px;background:var(--hpx-sunk);border-radius:var(--hpx-r-sm);font:11px/1.45 ui-monospace,SFMono-Regular,Menlo,monospace;color:#c9d8ec;white-space:pre-wrap;word-break:break-word;max-height:220px;overflow:auto}
@media (max-width:600px){.hpx-panel{left:8px!important;right:8px!important;width:auto!important;max-width:none!important}}
`;
  function ensureCss(id, css) {
    try {
      if (document.getElementById(id)) return;
      const s = document.createElement('style'); s.id = id; s.textContent = css; document.head.appendChild(s);
    } catch (_) { /* no DOM */ }
  }
  const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const X_ICON = '<svg viewBox="0 0 24 24"><path d="M6 6l12 12M18 6L6 18"/></svg>';

  const CSS = `
.hpx-live-pill{position:absolute;z-index:6;right:12px;bottom:72px;display:inline-flex;align-items:center;gap:8px;height:36px;padding:0 13px 0 11px;border-radius:12px;
background:var(--hpx-glass);box-shadow:var(--hpx-sh);backdrop-filter:blur(18px) saturate(1.4);-webkit-backdrop-filter:blur(18px) saturate(1.4);font-weight:600;font-size:12.5px;pointer-events:auto}
.hpx-live-pill:hover{background:var(--hpx-glass-strong)}
.hpx-live-pill .hpx-dot{width:8px;height:8px;border-radius:50%;background:var(--hpx-mute);flex:none}
.hpx-live-pill.hpx-on .hpx-dot{background:#ff4f6d;box-shadow:0 0 0 0 rgba(255,79,109,.6);animation:hpx-pulse 1.6s infinite}
.hpx-live-pill.hpx-on{color:#fff}
.hpx-live-pill .hpx-n{color:var(--hpx-dim);font-weight:500}
@keyframes hpx-pulse{0%{box-shadow:0 0 0 0 rgba(255,79,109,.55)}70%{box-shadow:0 0 0 7px rgba(255,79,109,0)}100%{box-shadow:0 0 0 0 rgba(255,79,109,0)}}
.hpx-live{right:12px;bottom:116px;width:310px;max-height:min(520px,calc(100vh - 200px))}
.hpx-live .hpx-status{display:flex;align-items:center;gap:8px;padding:9px 11px;border-radius:var(--hpx-r-sm);background:var(--hpx-sunk);font-size:12px}
.hpx-live .hpx-status b{font-weight:600}
.hpx-live .hpx-status .hpx-v{margin-left:auto;font-weight:700}
.hpx-live .hpx-sw{display:flex;align-items:center;gap:10px}
.hpx-live .hpx-sw .hpx-field{flex:1}
.hpx-live .hpx-players{display:flex;flex-direction:column;gap:4px}
.hpx-live .hpx-pl{display:flex;align-items:center;gap:8px;font-size:12px}
.hpx-live .hpx-pl i{width:10px;height:10px;border-radius:50%;flex:none}
.hpx-live .hpx-pl.hpx-off{opacity:.45}
.hpx-live .hpx-pl .hpx-me{font-size:10px;color:var(--hpx-mute);margin-left:auto}
.hpx-live .hpx-feed{display:flex;flex-direction:column;gap:5px;font-size:11.5px}
.hpx-live .hpx-feed div{display:flex;gap:6px;align-items:baseline}
.hpx-live .hpx-feed b{font-weight:600;flex:none}
.hpx-live .hpx-feed span{color:var(--hpx-dim);min-width:0}
.hpx-live .hpx-feed time{margin-left:auto;color:var(--hpx-mute);font-size:10px;flex:none;padding-left:6px}
.hpx-live .hpx-sec{margin-top:12px}
.hpx-live .hpx-acts{display:flex;gap:6px;margin-top:12px}
.hpx-live .hpx-acts .hpx-btn{flex:1}
`;

  // Per-tab identity: live.mjs keeps one token in localStorage, so every tab of a browser would be the same player.
  // We park each tab's token in sessionStorage (survives reloads of that tab) and swap it in before connecting.
  const LS_KEY = 'human-live-token', SS_KEY = 'hpx-live-token';
  const ls = { get: (k) => { try { return localStorage.getItem(k); } catch (_) { return null; } }, set: (k, v) => { try { v == null ? localStorage.removeItem(k) : localStorage.setItem(k, v); } catch (_) { /* blocked */ } } };
  const ss = { get: (k) => { try { return sessionStorage.getItem(k); } catch (_) { return null; } }, set: (k, v) => { try { sessionStorage.setItem(k, v); } catch (_) { /* blocked */ } } };

  function mount(host, opts = {}) {
    host = host || {};
    const safe = (name, ...a) => { try { const f = host[name]; return typeof f === 'function' ? f.apply(host, a) : undefined; } catch (e) { console.warn(`[HPLive] host.${name} failed`, e); } };
    ensureCss('hpx-base-css', BASE_CSS); ensureCss('hpx-live-css', CSS);
    const hostname = (() => { try { return location.hostname || 'localhost'; } catch (_) { return 'localhost'; } })();
    const httpBase = opts.httpUrl || `http://${hostname}:3000`;
    const db = opts.db || 'human-live';
    const liveUrl = (() => { try { return new URL(opts.liveUrl || './live.mjs', document.baseURI).href; } catch (_) { return opts.liveUrl || './live.mjs'; } })();
    const perTab = opts.perTabIdentity !== false;
    const mountNode = host.mount || document.body;

    const wrap = document.createElement('div'); wrap.className = 'hpx'; wrap.style.cssText = 'position:absolute;inset:0;pointer-events:none;z-index:6';
    wrap.innerHTML = `
      <button class="hpx-live-pill" type="button" hidden aria-pressed="false"><span class="hpx-dot"></span><span class="hpx-lbl">Go live</span><span class="hpx-n"></span></button>
      <section class="hpx-panel hpx-live hpx-closed" aria-label="Live session">
        <div class="hpx-head"><h3>Live plan <span class="hpx-tag">Shared</span></h3><button class="hpx-x" data-act="close" aria-label="Close"><svg viewBox="0 0 24 24"><path d="M6 6l12 12M18 6L6 18"/></svg></button></div>
        <div class="hpx-body"></div></section>`;
    if (opts.pill === false) wrap.querySelector('.hpx-live-pill').remove();
    mountNode.appendChild(wrap);
    const pill = wrap.querySelector('.hpx-live-pill'), panel = wrap.querySelector('.hpx-live'), bodyEl = panel.querySelector('.hpx-body');

    let available = false, on = false, connecting = false, live = null, st = null, lastPlan = null, lastErr = null, destroyed = false, lastEditsKey = '';
    const myName = () => ls.get('planner-name') || '';

    // ── reachability ──
    const ready = (async () => {
      if (opts.forceUnavailable) return false;
      try {
        if (location.protocol === 'https:' && !opts.httpUrl) return false;   // mixed content: a published artifact can't reach :3000
        const ctl = new AbortController(); const t = setTimeout(() => ctl.abort(), opts.probeMs || 1500);
        const r = await fetch(`${httpBase}/v1/database/${encodeURIComponent(db)}`, { signal: ctl.signal, cache: 'no-store' });
        clearTimeout(t);
        return r.ok;
      } catch (_) { return false; }
    })().then((ok) => {
      available = ok && !destroyed;
      if (pill) pill.hidden = !available;
      safe('onLiveAvailable', available);
      render();
      if (available && opts.autoConnect) start();
      return available;
    });

    // ── state -> host ──
    const editsOf = (s) => {
      const blocks = {};
      for (const [bid, b] of s.blocks || []) blocks[String(bid)] = { scale: +b.scale, ...(b.zone ? { zone: b.zone } : {}) };
      return { pedestrianized: [...(s.streets || [])].map(Number).sort((a, b) => a - b), blocks, policies: [], reopened: [] };
    };
    function onChange(s, table) {
      if (destroyed || !on) return;
      st = s;
      if (table === '*' && perTab) { const t = ls.get(LS_KEY); if (t) ss.set(SS_KEY, t); }
      if (table === 'player' || table === '*') {
        safe('showCursors', (s.players || []).filter((p) => p.online && !p.me && isFinite(p.x) && isFinite(p.z) && !(p.x === 0 && p.z === 0))
          .map((p) => ({ id: p.id, name: p.name || 'Planner', color: p.color || '#7fd3ff', x: p.x, z: p.z })));
      }
      const sc = s.scenario;
      const edits = editsOf(s), key = JSON.stringify(edits);
      if (sc && sc.status === 'ready' && sc.planId && (sc.planId !== lastPlan || key !== lastEditsKey)) {
        lastPlan = sc.planId; lastEditsKey = key;
        const payload = { planId: sc.planId, edits, result: s.result };
        if (typeof host.loadLivePlan === 'function') safe('loadLivePlan', payload);
        else safe('applyEdits', edits, 'Live plan');
      } else if (!sc || !sc.planId) {
        if (key !== lastEditsKey && table === '*') { lastEditsKey = key; safe('applyEdits', edits, 'Live plan'); }
      }
      if (table !== 'player' || isOpen()) render(); else renderPill();
    }

    async function start() {
      if (!available || on || connecting || destroyed) return;
      connecting = true; lastErr = null; render();
      try {
        const mod = await import(/* webpackIgnore: true */ liveUrl);
        if (destroyed) return;
        if (perTab) ls.set(LS_KEY, ss.get(SS_KEY));   // this tab's own token, or none -> fresh identity
        on = true; lastPlan = null; lastEditsKey = '';
        live = mod.connectLive({
          uri: opts.uri, db,
          name: myName() || undefined,
          onChange,
          onError: (err) => { console.warn('[HPLive]', err); lastErr = 'Lost the live connection.'; render(); },
        });
        safe('onLiveChange', true);
        safe('toast', 'Live: you now edit the shared plan');
      } catch (e) {
        console.warn('[HPLive] could not load the live client', e);
        on = false; live = null; lastErr = "Couldn't load the live client (live.mjs).";
      } finally { connecting = false; render(); }
    }
    function stop() {
      if (!on) return;
      try { live?.disconnect(); } catch (_) { /* already closed */ }
      live = null; on = false; st = null;
      safe('showCursors', []); safe('onLiveChange', false); render();
    }

    // ── render ──
    const ago = (d) => { const s = Math.max(0, (Date.now() - d.getTime()) / 1000); return s < 60 ? 'now' : s < 3600 ? `${Math.floor(s / 60)}m` : `${Math.floor(s / 3600)}h`; };
    function renderPill() {
      if (!pill) return;
      pill.classList.toggle('hpx-on', on); pill.setAttribute('aria-pressed', String(on));
      pill.querySelector('.hpx-lbl').textContent = connecting ? 'Connecting…' : on ? 'Live' : 'Go live';
      const n = on && st ? st.players.filter((p) => p.online).length : 0;
      pill.querySelector('.hpx-n').textContent = on && n ? `· ${n} online` : '';
    }
    function render() {
      if (destroyed) return;
      renderPill();
      if (!available) {
        bodyEl.innerHTML = `<div class="hpx-offline"><b>Needs the live engine</b><p>Live editing runs on SpacetimeDB (port 3000), which isn't reachable from this page. See <code>backend/live/README.md</code>.</p></div>`;
        return;
      }
      if (!on) {
        bodyEl.innerHTML = `<p class="hpx-dim" style="margin:0 0 10px;font-size:12.5px">Edit one shared plan with everyone in the room. Car-free streets, block edits and cursors sync in about a second.</p>
          <div class="hpx-sw"><input class="hpx-field" data-k="name" maxlength="24" placeholder="Your name" value="${esc(myName())}"></div>
          ${lastErr ? `<p class="hpx-down" style="font-size:11.5px;margin:8px 0 0">${esc(lastErr)}</p>` : ''}
          <div class="hpx-acts"><button class="hpx-btn hpx-primary" data-do="start" ${connecting ? 'disabled' : ''}>${connecting ? '<span class="hpx-spin"></span> Connecting…' : 'Go live'}</button></div>`;
        return;
      }
      const s = st, sc = s?.scenario, res = s?.result;
      const busy = sc && (sc.status === 'pending' || sc.status === 'computing');
      const label = !s ? 'Connecting…' : !sc ? 'Waiting for the shared plan' : sc.status === 'error' ? `Engine error${sc.error ? ': ' + sc.error : ''}` : busy ? (sc.days ? `Replanning day ${sc.day}/${sc.days}…` : 'Replanning…') : 'Settled';
      const v = res?.value?.total;
      const players = (s?.players || []).filter((p) => p.online || p.me).sort((a, b) => b.me - a.me), nOff = (s?.players || []).filter((p) => !p.online && !p.me).length;
      const feed = (s?.activity || []).slice(-12).reverse();
      const nStreets = s ? s.streets.size : 0, nBlocks = s ? s.blocks.size : 0;
      const local = safe('getPlanEdits') || {};
      const canShare = s && !nStreets && !nBlocks && ((local.pedestrianized || []).length || Object.keys(local.blocks || {}).length);
      bodyEl.innerHTML = `<div class="hpx-status">${busy || !s ? '<span class="hpx-spin"></span>' : sc?.status === 'error' ? '<span class="hpx-down">●</span>' : '<span class="hpx-up">●</span>'}<b>${esc(label)}</b>
          ${v != null && isFinite(v) ? `<span class="hpx-v ${v >= 0 ? 'hpx-up' : 'hpx-down'}">${v >= 0 ? '+' : '−'}$${Math.abs(v / 1e6).toFixed(2)}M/yr</span>` : ''}</div>
        <p class="hpx-muted" style="font-size:11px;margin:6px 2px 0">${nStreets} car-free street segment${nStreets === 1 ? '' : 's'} · ${nBlocks} block edit${nBlocks === 1 ? '' : 's'}</p>
        ${lastErr ? `<p class="hpx-down" style="font-size:11.5px;margin:8px 0 0">${esc(lastErr)}</p>` : ''}
        <div class="hpx-sec"><p class="hpx-eyebrow">Planners</p><div class="hpx-players">${players.map((p) => `<div class="hpx-pl ${p.online ? '' : 'hpx-off'}"><i style="background:${esc(p.color)}"></i>${esc(p.name || 'Planner')}${p.me ? '<span class="hpx-me">you</span>' : ''}</div>`).join('') || '<span class="hpx-muted">Just you.</span>'}${nOff ? `<span class="hpx-muted" style="font-size:11px">+${nOff} offline</span>` : ''}</div></div>
        <div class="hpx-sec"><p class="hpx-eyebrow">Activity</p><div class="hpx-feed">${feed.map((a) => `<div><b style="color:${esc(a.color)}">${esc(a.who)}</b><span>${esc(a.text)}</span><time>${ago(a.at)}</time></div>`).join('') || '<span class="hpx-muted">No edits yet.</span>'}</div></div>
        <div class="hpx-sec"><div class="hpx-sw"><input class="hpx-field" data-k="name" maxlength="24" placeholder="Your name" value="${esc(myName() || players.find((p) => p.me)?.name || '')}"><button class="hpx-btn hpx-sm" data-do="rename">Rename</button></div></div>
        <div class="hpx-acts">${canShare ? '<button class="hpx-btn hpx-primary hpx-sm" data-do="share">Share my plan</button>' : ''}<button class="hpx-btn hpx-sm" data-do="reset" ${nStreets || nBlocks ? '' : 'disabled'}>Reset shared plan</button><button class="hpx-btn hpx-sm" data-do="stop">Leave</button></div>`;
    }

    bodyEl.addEventListener('click', (e) => {
      const b = e.target.closest('button[data-do]'); if (!b || b.disabled) return;
      const nm = bodyEl.querySelector('[data-k=name]')?.value.trim();
      if (b.dataset.do === 'start') { if (nm) ls.set('planner-name', nm); start(); }
      else if (b.dataset.do === 'rename' && nm) { ls.set('planner-name', nm); api.setName(nm); safe('toast', `You're ${nm}`); }
      else if (b.dataset.do === 'reset') api.reset();
      else if (b.dataset.do === 'stop') stop();
      else if (b.dataset.do === 'share') {
        const local = safe('getPlanEdits') || {};
        if ((local.pedestrianized || []).length) api.setPedestrian(local.pedestrianized, true);
        const byKey = new Map();
        for (const [bid, ed] of Object.entries(local.blocks || {})) { const k = `${ed.scale ?? 1}|${ed.zone || ''}`; if (!byKey.has(k)) byKey.set(k, []); byKey.get(k).push(+bid); }
        for (const [k, ids] of byKey) { const [sc, z] = k.split('|'); api.setBlock(ids, +sc, z); }
      }
    });
    bodyEl.addEventListener('keydown', (e) => { if (e.key === 'Enter' && e.target.matches('[data-k=name]')) { e.preventDefault(); bodyEl.querySelector('[data-do=rename],[data-do=start]')?.click(); } });
    pill?.addEventListener('click', () => { if (!on && !connecting) { open(); start(); } else toggle(); });
    panel.querySelector('[data-act=close]').addEventListener('click', () => close());

    const guard = (fn) => (...a) => { if (!on || !live) return false; try { Promise.resolve(fn(...a)).catch((err) => console.warn('[HPLive] reducer failed', err)); } catch (err) { console.warn('[HPLive]', err); return false; } return true; };
    const isOpen = () => !panel.classList.contains('hpx-closed');
    function open() { if (!available) return; panel.classList.remove('hpx-closed'); render(); safe('onPanel', 'live', true); }
    function close() { panel.classList.add('hpx-closed'); safe('onPanel', 'live', false); }
    function toggle() { isOpen() ? close() : open(); }
    function destroy() { stop(); destroyed = true; wrap.remove(); }

    const api = {
      open, close, toggle, destroy, isOpen, start, stop, ready, el: panel, pill,
      isLive: () => on && !!live,
      isAvailable: () => available,
      state: () => (live ? live.state() : null),
      setPedestrian: guard((ids, flag = true) => live.setPedestrian([].concat(ids).map(Number), !!flag)),
      setBlock: guard((ids, scale = 1, zone = '') => live.setBlock([].concat(ids).map(Number), +scale, zone || '')),
      reset: guard(() => live.reset()),
      setName: guard((n) => live.setName(String(n).slice(0, 24))),
      cursor: guard((x, z) => { if (isFinite(x) && isFinite(z)) live.setCursor(+x, +z); }),
    };
    render();
    return api;
  }

  window.HPLive = { mount };
})();
