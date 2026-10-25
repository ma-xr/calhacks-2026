// The Human Project · backend connector for the mockup pages.
// Inlined into each page at build time (scripts/build_mockup.py replaces /*__HP_BACKEND__*/).
// Talks to the simulation API (docs/contracts/sim-api.md). Falls back to a bundled snapshot
// (./backend-snapshot/) when the API is unreachable, e.g. on a published artifact.
// Exposes window.HPBackend.
(() => {
  // Engine URL: ?api=<url> wins; otherwise the host that served this page, port 8787 (works on localhost and LAN).
  const DEFAULT_API = (() => {
    try { const q = new URLSearchParams(location.search).get('api'); if (q) return q.replace(/\/$/, '');
      if (/^https?:$/.test(location.protocol) && location.hostname) return `${location.protocol}//${location.hostname}:8787`; } catch (_) {}
    return 'http://localhost:8787';
  })();
  const SNAP = './backend-snapshot/';

  const timeout = (ms) => new Promise((_, rej) => setTimeout(() => rej(new Error('timeout')), ms));
  async function getJSON(url, opts = {}, ms = 30000) {
    const r = await Promise.race([fetch(url, opts), timeout(ms)]);
    if (!r.ok) throw new Error(`${url} → ${r.status}`);
    return r.json();
  }
  const sortedIds = (a) => [...new Set(a)].map(Number).sort((x, y) => x - y);

  // Canonical edits payload (contract §POST /scenario) from page state.
  // treatments: Map/object edge id -> 'slow' | 'bike_lane' | 'road_diet'; closedRoads: freeway ramp edge ids.
  // Newer fields are only included when used, so older plans keep the same payload and cache key.
  function editsFrom({ ped = [], blocks = new Map(), policies = [], reopened = [], treatments = new Map(), closedRoads = [] } = {}) {
    const b = {};
    for (const [bid, e] of (blocks instanceof Map ? blocks : new Map(Object.entries(blocks)))) {
      const shops = e.shops ?? e.sh;
      b[String(bid)] = { scale: +(e.scale ?? e.s ?? 1), ...(e.zone ?? e.z ? { zone: e.zone ?? e.z } : {}), ...(shops ? { shops } : {}) };
    }
    const out = { pedestrianized: sortedIds([...ped]), blocks: b, policies, reopened: sortedIds(reopened) };
    const t = treatments instanceof Map ? [...treatments] : Object.entries(treatments || {});
    if (t.length) out.street_treatments = Object.fromEntries(t.map(([k, v]) => [String(k), v]).sort((x, y) => x[0] - y[0]));
    if (closedRoads.length) out.closed_roads = sortedIds(closedRoads);
    return out;
  }
  const sortKeys = (o) => o && typeof o === 'object' && !Array.isArray(o) ? Object.keys(o).sort().reduce((r, k) => (r[k] = sortKeys(o[k]), r), {}) : o;
  const normPolicy = (p) => ({ kind: p.kind, target: p.target ?? null, amount: +(p.amount ?? 0), params: sortKeys(p.params ?? null) });
  const editsKey = (e) => JSON.stringify({
    p: sortedIds(e.pedestrianized || []),
    b: Object.keys(e.blocks || {}).sort((x, y) => x - y).map(k => [String(k), +(e.blocks[k].scale ?? e.blocks[k].s ?? 1), e.blocks[k].zone ?? e.blocks[k].z ?? null,
      ...(e.blocks[k].shops ?? e.blocks[k].sh ? [e.blocks[k].shops ?? e.blocks[k].sh] : [])]),
    po: (e.policies || []).map(normPolicy).sort((x, y) => JSON.stringify(x) < JSON.stringify(y) ? -1 : 1),
    r: sortedIds(e.reopened || []),
    rm: e.reopen_mode || '',
    ...(Object.keys(e.street_treatments || {}).length ? { t: Object.entries(e.street_treatments).map(([k, v]) => [+k, v]).sort((x, y) => x[0] - y[0]) } : {}),
    ...(e.closed_roads?.length ? { c: sortedIds(e.closed_roads) } : {}),
  });
  // Union of two edit sets: an AI planner option is applied ON TOP of the current plan (b wins on conflicts).
  function mergeEdits(a = {}, b = {}) {
    const pol = new Map();
    for (const p of [...(a.policies || []), ...(b.policies || [])]) pol.set(p.kind + ':' + (p.target ?? ''), p);
    return {
      pedestrianized: sortedIds([...(a.pedestrianized || []), ...(b.pedestrianized || [])]),
      blocks: { ...(a.blocks || {}), ...(b.blocks || {}) },
      policies: [...pol.values()],
      reopened: sortedIds([...(a.reopened || []), ...(b.reopened || [])]),
      reopen_mode: b.reopen_mode || a.reopen_mode || '',
      street_treatments: { ...(a.street_treatments || {}), ...(b.street_treatments || {}) },
      closed_roads: sortedIds([...(a.closed_roads || []), ...(b.closed_roads || [])]),
    };
  }
  const isEmpty = (e) => !(e.pedestrianized?.length || Object.keys(e.blocks || {}).length || e.policies?.length || e.reopened?.length
    || Object.keys(e.street_treatments || {}).length || e.closed_roads?.length);

  // Trip geometry: contract "Rebuilding a trip polyline".
  // Returns { pts: [[x,z]...], segE: [edgeId per segment], cum: Float32Array, len }.
  function tripPolyline(trip, edges) {
    const pts = [], segE = [];
    for (const s of trip.steps) {
      const e = edges[s >> 1]; if (!e) continue;
      const p = (s & 1) ? e.p.slice().reverse() : e.p;
      for (let j = 0; j < p.length; j++) { if (pts.length && j === 0) continue; pts.push(p[j]); if (pts.length > 1) segE.push(s >> 1); }
    }
    let h = trip.trim_head || 0, t = trip.trim_tail || 0;
    while (h-- > 0 && pts.length > 2) { pts.shift(); segE.shift(); }
    while (t-- > 0 && pts.length > 2) { pts.pop(); segE.pop(); }
    const cum = new Float32Array(pts.length);
    for (let i = 1; i < pts.length; i++) cum[i] = cum[i - 1] + Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]);
    return { pts, segE, cum, len: cum[cum.length - 1] || 0 };
  }

  // Turns the result's trips into animatable objects. Live results carry every real trip (max_trips, share 1.0),
  // so copies defaults to 1. Thinner samples (the snapshot) are replayed a few times with a small, deterministic
  // time jitter; each copy keeps its real route.
  function expandTrips(result, edges, { copies, jitter = 420 } = {}) {
    const out = [];
    const items = result.trips?.items || [];
    const share = result.trips?.sample_share ?? 1;
    if (copies == null) copies = share >= 0.6 ? 1 : share >= 0.3 ? 2 : 3;
    for (let i = 0; i < items.length; i++) {
      const tr = items[i]; const geo = tripPolyline(tr, edges); if (geo.pts.length < 2 || geo.len < 1) continue;
      const dur = Math.max(30, tr.t_end - tr.t_start);
      for (let k = 0; k < copies; k++) {
        const u = ((i * 2654435761 + k * 40503) >>> 0) / 4294967296;
        const dt = k === 0 ? 0 : (u - 0.5) * 2 * jitter;
        out.push({ ...tr, ...geo, t0: tr.t_start + dt, t1: tr.t_end + dt, dur, v: geo.len / dur, copy: k, side: (u < 0.5 ? -1 : 1) });
      }
    }
    out.sort((a, b) => a.t0 - b.t0);
    return out;
  }

  // Cumulative inlet counts at time t (seconds), interpolating within the hour.
  function inletCountsAt(result, t) {
    const h = Math.max(0, Math.min(24, t / 3600)); const H = Math.floor(h), f = h - H;
    return (result.inlets || []).map(r => {
      let a = 0, b = 0;
      for (let i = 0; i < H && i < 24; i++) { a += r.entered_hour[i]; b += r.left_hour[i]; }
      if (H < 24) { a += r.entered_hour[H] * f; b += r.left_hour[H] * f; }
      return { i: r.i, entered: a, left: b };
    });
  }
  // People per hour on an edge at time t (seconds).
  const edgeHour = (arr, e, t) => { const row = arr?.[e]; if (!row) return 0; const h = Math.min(23, Math.max(0, Math.floor(t / 3600))); return row[h]; };

  async function connect({ api = DEFAULT_API, snapshot = SNAP, probeMs = 900, maxTrips = 100000 } = {}) {
    const q = `max_trips=${maxTrips}`;   // contract v0.3: 100000 returns every trip of the day (~52k)
    let mode = 'snapshot';
    const forceSnap = /[?&]snapshot\b/.test(location.search);   // ?snapshot: replay frozen results, no API or Claude calls
    if (!forceSnap) try { const h = await getJSON(api + '/health', {}, probeMs); if (h.ok && h.baseline_ready) mode = 'live'; } catch (_) { /* offline */ }
    const cache = new Map();
    let snap = null;
    if (mode === 'snapshot') {
      try { snap = await getJSON(snapshot + 'index.json', {}, 8000); } catch (_) { snap = null; }
      if (!snap) mode = 'offline';
    }
    const world = mode === 'live' ? await getJSON(api + '/world') : snap ? await getJSON(snapshot + snap.world) : null;
    const loadSnapResult = async (id) => { const f = snap?.results?.[id]; return f ? getJSON(snapshot + f) : null; };
    const baseline = mode === 'live' ? await getJSON(`${api}/baseline?${q}`) : await loadSnapResult('baseline');
    if (baseline) cache.set(editsKey(editsFrom()), baseline);
    if (snap) for (const [id, meta] of Object.entries(snap.results || {})) if (id !== 'baseline' && snap.edits?.[id]) cache.set(editsKey(snap.edits[id]), { lazy: id });

    async function resolve(v) { if (v && v.lazy) { const r = await loadSnapResult(v.lazy); return r; } return v; }

    // Run a plan. onProgress({day, days, label}) streams replanning days in live mode.
    async function scenario(edits, { onProgress, name = 'Plan A' } = {}) {
      const key = editsKey(edits);
      if (isEmpty(edits)) return baseline;
      if (cache.has(key)) { const r = await resolve(cache.get(key)); if (r) { cache.set(key, r); return r; } }
      if (mode !== 'live') return null;   // caller falls back to its local estimate
      const res = await fetch(`${api}/scenario?stream=1&${q}`, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ name, edits }) });
      const reader = res.body.getReader(); const dec = new TextDecoder(); let buf = '', result = null;
      for (;;) {
        const { value, done } = await reader.read(); if (done) break; buf += dec.decode(value, { stream: true });
        let i; while ((i = buf.indexOf('\n\n')) >= 0) {
          const msg = buf.slice(0, i); buf = buf.slice(i + 2);
          const ev = /event: (\w+)/.exec(msg)?.[1]; const d = /data: (.*)/s.exec(msg)?.[1]; if (!d) continue;
          const data = JSON.parse(d);
          if (ev === 'progress') onProgress?.(data); else if (ev === 'result') result = data;
        }
      }
      if (result) cache.set(key, result);
      return result;
    }
    async function getScenario(id) {
      if (id === 'baseline') return baseline;
      if (mode === 'live') return getJSON(`${api}/scenario/${id}?${q}`);
      return loadSnapResult(id);
    }
    async function agent(sid, aid) {
      if (mode === 'live') return getJSON(`${api}/scenario/${sid}/agent/${aid}`);
      const f = snap?.agents?.[`${sid}:${aid}`]; return f ? getJSON(snapshot + f) : null;
    }
    const post = (path, body, ms = 60000) => getJSON(api + path, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(body) }, ms);
    const narrative = {
      explain: (sid, question) => mode === 'live' ? post('/narrative/explain', { scenario: sid, question }) : Promise.resolve(snap?.narrative?.explain?.[sid] || null),
      diary: (sid, agent_id) => mode === 'live' ? post('/narrative/diary', { scenario: sid, agent_id }) : Promise.resolve(snap?.narrative?.diary?.[`${sid}:${agent_id}`] || null),
      posts: (sid, n = 6) => mode === 'live' ? post('/narrative/posts', { scenario: sid, n }) : Promise.resolve(snap?.narrative?.posts?.[sid] || null),
      planner: (goal) => mode === 'live' ? post('/narrative/planner', { goal }, 90000) : Promise.resolve(snap?.narrative?.planner || null),
    };
    return { mode, api, world, baseline, hero: world?.hero, scenario, getScenario, agent, narrative, editsFrom, editsKey, mergeEdits };
  }

  // Inlets are a variable-length list from GET /world (contract v0.4): never assume ids 0-7 or an order.
  // mergeInlets appends every engine inlet the page doesn't know yet to its own list, keeping position == i, and
  // marks which ones get a map marker: the page's own ones plus the busiest generated car inlets of the baseline.
  // Returns toy[engineI] -> page index, for copying engine counts into per-inlet arrays.
  function mergeInlets(list, world, baseline, { maxExtra = 12, minShare = 0.04 } = {}) {
    const toy = [];
    if (!world || !world.inlets) return { toy, extra: [] };
    const vol = new Map((baseline?.inlets || []).map(r => [r.i, (r.entered || 0) + (r.left || 0)]));
    const cars = world.inlets.filter(g => g.mode === 'car');
    const top = Math.max(1, ...cars.map(g => vol.get(g.i) || 0));
    const busy = cars.filter(g => !g.legacy && (vol.get(g.i) || 0) >= minShare * top)
      .sort((a, b) => (vol.get(b.i) || 0) - (vol.get(a.i) || 0)).slice(0, maxExtra).map(g => g.key);
    const extra = [];
    for (const e of world.inlets) {
      let g = list.find(x => x.key === e.key);
      if (!g) {
        const at = e.at || [e.x, e.z];
        g = { key: e.key, name: e.name, short: e.name, mode: e.mode, i: list.length, pos: [at[0], at[1]], side: e.side, cls: e.cls,
              entries: [], exits: [], engine: true, marker: busy.includes(e.key) };
        list.push(g); extra.push(g);
      }
      g.ei = e.i; toy[e.i] = g.i;
    }
    return { toy, extra };
  }
  const inletByKey = (world, key) => (world?.inlets || []).find(g => g.key === key) || null;

  window.HPBackend = { connect, editsFrom, editsKey, mergeEdits, isEmpty, tripPolyline, expandTrips, inletCountsAt, edgeHour, mergeInlets, inletByKey };
})();
