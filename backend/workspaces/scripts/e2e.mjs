// End-to-end check with two people: Ada creates a workspace, Ben joins it with the invite code, Ben
// makes the hero street car-free in Plan A, and both see the same settled result. Ada's client runs
// the compute against the engine (browser-side compute), so this needs the engine (:8787),
// `spacetime start` and the published module, but no public engine URL.
import { connectLive } from '../client/dist/live.mjs';

const ENGINE = process.env.HP_ENGINE || 'http://localhost:8787';
const world = await (await fetch(`${ENGINE}/world`)).json();
// --fresh adds one random editable street so the engine can't answer from its cache.
const edges = [...world.hero.street_edges];
if (process.argv.includes('--fresh')) edges.push(world.editable_edges[Math.floor(Math.random() * world.editable_edges.length)]);
const wsName = `e2e ${Date.now().toString(36)}`;
const fail = (msg, extra) => { console.error('FAIL:', msg, extra ?? ''); process.exit(1); };
const until = (label, fn, ms = 15000) => new Promise((res, rej) => {
  const t0 = Date.now();
  const tick = () => { let v; try { v = fn(); } catch (e) { return rej(e); } if (v) return res(v); if (Date.now() - t0 > ms) return rej(new Error(`timeout: ${label}`)); setTimeout(tick, 50); };
  tick();
});
const open = (name, engine) => new Promise((res) => {
  const c = connectLive({ uri: 'ws://localhost:3000', name, engine, onError: e => console.warn(name, 'error', e?.message ?? e), onChange: (s, t) => { if (t === '*' && s.ready) res(c); } });
});

const ada = await open('Ada (e2e)', ENGINE);
const ben = await open('Ben (e2e)', false);
console.log('connected: ada', ada.identity().slice(0, 8), 'ben', ben.identity().slice(0, 8));

await ada.createWorkspace(wsName, 'end-to-end check');
const ws = await until('workspace', () => ada.state().workspaces.find(w => w.name === wsName && w.invites.length && w.plans.length));
const plan = ws.plans[0], code = ws.invites[0].code;
console.log(`workspace ${ws.id} "${ws.name}" plan ${plan.id} invite ${code} (${ws.invites[0].role})`);
await until('baseline result', () => ada.planState(plan.id).scenario?.status === 'ready');
console.log('baseline settled');

await ben.join(code);
const bws = await until('ben sees workspace', () => ben.state().workspaces.find(w => w.id === ws.id));
if (bws.myRole !== 'editor') fail('ben should be an editor', bws.myRole);
if (bws.invites.length) fail('editors must not see invite codes');
console.log(`ben joined as ${bws.myRole}; members: ${bws.members.map(m => `${m.name}/${m.role}`).join(', ')}`);

const t0 = performance.now();
await ben.setPedestrian(plan.id, edges, true);
const target = ben.planState(plan.id).scenario.editVersion;
const r = await until('shared result', () => {
  const p = ben.planState(plan.id);
  return p.scenario?.status === 'ready' && p.result && p.result.editVersion >= target && p.streets.size >= edges.length ? p : null;
});
const ms = Math.round(performance.now() - t0);
console.log(`ben sees result after ${ms} ms (engine ${r.result.settleMs} ms${r.result.cached ? ', cached' : ''}): plan=${r.result.scenarioId} value=$${Math.round(r.result.value.total).toLocaleString()}/yr car trips Δ=${r.result.delta.trips?.car}`);
const a = ada.planState(plan.id);
if (a.result?.scenarioId !== r.result.scenarioId) fail('ada and ben disagree on the result');

// Viewers can't edit.
await ada.setRole(ws.id, ben.identity(), 'viewer');
await until('ben is viewer', () => ben.state().workspaces.find(w => w.id === ws.id)?.myRole === 'viewer');
let blocked = false;
try { await ben.reset(plan.id); } catch { blocked = true; }
if (!blocked) fail('viewer was allowed to reset the plan');
console.log('viewer edit correctly refused');
console.log('activity:', ada.state().workspaces.find(w => w.id === ws.id).activity.slice(-4).map(x => `${x.who}: ${x.text}`).join(' | '));

if (!process.argv.includes('--keep')) await ada.deleteWorkspace(ws.id);
console.log('PASS');
setTimeout(() => process.exit(ms <= 10000 ? 0 : 2), 300);
