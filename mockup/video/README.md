# Video deck

A deck for recording the CommonGround video while someone narrates live. It shows almost no text. Most slides drive the real 3D app (same origin, through `window.__bw`): the camera, the info views, the 2nd St edit and following Maria. The narration lives only in the presenter window.

## Record

1. Run `./run.sh` (the engine and the web app). It also copies the website's client to `mockup/site/live.mjs`.
2. For the workspace slide, start SpacetimeDB: `spacetime start`, then `cd backend/workspaces && npm install && npm run publish:local`.
3. Open http://localhost:8765/video/ in Chrome. Add `?snapshot` to replay saved engine results without the engine. The workspace slide still needs the engine to show a plan's value.
4. Wait for **● City loaded**, then press **P** to open the presenter window on your second screen, and **F** to make the deck fullscreen.
5. Start the screen recording (macOS: ⇧⌘5 → record the screen, and pick the microphone under Options). Then press **→** to begin.

| Key | Action |
|---|---|
| → · PageDown · Space | Next reveal, or the next slide when none are left |
| ← · PageUp | Previous slide (it rebuilds that slide's app state) |
| P | Presenter window |
| F | Fullscreen |
| B or . | Black screen |
| M | Manual reveals: each reveal waits for a click |

## Pacing

Each reveal fires when the narrator reaches a marked word at the set pace (default 155 words a minute). The presenter window numbers and underlines those words. Pressing → fires the next reveal early, and the later ones move up with it. Change the pace with − / + in the presenter window or with `?wpm=140`. Rehearse a single slide with `?slide=9`.

The presenter window also has slide and total timers with target times, a **Mic check** level meter, and **Reload app**.

## The workspace slide

Slide 13 shows two teammates side by side on the CommonGround website: Max (editing) and Aziz (watching). Each is their own SpacetimeDB identity (`?acct=max`, `?acct=aziz`).

**Setup:** the deck does this itself from slide 11 on. It signs both of them in, creates the **SF Planning** workspace if it doesn't exist yet, and has Aziz join it with an editor invite.

**On the slide**, while you narrate "[Create the project, edit a road.]":
1. The deck's cursor clicks **+ New plan** in Max's window, types *2nd Street Promenade* and creates it.
2. It opens the plan and clicks **Try it: car-free 2nd Street**.
3. The new card on Aziz's board updates live with the engine's value, and a ring highlights it.

Each take first deletes the plan the last take created. To change the names, edit `TEAM`, `WS_NAME` and `PLAN_NAME` in `index.html`.

## Media

`media/ditmars.jpg` (optional, add it yourself): a photo of the Ditmars Blvd open street. When the street opens on slide 2, it fades in behind the +44% figure. Without it, the slide uses its animated street drawing.

## Slides

1. Cities shape us: the live city at dusk. 2. Ditmars Blvd, +44%. 3. Months, years. 4. Minutes. 5. CommonGround logo, then a dive to street level. 6. Data sources over the live info views. 7. Rush hour, with model vs BART arrivals (r = 0.97). 8. Painting 2nd St car-free. 9. Foot traffic, revenue and Mission St spillover, with the compare swipe. 10. Following Maria. 11. Policy tiles. 12. Factory Droid writing `through_charge.py`. 13. Two teammates editing one plan live (SpacetimeDB). 14. SF, Chicago and New York, then the US map. 15. Logo and "Tested in minutes, not years."
