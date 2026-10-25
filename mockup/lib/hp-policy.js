// The Human Project · Policy Book: built-in levers + Droid-written levers (GET /policies, POST /policies/propose, /approve, /reject).
// Classic script, no imports. Defines window.HPPolicy = { mount(host, opts) }.
// Host API (docs/fully-functional-spec.md §2): { B, world, getPlanEdits, applyEdits(edits, label), currentScenarioId, toast, mount, ... }.
// applyEdits receives the FULL new plan (this module merges the lever into getPlanEdits() itself, via B.mergeEdits).
(() => {
  if (window.HPPolicy) return;

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
.hpx-pol{left:12px;top:72px;bottom:72px;width:400px;max-width:calc(100vw - 24px)}
.hpx-pol .hpx-tabs{display:flex;gap:2px;padding:3px;border-radius:var(--hpx-r-sm);background:var(--hpx-sunk);margin:10px 14px 0;flex:none}
.hpx-pol .hpx-tabs button{flex:1;height:26px;border-radius:var(--hpx-r-xs);font-size:12.5px;font-weight:600;color:var(--hpx-dim)}
.hpx-pol .hpx-tabs button:hover{color:#fff}.hpx-pol .hpx-tabs button.hpx-on{background:var(--hpx-fill-hi);color:#fff}
.hpx-pol .hpx-lever h4{margin:0;font-size:13px;font-weight:700;display:flex;align-items:center;gap:7px}
.hpx-pol .hpx-lever p{margin:3px 0 9px;font-size:11.5px;color:var(--hpx-dim)}
.hpx-pol .hpx-lever.hpx-active{box-shadow:inset 0 0 0 1px rgba(180,108,255,.5)}
.hpx-pol .hpx-act-tag{font-size:10px;font-weight:700;color:#d6b4ff;background:rgba(180,108,255,.18);padding:2px 6px;border-radius:var(--hpx-r-xs);text-transform:uppercase;letter-spacing:.04em}
.hpx-pol .hpx-droid-tag{font-size:10px;font-weight:700;color:var(--hpx-hi);background:rgba(127,211,255,.12);padding:2px 6px;border-radius:var(--hpx-r-xs)}
.hpx-pol .hpx-row{display:flex;align-items:center;gap:8px;margin-top:7px}
.hpx-pol .hpx-row label{font-size:11.5px;color:var(--hpx-dim);flex:none;min-width:78px}
.hpx-pol .hpx-row output{font-weight:700;min-width:62px;text-align:right;font-size:12px}
.hpx-pol .hpx-row input[type=range]{flex:1}
.hpx-pol .hpx-row select{flex:1}
.hpx-pol .hpx-check{display:flex;align-items:center;gap:7px;font-size:12px;color:var(--hpx-dim);margin-top:7px}
.hpx-pol .hpx-acts{display:flex;gap:6px;justify-content:flex-end;margin-top:10px}
.hpx-pol .hpx-note{font-size:11px;color:var(--hpx-mute);margin:10px 2px 0}
.hpx-pol textarea.hpx-field{resize:vertical;min-height:60px}
.hpx-pol .hpx-prop{display:flex;align-items:center;gap:8px;width:100%;text-align:left;padding:9px 11px;border-radius:var(--hpx-r-sm);background:var(--hpx-fill);margin-top:6px}
.hpx-pol .hpx-prop:hover{background:var(--hpx-fill-hi)}
.hpx-pol .hpx-prop .hpx-t{flex:1;min-width:0}
.hpx-pol .hpx-prop .hpx-t b{display:block;font-size:12.5px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.hpx-pol .hpx-prop .hpx-t span{font-size:11px;color:var(--hpx-mute)}
.hpx-pol .hpx-st{font-size:10.5px;font-weight:700;text-transform:uppercase;letter-spacing:.04em;padding:2px 7px;border-radius:999px;flex:none;display:inline-flex;align-items:center;gap:5px}
.hpx-pol .hpx-st-run{background:rgba(127,211,255,.14);color:var(--hpx-hi)}
.hpx-pol .hpx-st-ready{background:rgba(255,210,58,.16);color:#ffe17a}
.hpx-pol .hpx-st-approved{background:rgba(79,220,122,.16);color:#8ff0ae}
.hpx-pol .hpx-st-failed,.hpx-pol .hpx-st-rejected{background:rgba(255,93,93,.12);color:#ffb0b0}
.hpx-pol .hpx-back{font-size:12px;color:var(--hpx-dim);font-weight:600;margin-bottom:8px}
.hpx-pol .hpx-back:hover{color:#fff}
.hpx-pol .hpx-sec{margin-top:12px}
.hpx-pol .hpx-checks{display:flex;flex-direction:column;gap:3px}
.hpx-pol .hpx-checks div{display:flex;gap:7px;font-size:11.5px}
.hpx-pol .hpx-checks i{font-style:normal;font-weight:800;width:12px;flex:none}
.hpx-pol .hpx-checks .hpx-ok i{color:var(--hpx-good)}.hpx-pol .hpx-checks .hpx-no i{color:var(--hpx-bad)}
.hpx-pol .hpx-checks span{color:var(--hpx-dim);min-width:0;overflow-wrap:anywhere}
.hpx-pol .hpx-kv{display:grid;grid-template-columns:1fr auto auto;gap:4px 12px;font-size:11.5px;align-items:baseline;padding:8px 10px;border-radius:var(--hpx-r-sm);background:var(--hpx-sunk)}
.hpx-pol .hpx-kv span:nth-child(3n+1){color:var(--hpx-dim)}
.hpx-pol .hpx-kv span:nth-child(3n+2),.hpx-pol .hpx-kv span:nth-child(3n){text-align:right;font-weight:600}
.hpx-pol .hpx-kv .hpx-h{color:var(--hpx-mute)!important;font-size:10px;font-weight:500!important}
.hpx-pol details summary{cursor:pointer;font-size:11.5px;font-weight:600;color:var(--hpx-dim);list-style:none}
.hpx-pol details summary::-webkit-details-marker{display:none}
.hpx-pol details summary::before{content:"▸ ";color:var(--hpx-mute)}.hpx-pol details[open] summary::before{content:"▾ "}
.hpx-pol .hpx-diff .hpx-add{color:#8ff0ae}.hpx-pol .hpx-diff .hpx-del{color:#ffb0b0}.hpx-pol .hpx-diff .hpx-hunk{color:var(--hpx-hi)}
.hpx-pol .hpx-plan p{margin:0 0 6px;font-size:12px;color:var(--hpx-dim)}
.hpx-pol .hpx-plan ul{margin:0;padding-left:16px;font-size:11.5px;color:var(--hpx-dim)}
.hpx-pol .hpx-decide{display:flex;gap:6px;margin-top:12px;position:sticky;bottom:-12px;padding:10px 0 2px;background:linear-gradient(transparent,rgba(16,32,60,.95) 30%)}
.hpx-pol .hpx-decide .hpx-btn{flex:1}
`;

  const RUNNING = new Set(['queued', 'planning', 'implementing', 'testing']);
  const STATUS_LABEL = { queued: 'Queued', planning: 'Planning', implementing: 'Writing code', testing: 'Running gate', ready: 'Ready for review', approved: 'Approved', rejected: 'Rejected', failed: 'Failed' };
  // Shown when GET /policies is unreachable (snapshot / offline): the engine's own built-ins.
  const FALLBACK_BUILTINS = [
    { kind: 'congestion_charge', title: 'Congestion charge', builtin: true, description: 'AM-peak (7–10) charge for cars entering; on one inlet or all of them', params: { amount: { default: 5, min: 0, max: 50, unit: 'USD' }, target: { default: '' } } },
    { kind: 'parking_price', title: 'Parking price change', builtin: true, description: '$ per day added to downtown parking', params: { amount: { default: 5, min: -30, max: 50, unit: 'USD/day' } } },
  ];
  const METRIC_ROWS = [
    ['vmt', 'Vehicle miles', 0], ['delay_hours', 'Delay (veh-h)', 0], ['car_commuters', 'Car commuters', 0], ['people', 'People', 0],
    ['revenue', 'Business revenue', '$'], ['visits', 'Visits', 0], ['co2_tonnes', 'CO₂ (t)', 1], ['charges_paid_usd', 'Charges paid', '$'], ['through_charges_paid_usd', 'Through charges', '$'],
  ];
  const fmtN = (v, d = 0) => (v == null || !isFinite(v)) ? '–' : Math.abs(v) >= 1e6 ? (v / 1e6).toFixed(2) + 'M' : Math.abs(v) >= 1e4 ? (v / 1e3).toFixed(1) + 'k' : (+v).toLocaleString('en-US', { maximumFractionDigits: d });
  const fmtMoney = (v) => (v < 0 ? '−$' : '$') + fmtN(Math.abs(v));
  const fmtUnit = (v, unit) => unit === 'USD' ? `$${v}` : unit === 'USD/day' ? `${v < 0 ? '−' : '+'}$${Math.abs(v)}/day` : unit ? `${v} ${unit}` : String(v);

  function mount(host, opts = {}) {
    host = host || {};
    const safe = (name, ...a) => { try { const f = host[name]; return typeof f === 'function' ? f.apply(host, a) : undefined; } catch (e) { console.warn(`[HPPolicy] host.${name} failed`, e); } };
    const B = host.B || null;
    const api = opts.api || B?.api || 'http://localhost:8787';
    const live = () => !!B && B.mode === 'live';
    ensureCss('hpx-base-css', BASE_CSS); ensureCss('hpx-pol-css', CSS);

    const root = document.createElement('section');
    root.className = 'hpx hpx-panel hpx-pol hpx-closed' + (opts.className ? ' ' + opts.className : '');
    root.setAttribute('aria-label', 'Policy Book');
    root.innerHTML = `
      <div class="hpx-head"><h3>Policy Book</h3><button class="hpx-x" data-act="close" aria-label="Close">${X_ICON}</button></div>
      <div class="hpx-tabs" role="tablist"><button class="hpx-on" data-tab="levers" role="tab">Levers</button><button data-tab="droid" role="tab">Write a lever with Droid</button></div>
      <div class="hpx-body"></div>`;
    (host.mount || document.body).appendChild(root);
    const bodyEl = root.querySelector('.hpx-body');
    let tab = 'levers', book = null, proposals = [], detail = null, pollT = null, destroyed = false, loadErr = null;

    const getJSON = async (path, init, ms = 15000) => {
      const ctl = new AbortController(); const t = setTimeout(() => ctl.abort(), ms);
      try {
        const r = await fetch(api + path, { ...(init || {}), signal: ctl.signal });
        let j = null; try { j = await r.json(); } catch (_) { /* empty */ }
        if (!r.ok) { const e = new Error(j?.detail || `HTTP ${r.status}`); e.status = r.status; throw e; }
        return j;
      } finally { clearTimeout(t); }
    };
    const post = (path, body) => getJSON(path, { method: 'POST', headers: { 'content-type': 'application/json' }, body: body ? JSON.stringify(body) : undefined });

    async function load() {
      if (!live()) { book = FALLBACK_BUILTINS; proposals = []; render(); return; }
      try { const j = await getJSON('/policies?full=false'); book = j.policies || []; proposals = (j.proposals || []).slice().sort((a, b) => (b.created_at || 0) - (a.created_at || 0)); loadErr = null; }
      catch (e) { loadErr = e.message; book = book || FALLBACK_BUILTINS; }
      if (!destroyed) render();
      schedulePoll();
    }
    function schedulePoll() {
      clearTimeout(pollT);
      const running = proposals.some((p) => RUNNING.has(p.status)) || (detail && RUNNING.has(detail.status));
      if (running && !destroyed) pollT = setTimeout(async () => {
        if (detail) { try { detail = await getJSON('/policies/' + encodeURIComponent(detail.id)); } catch (_) { /* keep */ } }
        load();
      }, 4000);
    }

    // ── plan helpers ──
    const planEdits = () => { const e = safe('getPlanEdits') || {}; return { pedestrianized: e.pedestrianized || [], blocks: e.blocks || {}, policies: e.policies || [], reopened: e.reopened || [], ...(e.reopen_mode ? { reopen_mode: e.reopen_mode } : {}) }; };
    const merge = (a, b) => {
      const m = (B && typeof B.mergeEdits === 'function') ? B.mergeEdits(a, b) : (window.HPBackend?.mergeEdits || ((x, y) => ({ ...x, ...y })))(a, b);
      const mode = b.reopen_mode !== undefined ? b.reopen_mode : a.reopen_mode;   // mergeEdits doesn't carry reopen_mode
      if (mode && m.reopened?.length) m.reopen_mode = mode;
      return m;
    };
    const marketEdges = () => (B?.world?.base_car_free_edges || host.world?.base_car_free_edges || []).map(Number);
    const activePolicy = (kind) => planEdits().policies.find((p) => p.kind === kind);
    const marketActive = () => { const m = new Set(marketEdges()); return m.size > 0 && planEdits().reopened.some((e) => m.has(+e)); };

    async function applyPlan(edits, label, btn) {
      if (btn) { btn.disabled = true; btn.dataset.txt = btn.textContent; btn.innerHTML = '<span class="hpx-spin"></span> Settling…'; }
      try { await safe('applyEdits', edits, label); safe('toast', label); }
      catch (e) { safe('toast', `Couldn't apply: ${e.message || e}`); }
      finally { if (!destroyed) render(); }
    }

    // ── render ──
    function render() {
      if (destroyed) return;
      root.querySelectorAll('[data-tab]').forEach((b) => b.classList.toggle('hpx-on', b.dataset.tab === tab));
      const keep = bodyEl.scrollTop;
      if (tab === 'levers') renderLevers(); else if (detail) renderDetail(); else renderDroid();
      bodyEl.scrollTop = keep;
    }

    function rangeRow(id, label, spec, value) {
      const min = spec.min ?? 0, max = spec.max ?? Math.max(10, (spec.default || 1) * 4);
      const span = max - min, step = spec.step ?? (span <= 2 ? 0.01 : span <= 20 ? 0.5 : 1);
      return `<div class="hpx-row"><label for="${id}">${label}</label><input id="${id}" type="range" min="${min}" max="${max}" step="${step}" value="${value}" data-unit="${spec.unit || ''}"><output>${fmtUnit(value, spec.unit)}</output></div>`;
    }

    function renderLevers() {
      if (!book) { bodyEl.innerHTML = '<div class="hpx-dim" style="display:flex;gap:8px;align-items:center"><span class="hpx-spin"></span> Loading levers…</div>'; return; }
      const carInlets = (B?.world?.inlets || []).filter((g) => g.mode === 'car' && g.has_entry !== false)
        .sort((a, b) => (b.legacy ? 1 : 0) - (a.legacy ? 1 : 0) || String(a.name).localeCompare(b.name));
      const cards = [];
      for (const p of book) {
        const act = activePolicy(p.kind);
        const head = `<h4>${esc(p.title || p.kind)} ${p.builtin ? '' : '<span class="hpx-droid-tag">Droid</span>'} ${act ? '<span class="hpx-act-tag">In plan</span>' : ''}</h4><p>${esc(p.description || '')}</p>`;
        let ctrls = '';
        if (p.kind === 'congestion_charge') {
          const tgt = act?.target ?? '';
          ctrls = `<div class="hpx-row"><label for="hpx-cc-t">Where</label><select id="hpx-cc-t" class="hpx-field" data-k="target"><option value="">Every car inlet</option>${carInlets.map((g) => `<option value="${esc(g.key)}" ${g.key === tgt ? 'selected' : ''}>${esc(g.name)}</option>`).join('')}</select></div>` +
            rangeRow('hpx-cc-a', 'Charge', p.params.amount, act?.amount ?? p.params.amount.default);
        } else if (p.kind === 'parking_price') {
          ctrls = rangeRow('hpx-pp-a', 'Change', p.params.amount, act?.amount ?? p.params.amount.default);
        } else {
          for (const [k, spec] of Object.entries(p.params || {})) {
            if (typeof spec?.default !== 'number') continue;
            ctrls += rangeRow(`hpx-p-${p.kind}-${k}`, esc(k.replace(/_/g, ' ')), spec, act?.params?.[k] ?? spec.default).replace('<input ', `<input data-k="${esc(k)}" `);
          }
        }
        if (!live() && !p.builtin) continue;
        cards.push(`<div class="hpx-card hpx-lever ${act ? 'hpx-active' : ''}" data-kind="${esc(p.kind)}">${head}${ctrls}
          <div class="hpx-acts">${act ? '<button class="hpx-btn hpx-sm" data-do="remove">Remove</button>' : ''}<button class="hpx-btn hpx-primary hpx-sm" data-do="apply">${act ? 'Update' : 'Apply to plan'}</button></div></div>`);
      }
      // Reopen Market St to cars (edit fields `reopened` + `reopen_mode`).
      const mk = marketEdges(), mAct = marketActive(), mMode = planEdits().reopen_mode;
      if (mk.length) cards.splice(Math.min(2, cards.length), 0, `<div class="hpx-card hpx-lever ${mAct ? 'hpx-active' : ''}" data-kind="__market"><h4>Reopen Market St to cars ${mAct ? '<span class="hpx-act-tag">In plan</span>' : ''}</h4>
        <p>Market St has been car-free since 2020. Undo that on all ${mk.length} segments.</p>
        <label class="hpx-check"><input type="checkbox" data-k="pre2020" ${mAct ? (mMode === 'pre2020' ? 'checked' : '') : 'checked'}> With the old pre-2020 forced turns</label>
        <div class="hpx-acts">${mAct ? '<button class="hpx-btn hpx-sm" data-do="remove">Keep car-free</button>' : ''}<button class="hpx-btn hpx-primary hpx-sm" data-do="apply">${mAct ? 'Update' : 'Reopen'}</button></div></div>`);
      bodyEl.innerHTML = cards.join('') +
        (loadErr ? `<p class="hpx-note">Couldn't load Droid levers (${esc(loadErr)}). Showing the built-ins.</p>` : '') +
        (!live() ? `<p class="hpx-note">Offline: results are the labelled estimate. Droid-written levers need the live engine.</p>` : `<p class="hpx-note">Each lever is merged into the current plan and the city re-settles.</p>`);
      bodyEl.querySelectorAll('input[type=range]').forEach((r) => r.addEventListener('input', () => { r.nextElementSibling.textContent = fmtUnit(+r.value, r.dataset.unit); }));
    }

    function leverEdits(card) {
      const kind = card.dataset.kind;
      if (kind === '__market') {
        const pre = card.querySelector('[data-k=pre2020]').checked;
        return { label: `Market St reopened to cars${pre ? ' (pre-2020 turns)' : ''}`, edits: { reopened: marketEdges(), reopen_mode: pre ? 'pre2020' : '' } };
      }
      const p = book.find((x) => x.kind === kind);
      if (kind === 'congestion_charge') {
        const target = card.querySelector('[data-k=target]').value || null, amount = +card.querySelector('input[type=range]').value;
        const nm = target ? (B?.world?.inlets || []).find((g) => g.key === target)?.name || target : 'every car inlet';
        return { label: `$${amount} congestion charge at ${nm}`, edits: { policies: [{ kind, target, amount }] } };
      }
      if (kind === 'parking_price') { const amount = +card.querySelector('input[type=range]').value; return { label: `Parking ${fmtUnit(amount, 'USD/day')}`, edits: { policies: [{ kind, amount }] } }; }
      const params = {}; card.querySelectorAll('input[data-k]').forEach((i) => { params[i.dataset.k] = +i.value; });
      return { label: `${p?.title || kind} applied`, edits: { policies: [{ kind, params }] } };
    }
    function removeLever(card) {
      const kind = card.dataset.kind, e = planEdits();
      if (kind === '__market') { const m = new Set(marketEdges()); e.reopened = e.reopened.filter((x) => !m.has(+x)); if (!e.reopened.length) delete e.reopen_mode; return { edits: e, label: 'Market St car-free again' }; }
      e.policies = e.policies.filter((p) => p.kind !== kind);
      return { edits: e, label: `${book.find((x) => x.kind === kind)?.title || kind} removed` };
    }

    function renderDroid() {
      if (!live()) {
        bodyEl.innerHTML = `<div class="hpx-offline"><b>Needs the live engine</b><p>Droid writes, tests and hot-loads new levers inside the running engine. Start it with <code>backend/run.sh</code> and reload.</p></div>`;
        return;
      }
      const running = proposals.some((p) => RUNNING.has(p.status));
      bodyEl.innerHTML = `<div class="hpx-card"><p class="hpx-eyebrow">Ask for a lever the engine doesn't have</p>
          <textarea class="hpx-field" rows="3" maxlength="500" placeholder="e.g. a $5 charge only for through-traffic"></textarea>
          <div class="hpx-acts" style="align-items:center"><span class="hpx-muted" style="font-size:11px;margin-right:auto">Droid plans, codes, tests it. About 2–3 min.</span>
          <button class="hpx-btn hpx-primary hpx-sm" data-do="propose" ${running ? 'disabled title="One proposal at a time"' : ''}>Write it</button></div></div>
        <div class="hpx-sec"><p class="hpx-eyebrow">Proposals</p>${proposals.length ? proposals.map((p) => `<button class="hpx-prop" data-id="${esc(p.id)}">
          <span class="hpx-t"><b>${esc(p.title || p.request)}</b><span>${esc(p.kind || '…')} · ${new Date((p.created_at || 0) * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span></span>${statusPill(p.status)}</button>`).join('') : '<p class="hpx-muted" style="font-size:12px;margin:0">None yet.</p>'}</div>`;
    }
    const statusPill = (s) => `<span class="hpx-st ${RUNNING.has(s) ? 'hpx-st-run' : 'hpx-st-' + esc(s)}">${RUNNING.has(s) ? '<span class="hpx-spin" style="width:9px;height:9px;border-width:1.5px"></span>' : ''}${esc(STATUS_LABEL[s] || s)}</span>`;

    function diffHtml(d) {
      return String(d || '').split('\n').map((l) => `<span class="${l.startsWith('+') && !l.startsWith('+++') ? 'hpx-add' : l.startsWith('-') && !l.startsWith('---') ? 'hpx-del' : l.startsWith('@@') ? 'hpx-hunk' : ''}">${esc(l)}</span>`).join('\n');
    }
    function renderDetail() {
      const p = detail, plan = p.plan || {};
      const g = (p.gates || [])[p.gates.length - 1];
      const m = p.metrics || {};
      const rows = METRIC_ROWS.filter(([k]) => m[k]).map(([k, lbl, f]) => {
        const r = m[k], pct = r.baseline ? (r.delta / r.baseline) * 100 : null;
        const val = f === '$' ? fmtMoney(r.policy) : fmtN(r.policy, f || 0);
        const dl = f === '$' ? fmtMoney(r.delta) : (r.delta > 0 ? '+' : '') + fmtN(r.delta, f || 0);
        return `<span>${lbl}</span><span>${val}</span><span class="${r.delta > 0 ? 'hpx-up' : r.delta < 0 ? 'hpx-down' : ''}">${dl}${pct != null && Math.abs(pct) >= 0.05 ? ` (${pct > 0 ? '+' : ''}${pct.toFixed(1)}%)` : ''}</span>`;
      }).join('');
      bodyEl.innerHTML = `<button class="hpx-back" data-do="back">← All proposals</button>
        <div class="hpx-card"><div style="display:flex;gap:8px;align-items:flex-start"><div style="flex:1;min-width:0"><b style="font-size:13.5px">${esc(plan.title || p.request)}</b>
          <div class="hpx-muted" style="font-size:11.5px;margin-top:2px">“${esc(p.request)}”</div></div>${statusPill(p.status)}</div>
          ${p.error ? `<div class="hpx-down" style="font-size:11.5px;margin-top:6px">${esc(p.error)}</div>` : ''}</div>
        ${plan.summary || plan.hooks ? `<div class="hpx-sec hpx-plan"><p class="hpx-eyebrow">Plan</p>${plan.summary ? `<p>${esc(plan.summary)}</p>` : ''}
          ${plan.hooks ? `<p><b>Hooks:</b> ${esc([].concat(plan.hooks).join(', '))}</p>` : ''}
          ${plan.params ? `<p><b>Params:</b> ${Object.entries(plan.params).map(([k, v]) => `${esc(k)} = ${esc(v?.default ?? JSON.stringify(v))}${v?.unit ? ' ' + esc(v.unit) : ''}`).join(', ')}</p>` : ''}
          ${Array.isArray(plan.assumptions) && plan.assumptions.length ? `<p><b>Assumptions</b></p><ul>${plan.assumptions.map((a) => `<li>${esc(typeof a === 'string' ? a : JSON.stringify(a))}</li>`).join('')}</ul>` : ''}</div>` : ''}
        ${p.todos && String(p.todos).trim() ? `<div class="hpx-sec"><p class="hpx-eyebrow">Droid's steps</p><div class="hpx-pre" style="max-height:none">${esc(p.todos)}</div></div>` : ''}
        ${g ? `<div class="hpx-sec"><p class="hpx-eyebrow">Gate · attempt ${g.attempt} · ${g.passed ? 'passed' : 'failed'}</p><div class="hpx-checks">${(g.checks || []).map((c) => `<div class="${c.ok ? 'hpx-ok' : 'hpx-no'}"><i>${c.ok ? '✓' : '✕'}</i><b style="font-weight:600;flex:none">${esc(c.name)}</b><span>${esc(String(c.detail || '').slice(0, 220))}</span></div>`).join('')}</div></div>` : ''}
        ${rows ? `<div class="hpx-sec"><p class="hpx-eyebrow">Engine test at example params</p><div class="hpx-kv"><span class="hpx-h">Metric</span><span class="hpx-h">With policy</span><span class="hpx-h">vs baseline</span>${rows}</div></div>` : ''}
        ${(p.steps || []).length ? `<div class="hpx-sec"><details><summary>${p.steps.length} tool calls</summary>${p.steps.map((s) => `<div class="hpx-pre">${esc(s.tool)}: ${esc(String(s.summary || '').slice(0, 160))}\n${esc(String(s.input || '').slice(0, 600))}</div>`).join('')}</details></div>` : ''}
        ${p.diff ? `<div class="hpx-sec"><details><summary>Code diff</summary><pre class="hpx-pre hpx-diff" style="max-height:340px">${diffHtml(p.diff)}</pre></details></div>` : ''}
        ${RUNNING.has(p.status) ? `<p class="hpx-note" style="display:flex;gap:7px;align-items:center"><span class="hpx-spin"></span> ${esc(STATUS_LABEL[p.status])}… this updates by itself.</p>` : ''}
        ${p.status === 'ready' ? `<div class="hpx-decide"><button class="hpx-btn hpx-bad" data-do="reject">Reject</button><button class="hpx-btn hpx-good" data-do="approve">Approve &amp; hot-load</button></div>` : ''}
        ${p.status === 'approved' ? `<div class="hpx-decide"><button class="hpx-btn hpx-primary" data-do="to-levers">Use it in the Levers tab</button></div>` : ''}`;
    }

    async function openDetail(id) {
      try { detail = await getJSON('/policies/' + encodeURIComponent(id)); } catch (e) { safe('toast', `Couldn't load proposal: ${e.message}`); return; }
      render(); bodyEl.scrollTop = 0; schedulePoll();
    }

    bodyEl.addEventListener('click', async (e) => {
      const btn = e.target.closest('button'); if (!btn || btn.disabled) return;
      const card = btn.closest('.hpx-lever');
      const act = btn.dataset.do;
      try {
        if (act === 'apply' && card) {
          const { edits, label } = leverEdits(card), base = planEdits();
          base.policies = base.policies.filter((p) => p.kind !== card.dataset.kind);   // one card = one policy (re-targeting replaces it)
          await applyPlan(merge(base, edits), label, btn);
        }
        else if (act === 'remove' && card) { const { edits, label } = removeLever(card); await applyPlan(edits, label, btn); }
        else if (act === 'propose') {
          const ta = bodyEl.querySelector('textarea'); const req = ta.value.trim();
          if (req.length < 3) { ta.focus(); return; }
          btn.disabled = true; btn.innerHTML = '<span class="hpx-spin"></span> Starting…';
          const p = await post('/policies/propose', { request: req });
          safe('toast', 'Droid is writing your lever…');
          detail = p; await load(); openDetail(p.id);
        } else if (act === 'approve' || act === 'reject') {
          btn.disabled = true;
          const r = await post(`/policies/${encodeURIComponent(detail.id)}/${act}`);
          detail = act === 'approve' ? r.proposal : r;
          safe('toast', act === 'approve' ? `${detail.plan?.title || detail.kind} is now a lever` : 'Proposal rejected');
          await load();
        } else if (act === 'back') { detail = null; render(); }
        else if (act === 'to-levers') { detail = null; tab = 'levers'; render(); }
        else if (btn.classList.contains('hpx-prop')) openDetail(btn.dataset.id);
      } catch (err) { safe('toast', err.message || String(err)); render(); }
    });
    root.querySelectorAll('[data-tab]').forEach((b) => b.addEventListener('click', () => { tab = b.dataset.tab; render(); if (tab === 'droid' && live()) load(); }));
    root.querySelector('[data-act=close]').addEventListener('click', () => close());
    root.addEventListener('keydown', (e) => { if (e.key === 'Escape') close(); });

    const isOpen = () => !root.classList.contains('hpx-closed');
    function open() { root.classList.remove('hpx-closed'); load(); safe('onPanel', 'policy', true); }
    function close() { root.classList.add('hpx-closed'); clearTimeout(pollT); safe('onPanel', 'policy', false); }
    function toggle() { isOpen() ? close() : open(); }
    function destroy() { destroyed = true; clearTimeout(pollT); root.remove(); }
    function showTab(t) { tab = t === 'droid' ? 'droid' : 'levers'; detail = null; render(); }

    render();
    return { open, close, toggle, destroy, isOpen, refresh: load, showTab, el: root, available: live() };
  }

  window.HPPolicy = { mount };
})();
