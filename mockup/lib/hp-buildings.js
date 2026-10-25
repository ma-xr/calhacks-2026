// CommonGround · recognizable San Francisco buildings.
// Inlined at build time (scripts/build_mockup.py replaces /*__HP_BUILDINGS__*/) with
// data/processed/buildings_detail.json (OSM building:part, roof shapes, colours, materials).
//
// window.HPBuildings.geometry(THREE, building, index) -> non-indexed BufferGeometry (position, normal, aCrown)
//   - OSM building parts with real tier heights and roof shapes (pyramidal, dome, gabled, mansard...)
//   - hand-built landmarks where OSM is too coarse: Transamerica Pyramid, Salesforce Tower, 181 Fremont
//   - generic detail: crown setbacks on tall towers, rooftop mechanical boxes on mid-rises
//   aCrown = 1 marks crown/spire faces a page may light at night.
// window.HPBuildings.style(building, index) -> { col: [r,g,b] | null, glass: true|false|null }
// Geometry stays in the world.json frame and grows from y=0, so a page's per-building height scaling still works.
(() => {
  const DATA = /*__HP_BUILDINGS_DATA__*/null;
  const PARTS = DATA?.parts || {}, TAGS = DATA?.tags || {};

  const hex = (h) => h ? [1, 3, 5].map(i => Math.pow(parseInt(h.slice(i, i + 2), 16) / 255, 2.2)) : null;
  const hash = (a, b) => { let h = Math.imul(a + 0x9e3779b9, 0x85ebca6b) ^ Math.imul(b + 0x7f4a7c15, 0xc2b2ae35); h ^= h >>> 13; h = Math.imul(h, 0x27d4eb2f); h ^= h >>> 16; return (h >>> 0) / 4294967296; };

  // Landmark looks (linear-ish RGB) and materials.
  const LOOK = {
    'Transamerica Pyramid': { col: [0.93, 0.92, 0.88], glass: false },
    'Salesforce Tower': { col: [0.78, 0.81, 0.84], glass: true },
    '181 Fremont Tower': { col: [0.62, 0.69, 0.76], glass: true },
    'Millennium Tower': { col: [0.58, 0.68, 0.76], glass: true },
    '555 California Street': { col: [0.30, 0.17, 0.15], glass: false },        // carnelian granite
    'San Francisco Ferry Building': { col: [0.93, 0.89, 0.80], glass: false },
    'Russ Building': { col: [0.86, 0.78, 0.64], glass: false },
    'Hallidie Building': { col: [0.45, 0.62, 0.74], glass: true },
    'San Francisco Museum of Modern Art': { col: [0.70, 0.44, 0.34], glass: false },
    'Embarcadero Center 1': { col: [0.86, 0.85, 0.82], glass: false }, 'Embarcadero Center 2': { col: [0.86, 0.85, 0.82], glass: false },
    'Embarcadero Center 3': { col: [0.86, 0.85, 0.82], glass: false }, 'Embarcadero Center 4': { col: [0.86, 0.85, 0.82], glass: false },
    'California Center': { col: [0.82, 0.74, 0.62], glass: false },
    'Park Tower at Transbay': { col: [0.52, 0.64, 0.73], glass: true },
  };
  const MAT = { glass: { glass: true, col: null }, brick: { glass: false, col: [0.55, 0.27, 0.19] }, concrete: { glass: false, col: [0.74, 0.73, 0.70] },
    stone: { glass: false, col: [0.82, 0.76, 0.64] }, metal: { glass: true, col: [0.70, 0.73, 0.76] }, plaster: { glass: false, col: [0.90, 0.86, 0.78] } };

  // The hand-built landmarks and colours are San Francisco's. Other cities can share names (NYC has its own
  // "Salesforce Tower"), so they apply only on the SF page (read from the page's #city config, default SF).
  let SF_ONLY = null;
  const isSF = () => { if (SF_ONLY === null) { try { SF_ONLY = JSON.parse(document.getElementById('city').textContent).id === 'sf'; } catch (_) { SF_ONLY = true; } } return SF_ONLY; };

  function style(b, i) {
    const look = isSF() ? LOOK[b.n] : null; if (look) return look;
    const parts = PARTS[i]; const t = TAGS[i] || (parts && parts[0]) || {};
    const m = MAT[t.mat]; const c = hex(t.col);
    if (m || c) return { col: c || m?.col || null, glass: m ? m.glass : null };
    return { col: null, glass: null };
  }

  // ---- geometry helpers -------------------------------------------------------------------
  function area2(P) { let a = 0; for (let i = 0; i < P.length; i++) { const [x1, z1] = P[i], [x2, z2] = P[(i + 1) % P.length]; a += x1 * z2 - x2 * z1; } return a; }
  function centroid(P) { let x = 0, z = 0; for (const p of P) { x += p[0]; z += p[1]; } return [x / P.length, z / P.length]; }
  function obb(P) {
    let best = 0, ang = 0;
    for (let i = 0; i < P.length; i++) { const [x1, z1] = P[i], [x2, z2] = P[(i + 1) % P.length]; const L = Math.hypot(x2 - x1, z2 - z1); if (L > best) { best = L; ang = Math.atan2(z2 - z1, x2 - x1); } }
    const c = centroid(P), ux = [Math.cos(ang), Math.sin(ang)], uz = [-ux[1], ux[0]]; let hx = 0, hz = 0;
    for (const p of P) { const dx = p[0] - c[0], dz = p[1] - c[1]; hx = Math.max(hx, Math.abs(dx * ux[0] + dz * ux[1])); hz = Math.max(hz, Math.abs(dx * uz[0] + dz * uz[1])); }
    return { c, ux, uz, hx, hz };
  }

  class Mesh {
    constructor() { this.pos = []; this.crown = []; }
    tri(a, b, c, want, crown = 0) {   // want: [nx, ny, nz] outward hint; flips winding to face it
      const ux = b[0] - a[0], uy = b[1] - a[1], uz = b[2] - a[2], vx = c[0] - a[0], vy = c[1] - a[1], vz = c[2] - a[2];
      const nx = uy * vz - uz * vy, ny = uz * vx - ux * vz, nz = ux * vy - uy * vx;
      if (nx * want[0] + ny * want[1] + nz * want[2] < 0) [b, c] = [c, b];
      this.pos.push(...a, ...b, ...c); this.crown.push(crown, crown, crown);
    }
    // Walls from y0 (polygon P0) to y1 (polygon P1, same vertex count) plus an optional flat cap on P1.
    band(P0, y0, P1, y1, cap, crown = 0) {
      const s = Math.sign(area2(P0)) || 1;
      for (let i = 0; i < P0.length; i++) {
        const j = (i + 1) % P0.length; const [x1, z1] = P0[i], [x2, z2] = P0[j];
        const out = [s * (z2 - z1), 0, -s * (x2 - x1)];
        const a = [x1, y0, z1], b = [x2, y0, z2], c = [P1[j][0], y1, P1[j][1]], d = [P1[i][0], y1, P1[i][1]];
        this.tri(a, b, c, out, crown); this.tri(a, c, d, out, crown);
      }
      if (cap) this.cap(P1, y1, crown);
    }
    cap(P, y, crown = 0) {
      let tris = null; try { tris = THREE_.ShapeUtils.triangulateShape(P.map(p => new THREE_.Vector2(p[0], p[1])), []); } catch (_) { tris = null; }
      if (!tris || !tris.length) {   // triangulation failed (self-touching outline): close the roof with a fan rather than leave it open
        const c = centroid(P); for (let i = 0; i < P.length; i++) { const j = (i + 1) % P.length; this.tri([c[0], y, c[1]], [P[i][0], y, P[i][1]], [P[j][0], y, P[j][1]], [0, 1, 0], crown); }
        return;
      }
      for (const [a, b, c] of tris) this.tri([P[a][0], y, P[a][1]], [P[b][0], y, P[b][1]], [P[c][0], y, P[c][1]], [0, 1, 0], crown);
    }
    apex(P, y0, top, crown = 0) {   // pyramid from polygon at y0 to a single point
      const s = Math.sign(area2(P)) || 1;
      for (let i = 0; i < P.length; i++) { const j = (i + 1) % P.length; const [x1, z1] = P[i], [x2, z2] = P[j]; this.tri([x1, y0, z1], [x2, y0, z2], top, [s * (z2 - z1), 0.4, -s * (x2 - x1)], crown); }
    }
    // A prism with an OSM-style roof on top.
    prism(P, y0, y1, roof, rh, crown = 0) {
      if (P.length < 3 || y1 <= y0 + 0.2) return;
      if (y0 > 0.5) this.cap(P, y0, 0);                                 // underside of floating parts (seen from below rarely)
      const c = centroid(P); const r = roof || 'flat';
      const h = Math.max(0, Math.min(rh ?? (r === 'flat' || r === 'skillion' ? 0 : Math.min(12, (y1 - y0) * 0.35)), y1 - y0));
      const wallTop = y1 - h;
      this.band(P, y0, P, wallTop, r === 'flat' || r === 'skillion' || h < 0.3, crown);
      if (h < 0.3 || r === 'flat' || r === 'skillion') return;
      if (r === 'pyramidal' || r === 'hipped' || r === 'gabled' || r === 'quadruple_saltbox') {
        if (r === 'pyramidal') { this.apex(P, wallTop, [c[0], y1, c[1]], crown); return; }
        const o = obb(P); const k = r === 'gabled' ? 0.0 : 0.25;   // ridge along the long axis
        const T = P.map(([x, z]) => { const dx = x - o.c[0], dz = z - o.c[1]; const a = dx * o.ux[0] + dz * o.ux[1], b = dx * o.uz[0] + dz * o.uz[1];
          const a2 = a * (r === 'gabled' ? 1 : 0.6), b2 = b * k; return [o.c[0] + o.ux[0] * a2 + o.uz[0] * b2, o.c[1] + o.ux[1] * a2 + o.uz[1] * b2]; });
        this.band(P, wallTop, T, y1, true, crown); return;
      }
      if (r === 'dome' || r === 'round' || r === 'onion') {
        let prev = P, py = wallTop; const N = 4;
        for (let k = 1; k <= N; k++) { const t = k / N; const s = Math.cos(t * Math.PI / 2); const y = wallTop + h * Math.sin(t * Math.PI / 2);
          const Q = P.map(([x, z]) => [c[0] + (x - c[0]) * Math.max(s, 0.04), c[1] + (z - c[1]) * Math.max(s, 0.04)]); this.band(prev, py, Q, y, k === N, crown); prev = Q; py = y; }
        return;
      }
      if (r === 'mansard') { const Q = P.map(([x, z]) => [c[0] + (x - c[0]) * 0.8, c[1] + (z - c[1]) * 0.8]); this.band(P, wallTop, Q, y1, true, crown); return; }
      this.cap(P, wallTop, crown);
    }
    geometry() {
      const g = new THREE_.BufferGeometry();
      g.setAttribute('position', new THREE_.Float32BufferAttribute(this.pos, 3));
      g.setAttribute('aCrown', new THREE_.Float32BufferAttribute(this.crown, 1));
      g.computeVertexNormals();
      return g;
    }
  }
  let THREE_ = null;
  const rectAt = (o, hx, hz, scale = 1) => [[-1, -1], [1, -1], [1, 1], [-1, 1]].map(([a, b]) => [o.c[0] + (o.ux[0] * a * hx + o.uz[0] * b * hz) * scale, o.c[1] + (o.ux[1] * a * hx + o.uz[1] * b * hz) * scale]);
  const ring = (c, r, n, k = 0) => Array.from({ length: n }, (_, i) => { const t = (i / n) * Math.PI * 2 + k; return [c[0] + Math.cos(t) * r, c[1] + Math.sin(t) * r]; });
  // Squircle: rounded square, like Salesforce Tower's plan.
  const squircle = (o, r, n = 24) => Array.from({ length: n }, (_, i) => { const t = (i / n) * Math.PI * 2; const ct = Math.cos(t), st = Math.sin(t);
    const a = Math.sign(ct) * Math.pow(Math.abs(ct), 0.5) * r, b = Math.sign(st) * Math.pow(Math.abs(st), 0.5) * r;
    return [o.c[0] + o.ux[0] * a + o.uz[0] * b, o.c[1] + o.ux[1] * a + o.uz[1] * b]; });

  // ---- landmarks ----------------------------------------------------------------------------
  const LANDMARKS = {
    'Transamerica Pyramid'(m, b) {
      const o = obb(b.p); const H = 212, base = Math.min(Math.max(o.hx, o.hz), 30);
      const half = (y) => base - (base - 4.2) * (y / H);
      m.band(rectAt(o, base, base), 0, rectAt(o, half(H), half(H)), H, false);
      m.band(rectAt(o, half(H), half(H)), H, rectAt(o, 0.9, 0.9), 258, false, 1);          // spire
      m.apex(rectAt(o, 0.9, 0.9), 258, [o.c[0], 260, o.c[1]], 1);
      // Elevator (east) and stair/smoke (west) wings riding up the faces past the body.
      for (const side of [-1, 1]) {
        const y0 = 70, y1 = 232; const w = 5.5;
        const P0 = [[half(y0) - 3, -w], [half(y0) + 4, -w], [half(y0) + 4, w], [half(y0) - 3, w]];
        const P1 = [[half(H) - 1, -w * 0.8], [half(H) + 4, -w * 0.8], [half(H) + 4, w * 0.8], [half(H) - 1, w * 0.8]];
        const map = (P) => P.map(([a, bb]) => [o.c[0] + o.ux[0] * a * side + o.uz[0] * bb, o.c[1] + o.ux[1] * a * side + o.uz[1] * bb]);
        m.band(map(P0), y0, map(P1), y1, true);
      }
    },
    'Salesforce Tower'(m, b) {
      const o = obb(b.p); const r0 = Math.min(Math.max(o.hx, o.hz), 28);
      const levels = [[0, 1], [270, 0.86], [298, 0.80]];
      for (let k = 0; k < levels.length - 1; k++) m.band(squircle(o, r0 * levels[k][1]), levels[k][0], squircle(o, r0 * levels[k + 1][1]), levels[k + 1][0], false);
      // Open lattice crown, then the rounded top.
      const crown = [[298, 0.80], [312, 0.70], [321, 0.52], [325, 0.28], [326, 0.05]];
      for (let k = 0; k < crown.length - 1; k++) m.band(squircle(o, r0 * crown[k][1]), crown[k][0], squircle(o, r0 * crown[k + 1][1]), crown[k + 1][0], k === crown.length - 2, 1);
    },
    '181 Fremont Tower'(m, b) {
      const o = obb(b.p); const hx = Math.min(o.hx, 19), hz = Math.min(o.hz, 19);
      m.band(rectAt(o, hx, hz), 0, rectAt(o, hx * 0.86, hz * 0.86), 205, false);
      // Sloped faceted top, then the spire.
      const T = rectAt(o, hx * 0.86, hz * 0.86); const ridge = rectAt(o, hx * 0.15, hz * 0.6);
      m.band(T, 205, ridge, 228, true, 1);
      m.band(ring(o.c, 1.4, 6), 228, ring(o.c, 0.4, 6), 244, true, 1);
    },
  };

  function geometry(THREE, b, i) {
    THREE_ = THREE; const m = new Mesh();
    const lm = isSF() ? LANDMARKS[b.n] : null;
    if (lm) { lm(m, b); return m.geometry(); }
    const parts = PARTS[i];
    if (parts && parts.length) {
      const polys = parts.map(pt => { const P = []; for (let k = 0; k < pt.p.length; k += 2) P.push([pt.p[k], pt.p[k + 1]]); return P; });
      polys.forEach((P, k) => m.prism(P, parts[k].mh || 0, parts[k].h, parts[k].roof, parts[k].rh));
      // Many OSM buildings map only some parts (e.g. a one-storey ground floor). Trust the parts alone only when
      // they reach the building's height and cover most of its footprint; otherwise keep the full body too.
      const foot = Math.abs(area2(b.p)) / 2, covered = polys.reduce((a, P) => a + Math.abs(area2(P)) / 2, 0);
      const tallest = Math.max(...parts.map(p => p.h));
      const complete = tallest >= b.h * 0.85 && covered >= foot * 0.7;
      const top = Math.min(...parts.map(p => p.h));
      m.prism(b.p, 0, complete ? Math.min(b.h, Math.max(4, top * 0.999)) : b.h, 'flat');
      return m.geometry();
    }
    const t = TAGS[i]; const P = b.p; const h = b.h;
    if (t?.roof && t.roof !== 'flat') { m.prism(P, 0, h, t.roof, t.rh); return m.geometry(); }
    const c = centroid(P); const r = hash(i, 11);
    if (h >= 110) {
      // Tall towers: a crown setback and a mechanical penthouse.
      const sh = h * 0.93; const Q = P.map(([x, z]) => [c[0] + (x - c[0]) * 0.84, c[1] + (z - c[1]) * 0.84]);
      m.prism(P, 0, sh, 'flat'); m.prism(Q, sh, h, 'flat', 0, 0);   // generic crowns don't glow: only landmark crowns do
      const Rr = P.map(([x, z]) => [c[0] + (x - c[0]) * 0.36, c[1] + (z - c[1]) * 0.36]); m.prism(Rr, h, h + 6, 'flat', 0, 0);
      return m.geometry();
    }
    m.prism(P, 0, h, 'flat');
    if (h >= 20 && r < 0.55) {   // rooftop mechanical box / water tank
      const o = obb(P); const s = 0.28 + hash(i, 12) * 0.12;
      m.prism(rectAt(o, Math.min(o.hx, 18) * s / 0.5 * 0.5, Math.min(o.hz, 18) * s / 0.5 * 0.5), h, h + 3 + hash(i, 13) * 3, 'flat');
    }
    return m.geometry();
  }

  window.HPBuildings = { geometry, style, data: DATA, landmarks: Object.keys(LANDMARKS) };
})();
