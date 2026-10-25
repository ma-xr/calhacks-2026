# Faded city context around the simulation

The city used to stop abruptly at the edge of the simulated area. A shared layer now continues San Francisco beyond it: about 9.4k real OSM buildings, 2.2k streets, parks, and the real coastline (`data/processed/context.json`, built by `scripts/build_context.py`).

What the layer does:
- **Buildings:** start at half height and paler, so they clearly read as "not simulated". They then sink and blend into a haze with distance (fully gone about 1.3 km out).
- **Boundary:** a dashed line with a soft outward glow marks the simulated area.
- **Entry roads:** freeways and the main feeders (Market, Mission, Folsom, Broadway, Columbus, the Embarcadero, 3rd/4th/5th…) carry flowing accent dashes far past the edge, so the traffic entry points stay obvious.
- **Coastline:** outside the box, water and land follow the real coastline, which fixes the wrong north waterfront.

Reference integration: `mockup/variants/a-skyline/template.html` (search `HPContext`).

## How to add it to a page
1. Put `<script>/*__HP_CONTEXT__*/</script>` before the import map. `scripts/build_mockup.py` inlines `mockup/lib/hp-context.js` together with the data.
2. After the scene's land and water exist, add:
   ```js
   const CTX = window.HPContext?.add(THREE, scene, {
     fadeColor, buildingColor, roadColor, landColor, parkColor, waterColor,  // match your palette
     accent,   // entry-road dashes + boundary glow (use the car/inlet color)
     outline,  // boundary dash color
     fadeStart: 40, fadeEnd: 1300,
   });
   ```
3. Keep the layer in step with the time of day and theme, in the function that updates sky and fog:
   ```js
   CTX?.setColors({ fadeColor: <horizon-ish blend>, waterColor, landColor, buildingColor, roadColor })
   ```
   Make `fadeColor` match what the far distance looks like in your scene, roughly land color blended with the sky horizon. That way the haze is seamless.
4. In the frame loop: `CTX?.update(dt)`, which animates the entry-road dashes.
5. Optional: `CTX.showEdge(false)` hides the boundary line, e.g. in close-up shots. `CTX.setFade(start, end)` changes how quickly the context fades.

## Palette hints
- **Skyline (day):** fade = land `0xe2d5b8` lerped 60% toward the sky horizon; buildings `0xe9e2d6`; roads `0xc3bdb2`; water from the scene's water colors; accent `0x39d5ff`.
- **Night Ops:** fade near the dark horizon (e.g. `0x0e1626`); buildings a dark slate a little lighter than the ground; accent cyan; outline a pale blue-white.
- **Paper Model:** fade = the paper/table color; buildings white `0xf4f5f7`; roads a light gray; water pale blue-gray; accent the car blue.

## Notes
- The layer adds about 0.85 MB to the page (gzips to about 0.27 MB) and about 520k vertices in one draw call, plus a few small meshes.
- Camera: let the user zoom out far enough to see the fade (maxDistance around 5000–7000). Fog shouldn't hide the fade before it happens.
- Don't edit `mockup/lib/**` or `data/processed/context.json`. Ask the main agent for changes.
