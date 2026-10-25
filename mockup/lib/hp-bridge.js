// CommonGround · San Francisco–Oakland Bay Bridge, west span (decorative model).
// Inlined at build time via /*__HP_LIB:hp-bridge__*/. window.HPBridge.add(THREE, scene, { a: [x, z], b: [x, z] })
// builds it between the SF shore (a) and Yerba Buena Island (b) in world.json meters and returns
// { group, yAt(x, z), setNight(n) }: yAt gives the upper-deck height for cars driving on it (0 off the bridge).
//
// Real layout, simplified: two back-to-back suspension bridges joined at a concrete center anchorage,
// four steel towers (~160 m above the water), a double deck at ~58 m, catenary main cables with hangers,
// and the Bay Lights (white LEDs along the cables) at night.
(() => {
  function add(THREE, scene, opt = {}) {
    const [ax, az] = opt.a, [bx, bz] = opt.b;
    const L = Math.hypot(bx - ax, bz - az), ux = (bx - ax) / L, uz = (bz - az) / L, nx = -uz, nz = ux;
    const ang = Math.atan2(-uz, ux);
    const group = new THREE.Group(); group.name = 'bay-bridge'; scene.add(group);
    const steel = new THREE.MeshStandardMaterial({ color: opt.color ?? 0xc9cfd5, roughness: 0.55, metalness: 0.12 });   // silver-grey; low metalness so it isn't black without an env map
    const concrete = new THREE.MeshStandardMaterial({ color: 0xc9c3b6, roughness: 0.9 });
    const deckMat = new THREE.MeshStandardMaterial({ color: 0x9fa5ab, roughness: 0.75, metalness: 0.1 });
    const at = (t, lat = 0) => [ax + ux * L * t + nx * lat, az + uz * L * t + nz * lat];
    const DECK = 58, LOWER = 47, TOWER = 160, HALF = 13;
    const deckY = (t) => 25 + (DECK - 25) * Math.min(1, Math.max(0, t / 0.1)) ** 0.7;
    // A box aligned with the bridge: from t0 to t1 along it, centered at `lat`, between heights y0 and y1.
    function box(t0, t1, lat, w, y0, y1, mat) {
      const len = Math.max(0.5, (t1 - t0) * L);
      const m = new THREE.Mesh(new THREE.BoxGeometry(len, y1 - y0, w), mat);
      const [cx, cz] = at((t0 + t1) / 2, lat);
      m.position.set(cx, (y0 + y1) / 2, cz); m.rotation.y = ang; m.castShadow = true; group.add(m); return m;
    }
    // Decks (upper + lower) and the side trusses between them, in short pieces so the approach can rise.
    const N = 40;
    for (let i = 0; i < N; i++) {
      const t0 = i / N, t1 = (i + 1) / N, y = deckY((t0 + t1) / 2);
      box(t0, t1, 0, 24, y - 1.5, y + 1.0, deckMat);
      box(t0, t1, 0, 22, y - (DECK - LOWER) - 1.2, y - (DECK - LOWER) + 0.8, deckMat);
      for (const s of [-1, 1]) box(t0, t1, s * 11.6, 0.9, y - (DECK - LOWER), y, steel);
    }
    // Towers: two legs with cross beams, on concrete piers.
    const towers = [0.14, 0.38, 0.62, 0.86];
    for (const t of towers) {
      for (const s of [-1, 1]) box(t - 0.0025, t + 0.0025, s * HALF, 6, 0, TOWER, steel);
      for (const y of [LOWER - 8, 95, 128, TOWER - 6]) box(t - 0.002, t + 0.002, 0, HALF * 2 + 6, y, y + 5, steel);
      box(t - 0.008, t + 0.008, 0, 44, -2, 9, concrete);
    }
    // Center anchorage and the shore / island anchorages.
    box(0.485, 0.515, 0, 42, -2, 72, concrete);
    box(0.0, 0.02, 0, 34, -2, 40, concrete);
    box(0.975, 1.0, 0, 34, -2, 62, concrete);
    // Main cables: anchorage -> tower -> tower -> anchorage, for each of the two suspension units, both sides.
    const units = [[0.02, 0.14, 0.38, 0.485], [0.515, 0.62, 0.86, 0.975]];
    const cablePts = [];
    function cableY(t, u) {
      const [a0, t1, t2, a1] = u; const anchorY = 66, top = TOWER - 3, mid = DECK + 7;
      if (t <= t1) { const k = (t - a0) / (t1 - a0); return anchorY + (top - anchorY) * k - 18 * k * (1 - k); }
      if (t <= t2) { const k = (t - t1) / (t2 - t1); return top - 4 * (top - mid) * k * (1 - k); }
      const k = (t - t2) / (a1 - t2); return top + (anchorY - top) * k - 18 * k * (1 - k);
    }
    const cableMat = new THREE.MeshStandardMaterial({ color: 0xc2c8ce, roughness: 0.5, metalness: 0.15 });
    const hangers = [];
    for (const u of units) for (const s of [-1, 1]) {
      const pts = [];
      for (let k = 0; k <= 120; k++) { const t = u[0] + (u[3] - u[0]) * k / 120; const [x, z] = at(t, s * HALF); pts.push(new THREE.Vector3(x, cableY(t, u), z)); }
      const tube = new THREE.Mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts), 240, 1.1, 5, false), cableMat); group.add(tube);
      cablePts.push(pts);
      for (let d = 0; d <= (u[3] - u[0]) * L; d += 22) {
        const t = u[0] + d / L; const y = cableY(t, u), dy = deckY(t) + 1; if (y - dy < 2) continue;
        const [x, z] = at(t, s * HALF); hangers.push(x, y, z, x, dy, z);
      }
    }
    const hg = new THREE.BufferGeometry(); hg.setAttribute('position', new THREE.Float32BufferAttribute(hangers, 3));
    group.add(new THREE.LineSegments(hg, new THREE.LineBasicMaterial({ color: 0x9aa1a8, transparent: true, opacity: 0.55 })));
    // The Bay Lights: white LEDs along the cables, visible at night.
    const lp = []; for (const pts of cablePts) for (let i = 0; i < pts.length; i += 1) lp.push(pts[i].x, pts[i].y + 0.5, pts[i].z);
    const lg = new THREE.BufferGeometry(); lg.setAttribute('position', new THREE.Float32BufferAttribute(lp, 3));
    const lightMat = new THREE.PointsMaterial({ color: new THREE.Color(2.6, 2.6, 2.8), size: 10, sizeAttenuation: true, transparent: true, opacity: 0, depthWrite: false, toneMapped: false });
    const lights = new THREE.Points(lg, lightMat); group.add(lights);

    function yAt(x, z) {
      const dx = x - ax, dz = z - az, t = (dx * ux + dz * uz) / L, lat = Math.abs(dx * nx + dz * nz);
      if (t < 0.0 || t > 1.02 || lat > 30) return 0;
      return deckY(Math.min(1, t)) + 1.2;
    }
    return { group, yAt, length: L, setNight(n) { lightMat.opacity = Math.min(1, Math.max(0, n * 1.2)); lights.visible = n > 0.05; } };
  }
  window.HPBridge = { add };
})();
