// Droid live agent daemon: one warm Droid session per conversation, read-only (Factory @factory/droid-sdk).
//
// Started once by backend/droid/live.py with a minimal env (PATH, HOME, FACTORY_API_KEY) and argv JSON
// { backend, python, model, effort }. Protocol: JSON lines.
//   stdin : {op: "ask", rid, conv, prompt} | {op: "close", conv}
//   stdout: {rid, ev: "step" | "step_result" | "text" | "permission" | "done" | "error", ...}
//
// Permissions:
//   - tools:   allowlist via restrictToolIds = Execute + Script/WaitForScript (no Read, no ApplyPatch or other writes,
//              no web, MCP, sub-agents, automations, skills, settings)
//   - execute: only `<venv python> -m droid.simq ...` with plain arguments (no shell operators); everything else that
//              asks is cancelled
//   - sandbox: Droid's own command sandbox (runtime settings file): every command runs with network denied, writes
//              denied under the project root and the project .env unreadable
import { mkdirSync, writeFileSync } from 'node:fs';
import { dirname, resolve, join } from 'node:path';
import { createInterface } from 'node:readline';
import { AutonomyLevel, ToolConfirmationOutcome, createSession } from '@factory/droid-sdk/node';

const cfg = JSON.parse(process.argv[2]);
const BACKEND = resolve(cfg.backend);
const PY = cfg.python;
const IDLE_MS = 20 * 60 * 1000;
const ROOT = dirname(BACKEND);
const SETTINGS = join(BACKEND, 'droid', 'runtime', 'live-settings.json');
mkdirSync(dirname(SETTINGS), { recursive: true });
writeFileSync(SETTINGS, JSON.stringify({
  commandAllowlist: [],
  sandbox: { enabled: true, mode: 'per-command', filesystem: { denyRead: [join(ROOT, '.env')], denyWrite: [ROOT] }, network: { allowedDomains: [] } },
}, null, 1));
const sessions = new Map(); // conv -> {session, last, busy}

const emit = (o) => process.stdout.write(JSON.stringify({ t: Date.now(), ...o }) + '\n');

// Allowed: a single simq call, or a compound command split on `;`, `&&` or newlines whose every segment is
//   cd <backend dir>  |  P=<venv python>  |  <venv python | $P | ${P}> -m droid.simq <plain args>
// Anything else (pipes, redirects, $(...), backticks, other binaries) is rejected. Returns the simq args or null.
function simqArgs(cmd) {
  const segs = cmd.trim().split(/\s*(?:;|&&|\n)\s*/).filter(Boolean);
  const vars = new Set();
  const calls = [];
  for (const seg of segs) {
    const cd = seg.match(/^cd\s+(?:"([^"]+)"|'([^']+)'|(\S+))$/);
    if (cd) {
      if (resolve(BACKEND, cd[1] ?? cd[2] ?? cd[3]) !== BACKEND) return null;
      continue;
    }
    const as = seg.match(/^([A-Za-z_][A-Za-z0-9_]*)=(?:"([^"]+)"|'([^']+)'|(\S+))$/);
    if (as) {
      if (!isVenvPython(as[2] ?? as[3] ?? as[4])) return null;
      vars.add(as[1]);
      continue;
    }
    const a = oneSimq(seg, vars);
    if (a === null) return null;
    calls.push(a);
  }
  return calls.length ? calls.join(' ; ') : null;
}

// The venv interpreter, spelled absolute, relative to backend/ or quoted (python, python3 or python3.x).
function isVenvPython(p) {
  const abs = resolve(BACKEND, p);
  return dirname(abs) === dirname(resolve(PY)) && /^python(3(\.\d+)?)?$/.test(abs.split('/').pop());
}

function oneSimq(c, vars = new Set()) {
  const m = c.match(/^(?:"([^"]+)"|'([^']+)'|(\S+))\s+-m\s+droid\.simq\s+([\s\S]*)$/);
  if (!m) return null;
  const exe = m[1] ?? m[2] ?? m[3];
  const v = exe.match(/^\$\{?([A-Za-z_][A-Za-z0-9_]*)\}?$/);
  if (v ? !vars.has(v[1]) : !isVenvPython(exe)) return null;
  const args = m[4];
  // Plain arguments only: words, numbers, quoted names. No shell operators, substitutions or redirects.
  return /^[\p{L}\p{N}\s"'’.,:_\-#@+/]*$/u.test(args) ? args : null;
}

function permissionHandler(rid) {
  return ({ toolUses, options }) => {
    const calls = toolUses.flatMap(({ toolUse, details }) =>
      details?.type === 'script' ? (details.calls ?? []).map((c) => ({ tool: c.toolName, conf: c.confirmation })) : [{ tool: toolUse.name, conf: details }]);
    const verdicts = calls.map(({ tool, conf }) => {
      const cmd = conf?.type === 'exec' ? (conf.fullCommand || conf.command || '') : '';
      return { tool, target: cmd || conf?.type || 'unknown', ok: conf?.type === 'exec' && simqArgs(cmd) !== null };
    });
    const ok = verdicts.length > 0 && verdicts.every((v) => v.ok);
    for (const v of verdicts) emit({ rid, ev: 'permission', ...v, allowed: ok });
    const want = ok ? ToolConfirmationOutcome.ProceedOnce : ToolConfirmationOutcome.Cancel;
    return options.some((o) => o.value === want) ? want : ToolConfirmationOutcome.Cancel;
  };
}

const LABELS = {
  summary: 'Reading the scenario summary', streets: 'Ranking streets', edges: 'Ranking street segments', street: 'Looking up a street',
  stretch: 'Measuring a stretch', pois: 'Ranking businesses', poi: 'Looking up a business', agent: 'Reading a person’s day',
  agents: 'Counting people who changed mode', block: 'Looking up a block', blocks: 'Ranking blocks', inlets: 'Counting arrivals at the gateways',
  hour: 'Reading one hour of the day', value: 'Reading the $ value lines', assumptions: 'Checking assumptions', validation: 'Checking validation',
  find: 'Searching names',
};

function label(cmd) {
  const args = simqArgs(cmd) ?? '';
  const words = args.replace(/--scenario\s+\S+\s*/, '').trim();
  const sub = words.split(/\s+/)[0];
  return { label: (LABELS[sub] ?? 'Querying the sim') + (words.length > sub.length ? `: ${words.slice(sub.length).trim()}` : ''), simq: words };
}

const trim = (s, n) => (s.length > n ? s.slice(0, n) + ` …(+${s.length - n} chars)` : s);

const current = new Map(); // conv -> rid, for the permission handler
const owner = new Map();   // session -> conv (a spare session is adopted by the next new conversation)
let spare = null;          // Promise<DroidSession>: one pre-warmed session so a new conversation skips startup

function warmSpare() {
  spare = newSession().catch(() => null);
}

async function getSession(conv) {
  let s = sessions.get(conv);
  if (s) return s;
  const pre = spare && (await spare);
  warmSpare();
  const session = pre ?? (await newSession());
  owner.set(session, conv);
  s = { session, last: Date.now(), busy: false };
  sessions.set(conv, s);
  return s;
}

async function newSession() {
  let session;
  session = await createSession({
    cwd: BACKEND,
    execPath: join(BACKEND, 'droid', 'node_modules', '.bin', 'droid'),
    execArgs: ['--settings', SETTINGS],
    env: { PATH: process.env.PATH, HOME: process.env.HOME, FACTORY_API_KEY: process.env.FACTORY_API_KEY, PYTHONPATH: BACKEND },
    autonomyLevel: AutonomyLevel.Off,
    permissionHandler: (p) => permissionHandler(current.get(owner.get(session)))(p),
    askUserHandler: () => ({ cancelled: true }),
    systemPrompt: { type: 'preset', preset: 'droid', append: cfg.system },
    disableBuiltinSkills: true,
    ...(cfg.model ? { modelId: cfg.model } : {}),
    ...(cfg.effort ? { reasoningEffort: cfg.effort } : {}),
  });
  await session.updateSettings({ restrictToolIds: ['Execute', 'Script', 'WaitForScript'] });
  return session;
}

async function ask({ rid, conv, prompt, timeout_s }) {
  const t0 = Date.now();
  let s;
  try {
    s = await getSession(conv);
  } catch (e) {
    return emit({ rid, ev: 'error', message: `session start failed: ${e?.message ?? e}` });
  }
  if (s.busy) return emit({ rid, ev: 'error', message: 'conversation is busy' });
  s.busy = true;
  current.set(conv, rid);
  const timer = setTimeout(() => { s.session.interrupt().catch(() => {}); }, (timeout_s ?? 40) * 1000);
  const pending = new Map();
  let text = '';
  try {
    emit({ rid, ev: 'session', startup_ms: Date.now() - t0, session_id: s.session.id, model: s.session.settings.modelId });
    for await (const m of s.session.stream(prompt)) {
      if (m.type === 'tool_call' && m.name === 'Execute') {
        const cmd = String(m.input?.command ?? '');
        pending.set(m.toolUseId, cmd);
        emit({ rid, ev: 'step', id: m.toolUseId, ...label(cmd), command: cmd.replace(BACKEND + '/', '') });
      } else if (m.type === 'tool_result' && pending.has(m.toolUseId)) {
        const out = typeof m.content === 'string' ? m.content : JSON.stringify(m.content);
        emit({ rid, ev: 'step_result', id: m.toolUseId, is_error: m.isError, output: trim(out, 1200) });
      } else if (m.type === 'assistant' && m.text?.trim()) {
        text = m.text; // the last assistant message carries the answer JSON
        emit({ rid, ev: 'text', text: m.text });
      } else if (m.type === 'result') {
        if (!m.success) throw new Error(m.error?.message ?? `turn ended: ${m.subtype}`);
      }
    }
    emit({ rid, ev: 'done', text, ms: Date.now() - t0 });
  } catch (e) {
    emit({ rid, ev: 'error', message: String(e?.message ?? e), text, ms: Date.now() - t0 });
  } finally {
    clearTimeout(timer);
    s.busy = false;
    s.last = Date.now();
  }
}

setInterval(async () => {
  for (const [conv, s] of sessions) {
    if (!s.busy && Date.now() - s.last > IDLE_MS) {
      sessions.delete(conv);
      try { await s.session.close(); } catch {}
    }
  }
}, 60_000).unref();

if (!process.env.FACTORY_API_KEY) {
  emit({ ev: 'fatal', message: 'FACTORY_API_KEY is not set' });
  process.exit(1);
}
emit({ ev: 'ready' });
warmSpare();
createInterface({ input: process.stdin }).on('line', (line) => {
  let msg;
  try { msg = JSON.parse(line); } catch { return; }
  if (msg.op === 'ask') ask(msg);
  else if (msg.op === 'close') {
    const s = sessions.get(msg.conv);
    sessions.delete(msg.conv);
    s?.session.close().catch(() => {});
  }
}).on('close', async () => {
  for (const s of sessions.values()) { try { await s.session.close(); } catch {} }
  process.exit(0);
});
