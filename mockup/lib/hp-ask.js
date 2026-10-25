// The Human Project · "Ask the city": Droid live agent drawer (POST /droid/ask?stream=1).
// Classic script, no imports. Defines window.HPAsk = { mount(host, opts) }.
// Talks to the page only through the host API (docs/fully-functional-spec.md §2):
//   { B, world, getPlanEdits, applyEdits, currentScenarioId, flyTo, highlight, setInfoView, setTime, toast, mount, theme }
// Optional host extras it uses when present: getTime() -> seconds, getSelected() -> {type,id}, focusFor(ref) -> {x,z,radius}.
(() => {
  if (window.HPAsk) return;

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
.hpx-ask{left:12px;top:72px;bottom:72px;width:380px;max-width:calc(100vw - 24px)}
.hpx-ask .hpx-msgs{display:flex;flex-direction:column;gap:12px}
.hpx-ask .hpx-q{align-self:flex-end;max-width:85%;background:var(--hpx-accent);color:#fff;padding:7px 11px;border-radius:12px 12px 4px 12px;font-weight:500}
.hpx-ask .hpx-a{background:var(--hpx-fill);border-radius:12px 12px 12px 4px;padding:10px 12px}
.hpx-ask .hpx-md p{margin:0 0 7px}.hpx-ask .hpx-md p:last-child{margin-bottom:0}
.hpx-ask .hpx-md ul,.hpx-ask .hpx-md ol{margin:0 0 7px;padding-left:18px}.hpx-ask .hpx-md li{margin:2px 0}
.hpx-ask .hpx-md strong{color:#fff;font-weight:700}
.hpx-ask .hpx-md code{font:11.5px ui-monospace,Menlo,monospace;background:var(--hpx-sunk);padding:1px 4px;border-radius:4px}
.hpx-ask .hpx-steps{display:flex;flex-direction:column;gap:2px;margin:0 0 8px;padding:6px 8px;border-radius:var(--hpx-r-sm);background:var(--hpx-sunk)}
.hpx-ask .hpx-steps-h{display:flex;align-items:center;gap:7px;font-size:11px;font-weight:600;color:var(--hpx-dim);padding:2px 0 4px;width:100%;text-align:left}
.hpx-ask .hpx-steps-h .hpx-car{margin-left:auto;color:var(--hpx-mute);transition:transform .15s}
.hpx-ask .hpx-steps.hpx-fold .hpx-step{display:none}.hpx-ask .hpx-steps.hpx-fold .hpx-car{transform:rotate(-90deg)}
.hpx-ask .hpx-step{display:flex;align-items:flex-start;gap:7px;font-size:11.5px;color:var(--hpx-dim);text-align:left;width:100%;padding:2px 0}
.hpx-ask .hpx-step .hpx-ico{width:12px;height:12px;flex:none;margin-top:2px;display:grid;place-items:center;font-size:10px;font-weight:800}
.hpx-ask .hpx-step.hpx-done .hpx-ico{color:var(--hpx-good)}.hpx-ask .hpx-step.hpx-err .hpx-ico{color:var(--hpx-bad)}
.hpx-ask .hpx-step.hpx-denied .hpx-ico{color:var(--hpx-warn)}
.hpx-ask .hpx-step .hpx-lbl{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.hpx-ask .hpx-step.hpx-open .hpx-lbl{white-space:normal}
.hpx-ask .hpx-refs{display:flex;flex-wrap:wrap;gap:5px;margin-top:9px}
.hpx-ask .hpx-chip{display:inline-flex;flex-direction:column;align-items:flex-start;gap:1px;max-width:100%;padding:5px 9px;border-radius:var(--hpx-r-sm);background:rgba(127,211,255,.10);
border:1px solid rgba(127,211,255,.18);text-align:left;transition:background .15s,border-color .15s}
.hpx-ask .hpx-chip:hover{background:rgba(127,211,255,.2);border-color:rgba(127,211,255,.4)}
.hpx-ask .hpx-chip.hpx-on{background:rgba(127,211,255,.26);border-color:var(--hpx-hi)}
.hpx-ask .hpx-chip b{font-size:11.5px;font-weight:600;color:#fff;display:flex;gap:6px;align-items:baseline}
.hpx-ask .hpx-chip b i{font-style:normal;color:var(--hpx-hi);font-weight:700}
.hpx-ask .hpx-chip span{font-size:10.5px;color:var(--hpx-dim)}
.hpx-ask .hpx-meta{display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin-top:9px;font-size:10.5px;color:var(--hpx-mute)}
.hpx-ask .hpx-meta .hpx-btn{margin-left:auto}
.hpx-ask .hpx-err-box{color:#ffc4c4;font-size:12px}
.hpx-ask .hpx-foot{flex:none;padding:10px 12px 12px;border-top:1px solid var(--hpx-line)}
.hpx-ask .hpx-inrow{display:flex;gap:6px;padding:3px 3px 3px 11px;border-radius:var(--hpx-r-sm);background:var(--hpx-sunk);border:1px solid var(--hpx-line)}
.hpx-ask .hpx-inrow input{flex:1;min-width:0;background:none;border:0;color:var(--hpx-fg);font:inherit;padding:6px 0;outline:none}
.hpx-ask .hpx-inrow input::placeholder{color:var(--hpx-mute)}
.hpx-ask .hpx-sugs{display:flex;flex-wrap:wrap;gap:5px;margin-top:8px}
.hpx-ask .hpx-sug{font-size:11.5px;padding:4px 9px;border-radius:999px;background:var(--hpx-fill);color:var(--hpx-dim)}
.hpx-ask .hpx-sug:hover{background:var(--hpx-fill-hi);color:#fff}
.hpx-ask .hpx-empty{color:var(--hpx-dim);font-size:12.5px}
.hpx-ask .hpx-empty b{display:block;color:#fff;font-size:13.5px;margin-bottom:3px}
`;

  const SUGGESTIONS = ['Where is traffic worst at 8am?', 'Which businesses lose out?', 'What happened to Maria today?', 'How many people arrive at Embarcadero BART?'];

  // Tiny, safe markdown: escape first, then bold / italic / code, bullet and numbered lists, paragraphs.
  function md(src) {
    const inline = (s) => esc(s)
      .replace(/`([^`]+)`/g, '<code>$1</code>')
      .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
      .replace(/(^|[^*])\*([^*\s][^*]*)\*/g, '$1<em>$2</em>');
    const out = []; let list = null;
    const flush = () => { if (list) { out.push(`<${list.t}>${list.items.map((i) => `<li>${inline(i)}</li>`).join('')}</${list.t}>`); list = null; } };
    let para = [];
    const flushP = () => { if (para.length) { out.push(`<p>${inline(para.join(' '))}</p>`); para = []; } };
    for (const raw of String(src || '').split('\n')) {
      const line = raw.trim();
      const ul = /^[-*•]\s+(.*)$/.exec(line), ol = /^\d+[.)]\s+(.*)$/.exec(line);
      if (ul || ol) {
        flushP(); const t = ul ? 'ul' : 'ol';
        if (!list || list.t !== t) { flush(); list = { t, items: [] }; }
        list.items.push((ul || ol)[1]);
      } else if (!line) { flushP(); flush(); }
      else { flush(); para.push(line.replace(/^#{1,6}\s+/, '')); }
    }
    flushP(); flush();
    return out.join('');
  }

  function mount(host, opts = {}) {
    host = host || {};
    const safe = (name, ...a) => { try { const f = host[name]; return typeof f === 'function' ? f.apply(host, a) : undefined; } catch (e) { console.warn(`[HPAsk] host.${name} failed`, e); } };
    const B = host.B || null;
    const api = opts.api || B?.api || 'http://localhost:8787';
    const live = () => !!B && B.mode === 'live';
    ensureCss('hpx-base-css', BASE_CSS); ensureCss('hpx-ask-css', CSS);

    const root = document.createElement('section');
    root.className = 'hpx hpx-panel hpx-ask hpx-closed' + (opts.className ? ' ' + opts.className : '');
    root.setAttribute('aria-label', 'Ask the city');
    root.innerHTML = `
      <div class="hpx-head"><h3>Ask the city <span class="hpx-tag">Droid</span></h3>
        <button class="hpx-btn hpx-sm" data-act="new" title="Start a new conversation">New chat</button>
        <button class="hpx-x" data-act="close" aria-label="Close">${X_ICON}</button></div>
      <div class="hpx-body"><div class="hpx-msgs" aria-live="polite"></div></div>
      <div class="hpx-foot">
        <form class="hpx-inrow"><input type="text" maxlength="600" placeholder="Ask about this plan…" aria-label="Question">
          <button class="hpx-btn hpx-primary hpx-sm" type="submit">Ask</button></form>
        <div class="hpx-sugs"></div></div>`;
    const mountNode = host.mount || document.body;
    mountNode.appendChild(root);
    const $ = (s) => root.querySelector(s);
    const msgs = $('.hpx-msgs'), body = $('.hpx-body'), form = $('form'), input = $('input'), sugs = $('.hpx-sugs'), sendBtn = form.querySelector('button');

    let conversationId = null, busy = false, aborter = null, destroyed = false, activeChip = null;
    const scrollEnd = () => { body.scrollTop = body.scrollHeight; };

    function renderEmpty() {
      if (!live()) {
        msgs.innerHTML = `<div class="hpx-offline"><b>Needs the live engine</b>
          <p>Droid answers questions by querying the running simulation. Start it with <code>backend/run.sh</code> and reload this page.</p></div>`;
        form.querySelector('input').disabled = true; sendBtn.disabled = true; sugs.hidden = true; $('[data-act=new]').hidden = true;
        return;
      }
      msgs.innerHTML = `<div class="hpx-empty"><b>Ask anything about the plan on screen.</b>
        Droid queries the simulation, answers with its numbers, and points the map at what it mentions.</div>`;
      sugs.hidden = false;
      sugs.innerHTML = SUGGESTIONS.map((s) => `<button class="hpx-sug" type="button">${esc(s)}</button>`).join('');
    }
    sugs.addEventListener('click', (e) => { const b = e.target.closest('.hpx-sug'); if (b) ask(b.textContent); });

    // ── geometry: a reference -> camera target + highlight set ──
    const W = () => host.world || {};
    const EW = () => B?.world || {};
    function refHighlight(ref) {
      const ids = (ref.ids || []).map(Number), h = { edges: [], buildings: [], pois: [], agents: [] };
      const t = ref.type;
      if (t === 'street' || t === 'edge') h.edges = ids;
      else if (t === 'building') h.buildings = ids;
      else if (t === 'poi') h.pois = ids;
      else if (t === 'agent') h.agents = ids;
      else if (t === 'block') { const bo = EW().block_of || W().block_of || []; const set = new Set(ids); bo.forEach((b, i) => { if (set.has(b)) h.buildings.push(i); }); }
      else if (t === 'inlet') for (const id of ids) { const g = (EW().inlets || []).find((x) => x.i === id); if (g?.edges) h.edges.push(...g.edges); }
      return h;
    }
    function refFocus(ref) {
      const own = safe('focusFor', ref); if (own && isFinite(own.x)) return own;
      const pts = [], h = refHighlight(ref), w = W(), ew = EW();
      for (const e of h.edges) for (const p of (w.edges?.[e]?.p || [])) pts.push(p);
      for (const b of h.buildings) { const bd = w.buildings?.[b]; if (bd?.p) pts.push(...bd.p); else if (bd?.c) pts.push(bd.c); }
      for (const id of h.pois) { const p = (ew.pois || [])[id]; if (p && isFinite(p.x)) pts.push([p.x, p.z]); }
      if (ref.type === 'inlet') for (const id of ref.ids || []) { const g = (ew.inlets || []).find((x) => x.i === +id); if (g) pts.push(g.at || [g.x, g.z]); }
      if (!pts.length) return null;
      let x0 = Infinity, x1 = -Infinity, z0 = Infinity, z1 = -Infinity;
      for (const [x, z] of pts) { if (!isFinite(x) || !isFinite(z)) continue; x0 = Math.min(x0, x); x1 = Math.max(x1, x); z0 = Math.min(z0, z); z1 = Math.max(z1, z); }
      if (!isFinite(x0)) return null;
      return { x: (x0 + x1) / 2, z: (z0 + z1) / 2, radius: Math.max(140, Math.hypot(x1 - x0, z1 - z0) * 0.65) };
    }
    function applyAnswer(a) {
      if (!a) return;
      if (a.focus && isFinite(a.focus.x)) safe('flyTo', { x: a.focus.x, z: a.focus.z, radius: a.focus.radius_m || a.focus.radius || 300 });
      if (a.highlights) safe('highlight', { edges: a.highlights.edges || [], buildings: a.highlights.buildings || [], pois: a.highlights.pois || [], agents: a.highlights.agents || [] });
      if (a.info_view) safe('setInfoView', a.info_view);
      if (a.time_s != null && isFinite(a.time_s)) safe('setTime', +a.time_s);
    }

    // ── one exchange ──
    function addExchange(question) {
      if (msgs.querySelector('.hpx-empty, .hpx-offline')) msgs.innerHTML = '';
      sugs.hidden = true;
      const q = document.createElement('div'); q.className = 'hpx-q'; q.textContent = question;
      const a = document.createElement('div'); a.className = 'hpx-a';
      a.innerHTML = `<div class="hpx-steps"><button class="hpx-steps-h" type="button"><span class="hpx-spin"></span><span class="hpx-st">Droid is looking at the simulation…</span><span class="hpx-car">▾</span></button></div><div class="hpx-ans"></div>`;
      msgs.append(q, a); scrollEnd();
      const stepsEl = a.querySelector('.hpx-steps');
      a.querySelector('.hpx-steps-h').addEventListener('click', () => stepsEl.classList.toggle('hpx-fold'));
      const steps = new Map();
      return {
        el: a,
        step(s) {
          let row = steps.get(s.id);
          if (!row) {
            row = document.createElement('button'); row.type = 'button'; row.className = 'hpx-step';
            row.addEventListener('click', () => { row.classList.toggle('hpx-open'); const pre = row.nextElementSibling; if (pre?.classList.contains('hpx-pre')) pre.hidden = !pre.hidden; });
            const pre = document.createElement('pre'); pre.className = 'hpx-pre'; pre.hidden = true;
            stepsEl.append(row, pre); steps.set(s.id, row);
          }
          const st = s.status || 'running';
          row.className = 'hpx-step' + (st === 'done' ? ' hpx-done' : st === 'error' ? ' hpx-err' : st === 'denied' ? ' hpx-denied' : '') + (row.classList.contains('hpx-open') ? ' hpx-open' : '');
          const ico = st === 'running' ? '<span class="hpx-spin" style="width:10px;height:10px;border-width:1.5px"></span>' : st === 'done' ? '✓' : st === 'denied' ? '!' : '✕';
          row.innerHTML = `<span class="hpx-ico">${ico}</span><span class="hpx-lbl">${esc(s.label || s.simq || 'Query')}</span>`;
          const pre = row.nextElementSibling;
          if (pre) pre.textContent = (s.simq ? `$ simq ${s.simq}\n` : '') + (s.status === 'denied' ? 'Command denied by the sandbox.' : (s.output || ''));
          a.querySelector('.hpx-st').textContent = `Running ${steps.size} quer${steps.size === 1 ? 'y' : 'ies'}…`;
          scrollEnd();
        },
        finish(ans, err) {
          const head = a.querySelector('.hpx-steps-h');
          head.querySelector('.hpx-spin')?.remove();
          if (steps.size) { a.querySelector('.hpx-st').textContent = `${steps.size} simulation quer${steps.size === 1 ? 'y' : 'ies'}`; stepsEl.classList.add('hpx-fold'); }
          else stepsEl.remove();
          const box = a.querySelector('.hpx-ans');
          if (err) { box.innerHTML = `<div class="hpx-err-box">${esc(err)}</div><div class="hpx-meta"><button class="hpx-btn hpx-sm" type="button">Retry</button></div>`; box.querySelector('button').onclick = () => { a.previousElementSibling?.remove(); a.remove(); ask(question); }; scrollEnd(); return; }
          const refs = (ans.references || []).filter((r) => r && (r.ids?.length || r.label));
          box.innerHTML = `<div class="hpx-md">${md(ans.answer)}</div>` +
            (refs.length ? `<div class="hpx-refs">${refs.map((r, i) => `<button class="hpx-chip" type="button" data-i="${i}" title="${esc(r.why || '')}"><b>${esc(r.label || `${r.type} ${(r.ids || []).join(', ')}`)}${r.value ? `<i>${esc(r.value)}</i>` : ''}</b>${r.why ? `<span>${esc(r.why)}</span>` : ''}</button>`).join('')}</div>` : '') +
            `<div class="hpx-meta"><span>${ans.source === 'narrative_fallback' ? 'Claude summary (Droid unavailable)' : ans.source === 'narrative' ? 'Claude summary' : 'Droid'}${ans.latency_s ? ` · ${(+ans.latency_s).toFixed(1)} s` : ''}</span>` +
            (ans.focus || ans.highlights ? `<button class="hpx-btn hpx-sm" type="button" data-act="show">Show on map</button>` : '') + `</div>`;
          box.querySelectorAll('.hpx-chip').forEach((c) => c.addEventListener('click', () => {
            const r = refs[+c.dataset.i]; const f = refFocus(r) || (ans.focus && { x: ans.focus.x, z: ans.focus.z, radius: ans.focus.radius_m });
            if (activeChip) activeChip.classList.remove('hpx-on'); activeChip = c; c.classList.add('hpx-on');
            if (f) safe('flyTo', f);
            safe('highlight', refHighlight(r));
          }));
          box.querySelector('[data-act=show]')?.addEventListener('click', () => { if (activeChip) activeChip.classList.remove('hpx-on'); applyAnswer(ans); });
          scrollEnd();
        },
      };
    }

    async function streamAsk(payload, ex, signal) {
      const r = await fetch(`${api}/droid/ask?stream=1`, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(payload), signal });
      if (!r.ok) { let d = ''; try { d = (await r.json()).detail; } catch (_) { /* not json */ } const e = new Error(d || `HTTP ${r.status}`); e.status = r.status; throw e; }
      if (!r.body) throw new Error('no stream');
      const reader = r.body.getReader(), dec = new TextDecoder(); let buf = '', answer = null, error = null;
      for (;;) {
        const { value, done } = await reader.read(); if (done) break;
        buf += dec.decode(value, { stream: true });
        let i;
        while ((i = buf.indexOf('\n\n')) >= 0) {
          const chunk = buf.slice(0, i); buf = buf.slice(i + 2);
          const ev = /^event: (.*)$/m.exec(chunk)?.[1]; const d = /^data: (.*)$/m.exec(chunk)?.[1]; if (!d) continue;
          let data; try { data = JSON.parse(d); } catch (_) { continue; }
          if (ev === 'step') ex.step(data); else if (ev === 'answer') answer = data; else if (ev === 'error') error = data.error || 'Droid failed';
        }
      }
      if (!answer) throw new Error(error || 'Droid returned no answer');
      return answer;
    }

    async function ask(question) {
      question = String(question || '').trim();
      if (busy || destroyed || question.length < 2) return;
      if (!live()) { renderEmpty(); return; }
      busy = true; sendBtn.disabled = true; input.value = '';
      const ex = addExchange(question);
      const sid = safe('currentScenarioId') || 'baseline';
      const view = {};
      const t = safe('getTime'); if (isFinite(t)) view.time_s = Math.round(t);
      const sel = safe('getSelected'); if (sel && sel.type != null) view.selected = sel;
      const payload = { scenario: sid, question, ...(conversationId ? { conversation_id: conversationId } : {}), ...(Object.keys(view).length ? { view } : {}) };
      aborter = new AbortController();
      const timer = setTimeout(() => aborter?.abort(), opts.timeoutMs || 90000);
      try {
        const ans = await streamAsk(payload, ex, aborter.signal);
        if (ans.conversation_id) conversationId = ans.conversation_id;
        ex.finish(ans); if (opts.autoApply !== false) applyAnswer(ans);
      } catch (e) {
        if (destroyed) return;
        if (e.status === 404) ex.finish(null, 'This plan is no longer on the engine. Re-run the plan, then ask again.');
        else if (e.status === 400) ex.finish(null, e.message);
        else {
          // Droid route down or failed: fall back to the Claude narrative explainer (text only, no map pointers).
          try {
            const n = await B.narrative.explain(sid, question);
            if (n?.answer) ex.finish({ answer: n.answer, references: [], source: 'narrative_fallback' });
            else throw new Error('empty');
          } catch (_) { ex.finish(null, e.name === 'AbortError' ? 'Droid took too long to answer.' : "Couldn't reach Droid or the narrator. Is the engine still running?"); }
        }
      } finally { clearTimeout(timer); aborter = null; busy = false; sendBtn.disabled = false; if (isOpen()) input.focus(); }
    }

    form.addEventListener('submit', (e) => { e.preventDefault(); ask(input.value); });
    $('[data-act=close]').addEventListener('click', () => close());
    $('[data-act=new]').addEventListener('click', () => reset());
    root.addEventListener('keydown', (e) => { if (e.key === 'Escape') close(); });

    function reset() {
      aborter?.abort();
      if (conversationId && live()) fetch(`${api}/droid/conversations/${encodeURIComponent(conversationId)}`, { method: 'DELETE' }).catch(() => {});
      conversationId = null; activeChip = null; renderEmpty();
    }
    const isOpen = () => !root.classList.contains('hpx-closed');
    function open() { root.classList.remove('hpx-closed'); if (live()) setTimeout(() => input.focus(), 50); safe('onPanel', 'ask', true); }
    function close() { root.classList.add('hpx-closed'); safe('onPanel', 'ask', false); }
    function toggle() { isOpen() ? close() : open(); }
    function destroy() { destroyed = true; aborter?.abort(); root.remove(); }

    renderEmpty();
    return { open, close, toggle, destroy, ask, reset, isOpen, el: root, get conversationId() { return conversationId; }, available: live() };
  }

  window.HPAsk = { mount, _md: md };
})();
