// The Human Project · faded San Francisco context around the simulation area.
// Inlined at build time (scripts/build_mockup.py replaces /*__HP_CONTEXT__*/), with the data from
// data/processed/context.json. Exposes window.HPContext.add(THREE, scene, options).
//
// What it draws, all in the world.json meter frame:
//  - the surrounding city (OSM buildings, streets, parks, coastline), sinking and blending into a haze
//    with distance from the simulation box, so the map continues instead of stopping
//  - a clear dashed boundary with a soft glow around the simulated blocks
//  - the main entry roads (freeways, feeders) highlighted with flowing dashes far beyond the edge
(() => {
  const DATA = /*__HP_CONTEXT_DATA__*/null;

  const GLSL_BOX = `
    uniform vec4 uBox;      // x0, z0, x1, z1 of the simulation area
    uniform vec2 uFade;     // fade start, fade end (meters outside the box)
    float boxDist(vec2 p) {
      vec2 c = (uBox.xy + uBox.zw) * 0.5, h = (uBox.zw - uBox.xy) * 0.5;
      vec2 d = abs(p - c) - h;
      return length(max(d, 0.0)) + min(max(d.x, d.y), 0.0);
    }
    float fadeAt(vec2 p) { return smoothstep(uFade.x, uFade.y, boxDist(p)); }`;

  function add(THREE, scene, opt = {}) {
    if (!DATA) return null;
    const box = DATA.simBox;
    const o = {
      fadeStart: 0, fadeEnd: 1700,
      fadeColor: 0xdfe6ec, buildingColor: 0xd6d3cc, roadColor: 0xa9adb3, landColor: 0xcdc8bf, parkColor: 0xa9c29a, waterColor: 0x9cc3da,
      accent: 0x39d5ff, outline: 0xffffff,
      inside: false,   // true: also draw the real land / water / parks inside the simulation box (cities without a hand-made shoreline)
      inletRoads: ['Market Street', 'Mission Street', 'Folsom Street', 'Howard Street', 'Harrison Street', 'Bryant Street', 'Broadway',
        'Columbus Avenue', 'The Embarcadero', 'King Street', '3rd Street', '4th Street', '5th Street', 'Fremont Street', 'Van Ness Avenue', 'Franklin Street', 'Gough Street', 'Octavia Boulevard'],
      ...opt,
    };
    const group = new THREE.Group(); group.name = 'hp-context'; scene.add(group);
    const U = {
      uBox: { value: new THREE.Vector4(box.x0, box.z0, box.x1, box.z1) },
      uFade: { value: new THREE.Vector2(o.fadeStart, o.fadeEnd) },
      uFadeColor: { value: new THREE.Color(o.fadeColor) },
      uTime: { value: 0 },
    };
    const col = (c) => new THREE.Color(c);

    // Haze over everything outside the box: the ground, water and the edges of the sim's own roads dissolve into it.
    const haze = new THREE.Mesh(new THREE.PlaneGeometry(16000, 16000).rotateX(-Math.PI / 2), new THREE.ShaderMaterial({
      transparent: true, depthWrite: false, fog: false,
      uniforms: { ...U },
      vertexShader: 'varying vec2 vP; void main(){ vec4 w = modelMatrix*vec4(position,1.0); vP = w.xz; gl_Position = projectionMatrix*viewMatrix*w; }',
      fragmentShader: GLSL_BOX + 'uniform vec3 uFadeColor; varying vec2 vP; void main(){ float f = fadeAt(vP); gl_FragColor = vec4(uFadeColor, f); }',
    }));
    haze.position.y = 1.6; haze.renderOrder = 5; group.add(haze);

    // Masked flat layers (land, water, parks) that only show outside the box, under the haze.
    const flatMat = (c) => new THREE.ShaderMaterial({
      transparent: true, depthWrite: false, fog: false, side: THREE.DoubleSide,
      uniforms: { ...U, uCol: { value: col(c) }, uInside: { value: o.inside ? 1 : 0 } },
      vertexShader: 'varying vec2 vP; void main(){ vec4 w = modelMatrix*vec4(position,1.0); vP = w.xz; gl_Position = projectionMatrix*viewMatrix*w; }',
      fragmentShader: GLSL_BOX + 'uniform vec3 uCol; uniform float uInside; varying vec2 vP; void main(){ float d = boxDist(vP); float a = max(uInside, smoothstep(0.0, 90.0, d)); if (a <= 0.0) discard; gl_FragColor = vec4(uCol, a); }',
    });
    const polyMesh = (flatPolys, c, y, holes) => {
      const shapes = flatPolys.map(f => { const s = new THREE.Shape(); for (let i = 0; i < f.length; i += 2) (i ? s.lineTo(f[i], -f[i + 1]) : s.moveTo(f[i], -f[i + 1])); return s; });
      if (holes) for (const s of shapes) s.holes = holes;
      const m = new THREE.Mesh(new THREE.ShapeGeometry(shapes).rotateX(-Math.PI / 2), flatMat(c)); m.position.y = y; m.renderOrder = 1; group.add(m); return m;
    };
    const mats = {};
    if (DATA.land?.length) {
      // Real coastline: water everywhere outside the box except the land polygons (cut out as holes), then the land itself.
      const holes = DATA.land.map(f => { const h = new THREE.Path(); for (let i = 0; i < f.length; i += 2) (i ? h.lineTo(f[i], -f[i + 1]) : h.moveTo(f[i], -f[i + 1])); return h; });
      mats.water = polyMesh([[-7000, -7000, 7000, -7000, 7000, 7000, -7000, 7000]], o.waterColor, 0.1, holes).material;
      mats.land = polyMesh(DATA.land, o.landColor, 0.12).material;
    }
    if (DATA.parks?.length) { mats.park = polyMesh(DATA.parks, o.parkColor, 0.2).material; }
    if (DATA.water?.length) { const m = polyMesh(DATA.water, o.waterColor, 0.16); if (!mats.water) mats.water = m.material; }   // rivers / lakes, with or without a coastline

    // Streets outside the box: flat ribbons under the haze.
    const W = [16, 13, 12, 10, 8, 7, 5];
    const roadPos = [], hiPos = [], hiAlong = [];
    const hiNames = new Set(o.inletRoads);
    for (const r of DATA.roads) {
      const cls = r[0], name = DATA.names[r[1]], w = W[cls] || 7; const pts = [];
      for (let i = 2; i < r.length; i += 2) pts.push([r[i], r[i + 1]]);
      let along = 0;
      for (let i = 0; i < pts.length - 1; i++) {
        const [x1, z1] = pts[i], [x2, z2] = pts[i + 1]; const L = Math.hypot(x2 - x1, z2 - z1) || 1; const nx = -(z2 - z1) / L * w / 2, nz = (x2 - x1) / L * w / 2;
        roadPos.push(x1 + nx, 0.3, z1 + nz, x2 + nx, 0.3, z2 + nz, x1 - nx, 0.3, z1 - nz, x1 - nx, 0.3, z1 - nz, x2 + nx, 0.3, z2 + nz, x2 - nx, 0.3, z2 - nz);
        if (cls <= 1 || hiNames.has(name)) {
          const k = cls <= 1 ? 0.55 : 0.4, hx = nx * k, hz = nz * k;
          hiPos.push(x1 + hx, 1.9, z1 + hz, x2 + hx, 1.9, z2 + hz, x1 - hx, 1.9, z1 - hz, x1 - hx, 1.9, z1 - hz, x2 + hx, 1.9, z2 + hz, x2 - hx, 1.9, z2 - hz);
          hiAlong.push(along, along + L, along, along, along + L, along + L);
        }
        along += L;
      }
    }
    const roadGeo = new THREE.BufferGeometry(); roadGeo.setAttribute('position', new THREE.Float32BufferAttribute(roadPos, 3));
    const roadMat = new THREE.MeshBasicMaterial({ color: o.roadColor, side: THREE.DoubleSide });
    const roads = new THREE.Mesh(roadGeo, roadMat); roads.renderOrder = 2; group.add(roads);

    // Entry roads: highlighted above the haze, fading out ~1.7× further than the city, with dashes flowing in.
    const hiGeo = new THREE.BufferGeometry(); hiGeo.setAttribute('position', new THREE.Float32BufferAttribute(hiPos, 3)); hiGeo.setAttribute('aAlong', new THREE.Float32BufferAttribute(hiAlong, 1));
    const hiMat = new THREE.ShaderMaterial({
      transparent: true, depthWrite: false, fog: false, side: THREE.DoubleSide,
      uniforms: { ...U, uCol: { value: col(o.accent) }, uReach: { value: 1.7 } },
      vertexShader: 'attribute float aAlong; varying float vA; varying vec2 vP; void main(){ vA = aAlong; vec4 w = modelMatrix*vec4(position,1.0); vP = w.xz; gl_Position = projectionMatrix*viewMatrix*w; }',
      fragmentShader: GLSL_BOX + `uniform vec3 uCol; uniform float uTime; uniform float uReach; varying float vA; varying vec2 vP;
        void main(){ float d = boxDist(vP); if (d < 0.0) discard;
          float a = (1.0 - smoothstep(uFade.x, uFade.y * uReach, d)) * smoothstep(0.0, 30.0, d);
          float dash = 0.55 + 0.45 * step(0.5, fract(vA / 38.0 + uTime * 0.6));
          gl_FragColor = vec4(uCol * 1.15, a * 0.8 * dash); }`,
    });
    const hi = new THREE.Mesh(hiGeo, hiMat); hi.renderOrder = 6; group.add(hi);

    // Buildings outside the box: they sink and blend into the haze with distance.
    // Shading is baked per face (roofs bright, walls by orientation to a fixed sun), so OSM ring winding never matters.
    const pos = [], shade = [];
    const v2 = (x, z) => new THREE.Vector2(x, z);
    const Lx = 0.55, Lz = 0.35;
    for (const b of DATA.buildings) {
      const h = b[0]; const P = []; for (let i = 1; i < b.length; i += 2) P.push([b[i], b[i + 1]]);
      if (P.length < 3) continue;
      const tone = 0.9 + ((P[0][0] * 7 + P[0][1] * 13) % 17) / 17 * 0.1;
      let cx = 0, cz = 0; for (const p of P) { cx += p[0]; cz += p[1]; } cx /= P.length; cz /= P.length;
      let tris; try { tris = THREE.ShapeUtils.triangulateShape(P.map(p => v2(p[0], p[1])), []); } catch (_) { continue; }
      for (const t of tris) for (const k of t) { pos.push(P[k][0], h, P[k][1]); shade.push(tone); }
      for (let i = 0; i < P.length; i++) {
        const [x1, z1] = P[i], [x2, z2] = P[(i + 1) % P.length]; const L = Math.hypot(x2 - x1, z2 - z1) || 1;
        let nx = (z2 - z1) / L, nz = -(x2 - x1) / L;
        if (nx * ((x1 + x2) / 2 - cx) + nz * ((z1 + z2) / 2 - cz) < 0) { nx = -nx; nz = -nz; }
        const sh = tone * (0.68 + 0.22 * Math.max(0, nx * Lx + nz * Lz) + 0.06 * Math.max(0, -nz));
        pos.push(x1, 0, z1, x2, 0, z2, x2, h, z2, x1, 0, z1, x2, h, z2, x1, h, z1);
        for (let k = 0; k < 6; k++) shade.push(sh);
      }
    }
    const bGeo = new THREE.BufferGeometry();
    bGeo.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3)); bGeo.setAttribute('aShade', new THREE.Float32BufferAttribute(shade, 1));
    const bMat = new THREE.ShaderMaterial({
      side: THREE.DoubleSide, fog: false,
      uniforms: { ...U, uCol: { value: col(o.buildingColor) } },
      vertexShader: GLSL_BOX + `attribute float aShade; varying float vF; varying float vS;
        void main(){ vec4 w = modelMatrix * vec4(position, 1.0); vF = fadeAt(w.xz); vS = aShade;
          w.y *= mix(0.9, 0.03, smoothstep(0.0, 0.95, vF)); gl_Position = projectionMatrix * viewMatrix * w; }`,   // eases down from near full height: no step at the edge
      fragmentShader: `uniform vec3 uCol; uniform vec3 uFadeColor; varying float vF; varying float vS;
        void main(){ gl_FragColor = vec4(mix(uCol * vS, uFadeColor, 0.08 + 0.92 * vF), 1.0); }`,   // and pales gradually with distance
    });
    const buildings = new THREE.Mesh(bGeo, bMat); buildings.renderOrder = 3; group.add(buildings);

    // Boundary of the simulated area: dashed line plus a soft outer glow band.
    const edgeMat = new THREE.ShaderMaterial({
      transparent: true, depthWrite: false, fog: false, side: THREE.DoubleSide,
      uniforms: { ...U, uCol: { value: col(o.outline) }, uGlow: { value: col(o.accent) } },
      vertexShader: 'attribute float aAlong; attribute float aAcross; varying float vA; varying float vX; void main(){ vA = aAlong; vX = aAcross; gl_Position = projectionMatrix*modelViewMatrix*vec4(position,1.0); }',
      fragmentShader: `uniform vec3 uCol; uniform vec3 uGlow; varying float vA; varying float vX;
        void main(){ float line = 1.0 - smoothstep(0.035, 0.06, abs(vX)); float dash = step(0.45, fract(vA / 26.0));
          float glow = pow(1.0 - smoothstep(0.0, 1.0, vX), 2.0) * step(0.0, vX) * 0.5;
          vec3 c = mix(uGlow, uCol, line); float a = max(line * dash * 0.95, glow);
          if (a < 0.01) discard; gl_FragColor = vec4(c, a); }`,
    });
    {
      const r = 14, band = 110, lw = 12; const p = [], al = [], ac = [];
      const corners = [[box.x0, box.z0], [box.x1, box.z0], [box.x1, box.z1], [box.x0, box.z1]];
      const ring = []; // rounded rectangle path
      const cc = [[box.x0 + r, box.z0 + r], [box.x1 - r, box.z0 + r], [box.x1 - r, box.z1 - r], [box.x0 + r, box.z1 - r]];
      const a0 = [Math.PI, 1.5 * Math.PI, 0, 0.5 * Math.PI];
      for (let k = 0; k < 4; k++) for (let j = 0; j <= 6; j++) { const t = a0[k] + j / 6 * Math.PI / 2; ring.push([cc[k][0] + Math.cos(t) * r, cc[k][1] + Math.sin(t) * r]); }
      ring.push(ring[0]);
      let along = 0;
      for (let i = 0; i < ring.length - 1; i++) {
        const [x1, z1] = ring[i], [x2, z2] = ring[i + 1]; const L = Math.hypot(x2 - x1, z2 - z1) || 1; let nx = (z2 - z1) / L, nz = -(x2 - x1) / L;
        const bcx = (box.x0 + box.x1) / 2, bcz = (box.z0 + box.z1) / 2; if (nx * ((x1 + x2) / 2 - bcx) + nz * ((z1 + z2) / 2 - bcz) < 0) { nx = -nx; nz = -nz; }   // glow always points outward
        // outward normal for a clockwise-in-screen ring; across runs -lw/band .. band
        const q = (w) => [x1 + nx * w, z1 + nz * w, x2 + nx * w, z2 + nz * w];
        const [ax, az, bx, bz] = q(-lw / 2), [cx, cz, dx, dz] = q(band);
        p.push(ax, 2.4, az, bx, 2.4, bz, dx, 2.4, dz, ax, 2.4, az, dx, 2.4, dz, cx, 2.4, cz);
        al.push(along, along + L, along + L, along, along + L, along);
        const A = -lw / 2 / band; ac.push(A, A, 1, A, 1, 1);
        along += L;
      }
      const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.Float32BufferAttribute(p, 3)); g.setAttribute('aAlong', new THREE.Float32BufferAttribute(al, 1)); g.setAttribute('aAcross', new THREE.Float32BufferAttribute(ac, 1));
      const edge = new THREE.Mesh(g, edgeMat); edge.renderOrder = 7; group.add(edge);
    }

    function setColors(c = {}) {
      if (c.fadeColor != null) U.uFadeColor.value.set(c.fadeColor);
      if (c.buildingColor != null) bMat.uniforms.uCol.value.set(c.buildingColor);
      if (c.roadColor != null) roadMat.color.set(c.roadColor);
      if (c.landColor != null && mats.land) mats.land.uniforms.uCol.value.set(c.landColor);
      if (c.waterColor != null && mats.water) mats.water.uniforms.uCol.value.set(c.waterColor);
      if (c.parkColor != null && mats.park) mats.park.uniforms.uCol.value.set(c.parkColor);
      if (c.accent != null) { hiMat.uniforms.uCol.value.set(c.accent); edgeMat.uniforms.uGlow.value.set(c.accent); }
      if (c.outline != null) edgeMat.uniforms.uCol.value.set(c.outline);
    }
    return {
      group, box, setColors,
      setFade(start, end) { U.uFade.value.set(start, end); },
      update(dt) { U.uTime.value += dt; },
      showEdge(on) { group.children.forEach(m => { if (m.material === edgeMat) m.visible = on; }); },
    };
  }

  window.HPContext = { add, data: DATA };
})();
