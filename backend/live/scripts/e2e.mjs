// End-to-end check: connect like a browser, make the hero street car-free, time until result_summary
// reflects that edit, then reset. Needs the engine (:8787), `spacetime start`, the published module
// and a reachable engine url (scripts/engine-proxy.mjs --set).
import { connectLive } from '../client/dist/live.mjs';

const world = await (await fetch('http://localhost:8787/world')).json();
// --fresh adds one random editable street so the engine can't answer from its cache.
const edges = [...world.hero.street_edges];
if (process.argv.includes('--fresh')) edges.push(world.editable_edges[Math.floor(Math.random() * world.editable_edges.length)]);
let t0 = 0, target = 0, done = false;

const live = connectLive({
  uri: 'ws://localhost:3000',
  name: 'e2e bot',
  onError: e => { console.error('error', e); process.exit(1); },
  onChange: (s, table) => {
    if (table === '*' && !t0) {
      console.log(`connected: ${s.players.length} players, status=${s.scenario?.status}, edits=${s.streets.size}`);
      t0 = performance.now();
      live.setPedestrian(edges, true).then(() => { target = live.state().scenario.editVersion; });
    }
    const r = s.result;
    if (!done && target && r && r.editVersion >= target && s.streets.size >= edges.length) {
      done = true;
      const ms = Math.round(performance.now() - t0);
      console.log(`result_summary after ${ms} ms (engine ${r.settleMs} ms${r.cached ? ', cached' : ''}): plan=${r.scenarioId} value_total=$${Math.round(r.value.total).toLocaleString()}/yr ` +
        `car trips Δ=${r.delta.trips.car} carDay[${edges[0]}]=${Math.round(r.carDay[edges[0]])} pedDay[${edges[0]}]=${Math.round(r.pedDay[edges[0]])}`);
      console.log('activity:', s.activity.slice(-3).map(a => `${a.who}: ${a.text}`).join(' | '));
      const keep = process.argv.includes('--keep');
      (keep ? Promise.resolve() : live.reset()).then(() => setTimeout(() => process.exit(ms <= 3000 ? 0 : 2), 300));
    }
  },
});
setTimeout(() => { console.error('timeout: no result in 15 s', live.state().scenario); process.exit(1); }, 15000);
