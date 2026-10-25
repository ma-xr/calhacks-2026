// Droid policy compiler: one proposal = one Droid session (Factory @factory/droid-sdk).
//
// Started by backend/droid/service.py with a minimal environment (PATH, HOME, FACTORY_API_KEY) and a JSON job on
// stdin: { id, request, backend, taken_kinds, gate_python, timeout_s, max_fix_turns, model? }.
// Writes one JSON event per stdout line: plan | todo | step | step_result | permission | text | gate | done | error.
//
// Permissions:
//   - tools:       allowlist via restrictToolIds (no web, MCP, sub-agents, automations, skills, settings)
//   - create/edit: only hp/policies/generated/<kind>.py and hp/policies/generated/test_<kind>.py (permissionHandler,
//                  autonomy Off, so every write and every non-read-only command asks)
//   - execute:     only the exact gate command
//   - sandbox:     Droid's own command sandbox (runtime settings file), cwd = hp/policies/generated: commands may write
//                  only there, have no network, and cannot read the project .env
import { spawn } from 'node:child_process';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, resolve, join } from 'node:path';
import {
  AutonomyLevel,
  ToolConfirmationOutcome,
  ToolConfirmationType,
  createSession,
} from '@factory/droid-sdk/node';

const job = JSON.parse(readFileSync(0, 'utf8'));
const BACKEND = resolve(job.backend);
const KIND_RE = /^[a-z][a-z0-9_]{1,40}$/;
const GEN = join(BACKEND, 'hp', 'policies', 'generated');
const SETTINGS = join(BACKEND, 'droid', 'runtime', 'compiler-settings.json');
mkdirSync(dirname(SETTINGS), { recursive: true });
writeFileSync(SETTINGS, JSON.stringify({
  commandAllowlist: [],
  sandbox: { enabled: true, mode: 'per-command', filesystem: { denyRead: [join(dirname(BACKEND), '.env')] }, network: { allowedDomains: [] } },
}, null, 1));
// Allowlist (restrictToolIds). In droid 0.249 tools are called from inside the Script tool (JS: tools.Read(...)).
const KEEP_TOOLS = ['Read', 'Grep', 'Glob', 'LS', 'Execute', 'ApplyPatch', 'TodoWrite', 'Script', 'WaitForScript'];
const deadline = Date.now() + (job.timeout_s ?? 480) * 1000;
const abort = new AbortController();
const timer = setTimeout(() => { emit('error', { message: `time limit of ${job.timeout_s}s reached` }); abort.abort(); }, deadline - Date.now());

function emit(ev, data = {}) {
  process.stdout.write(JSON.stringify({ ev, t: Date.now(), ...data }) + '\n');
}

let kind = null;
let allowed = new Set();
const gateCmd = () => `${job.gate_python} -m droid.gate ${kind}`;

const rel = (p) => p.replace(BACKEND + '/', '');

// One confirmation -> verdict. Script permissions carry one confirmation per tool call inside the script.
function judge(tool, conf, input) {
  const t = conf?.type;
  if (t === 'apply_patch' || t === ToolConfirmationType.Create || t === ToolConfirmationType.Edit) {
    const patch = String(conf.patchContent ?? input?.input ?? '');
    const files = [...patch.matchAll(/\*\*\* (?:Add|Update|Delete) File: (.+)/g)].map((m) => resolve(GEN, m[1].trim()));
    if (conf.filePath) files.push(resolve(GEN, conf.filePath));
    const ok = files.length > 0 && !/\*\*\* Delete File:/.test(patch) && files.every((f) => allowed.has(f));
    return { tool, target: [...new Set(files.map(rel))].join(', '), ok };
  }
  if (t === ToolConfirmationType.Execute) {
    const cmd = (conf.fullCommand || conf.command || '').trim();
    // Accept the gate command, optionally prefixed by `cd <backend> &&` and with quoted paths; nothing else.
    const norm = cmd.replace(/^cd\s+("?)([^"]+)\1\s*&&\s*/, (m, q, dir) => ([BACKEND, GEN].includes(resolve(GEN, dir)) ? '' : m)).replace(/"([^"\s]*(?:\s[^"]*)?)"/g, '$1');
    return { tool, target: cmd, ok: kind !== null && norm === gateCmd() };
  }
  return { tool, target: t ?? 'unknown', ok: false };
}

function permissionHandler({ toolUses, options }) {
  const verdicts = toolUses.flatMap(({ toolUse, details }) =>
    details?.type === 'script'
      ? (details.calls ?? []).map((c) => judge(c.toolName, c.confirmation, c.toolInput))
      : [judge(toolUse.name, details, toolUse.input)]);
  const ok = verdicts.every((v) => v.ok);
  for (const v of verdicts) emit('permission', { ...v, allowed: ok });
  const want = ok ? ToolConfirmationOutcome.ProceedOnce : ToolConfirmationOutcome.Cancel;
  return options.some((o) => o.value === want) ? want : ToolConfirmationOutcome.Cancel;
}

function summarize(name, input) {
  if (!input) return name;
  const p = input.file_path ?? input.filePath ?? input.path ?? input.pattern ?? input.command ?? input.query;
  return p ? `${name} ${String(p).replace(BACKEND + '/', '')}` : name;
}

async function turn(session, prompt, label) {
  emit('turn', { label });
  let text = '';
  for await (const m of session.stream(prompt, { abortSignal: abort.signal })) {
    switch (m.type) {
      case 'tool_call':
        if (m.name === 'TodoWrite') emit('todo', { todos: m.input?.todos ?? m.input });
        else emit('step', { id: m.toolUseId, tool: m.name, summary: summarize(m.name, m.input), input: trim(m.input) });
        break;
      case 'tool_result':
        if (m.toolName !== 'TodoWrite')
          emit('step_result', { id: m.toolUseId, tool: m.toolName, is_error: m.isError, output: trim(typeof m.content === 'string' ? m.content : JSON.stringify(m.content), 3000) });
        break;
      case 'assistant':
        if (m.text?.trim()) { text += m.text; emit('text', { text: m.text }); }
        break;
      case 'result':
        if (!m.success) throw new Error(m.error?.message ?? `turn ended: ${m.subtype}`);
        emit('usage', { tokens: m.tokenUsage ?? null });
        break;
    }
  }
  return text;
}

function trim(v, n = 1500) {
  const s = typeof v === 'string' ? v : JSON.stringify(v ?? '');
  return s.length > n ? s.slice(0, n) + ` …(+${s.length - n} chars)` : s;
}

function runGate() {
  return new Promise((res) => {
    const p = spawn(job.gate_python, ['-m', 'droid.gate', kind], { cwd: BACKEND, env: { PATH: process.env.PATH, HOME: process.env.HOME } });
    let out = '';
    p.stdout.on('data', (d) => (out += d));
    p.stderr.on('data', (d) => (out += d));
    const k = setTimeout(() => p.kill('SIGKILL'), Math.min(240_000, Math.max(5_000, deadline - Date.now())));
    p.on('close', () => {
      clearTimeout(k);
      const line = out.split('\n').reverse().find((l) => l.startsWith('GATE_RESULT '));
      const result = line ? JSON.parse(line.slice(12)) : { passed: false, checks: [{ name: 'gate', ok: false, detail: 'gate crashed or timed out' }] };
      res({ result, output: out.slice(-8000) });
    });
  });
}

function parsePlan(text) {
  const m = text.match(/```json\s*([\s\S]*?)```/) ?? text.match(/(\{[\s\S]*\})/);
  if (!m) throw new Error('Droid did not return a JSON plan');
  return JSON.parse(m[1]);
}

const RULES = `
You are the policy compiler inside "The Human Project", a deterministic agent-based traffic + retail sim of SF
FiDi/SoMa (Python, numpy). You write ONE new policy plugin module and ONE pytest file, nothing else.
Hard rules (enforced by the host; violating them gets the tool call cancelled):
- Write files ONLY with tools.ApplyPatch (inside Script). You may only create/edit the two files you are told. Never touch other files. Never read .env or any secrets.
- The only shell command you may run is the gate command you are given. No pip, no network, no web.
- The module may import only numpy and math. Pure functions of the read-only views: no I/O, no randomness,
  no eval/exec/getattr/open, no dunder attributes. Same input -> same output.
Read ${BACKEND}/hp/policies/__init__.py first: it documents the plugin interface (Agents, Edges, Pois views and the
hooks car_cost_usd / edge_cost_factor / poi_attractiveness). ${BACKEND}/hp/policies/testing.py has the test helpers.
`;

let session;
try {
  if (!process.env.FACTORY_API_KEY) throw new Error('FACTORY_API_KEY is not set');
  session = await createSession({
    cwd: GEN,
    execPath: join(BACKEND, 'droid', 'node_modules', '.bin', 'droid'),
    execArgs: ['--settings', SETTINGS],
    env: { PATH: process.env.PATH, HOME: process.env.HOME, FACTORY_API_KEY: process.env.FACTORY_API_KEY, PYTHONPATH: BACKEND },
    autonomyLevel: AutonomyLevel.Off,
    permissionHandler,
    askUserHandler: () => ({ cancelled: true }),
    systemPrompt: { type: 'preset', preset: 'droid', append: RULES },
    disableBuiltinSkills: true,
    abortSignal: abort.signal,
    ...(job.model ? { modelId: job.model } : {}),
  });
  await session.updateSettings({ restrictToolIds: KEEP_TOOLS, enabledToolIds: ['ApplyPatch'] });
  const tools = await session.listTools();
  emit('session', { session_id: session.id, model: session.settings.modelId, sandbox: SETTINGS.replace(BACKEND + '/', ''),
                    tools: tools.filter((t) => t.allowed).map((t) => t.id), disabled: tools.filter((t) => !t.allowed).map((t) => t.id) });

  // Turn 1: plan only.
  const planText = await turn(session, `A city planner asked for a lever the engine does not support yet:

  "${job.request}"

Read ${BACKEND}/hp/policies/__init__.py (and skim ${BACKEND}/hp/engine.py Ctx.choose for how car costs and through-traffic
work). Then reply with ONLY a fenced \`\`\`json block, no files written yet:
{
  "kind": "snake_case_id (not one of: ${['congestion_charge', 'parking_price', ...job.taken_kinds].join(', ')})",
  "title": "short UI title",
  "summary": "one paragraph: what the lever does in model terms and which hook(s) carry it",
  "hooks": ["car_cost_usd" | "edge_cost_factor" | "poi_attractiveness"],
  "params": {"name": {"default": number, "min": number, "max": number, "unit": "USD|min|share|..."}},
  "example": {"name": value},
  "assumptions": ["modelling simplifications a reviewer should know"],
  "steps": ["numbered implementation + test steps"]
}`, 'plan');
  const plan = parsePlan(planText);
  kind = String(plan.kind ?? '').toLowerCase();
  if (!KIND_RE.test(kind) || ['congestion_charge', 'parking_price'].includes(kind)) throw new Error(`invalid kind ${plan.kind}`);
  let n = 2;
  const base = kind;
  while (job.taken_kinds.includes(kind)) kind = `${base}_${n++}`;
  plan.kind = kind;
  const modPath = `hp/policies/generated/${kind}.py`;
  const testPath = `hp/policies/generated/test_${kind}.py`;
  allowed = new Set([resolve(BACKEND, modPath), resolve(BACKEND, testPath)]);
  emit('plan', { plan, files: [modPath, testPath], gate: gateCmd() });

  // Turn 2: implement + test.
  await turn(session, `Plan accepted. kind = "${kind}". Implement it now.

1. Create ${BACKEND}/${modPath} with KIND = "${kind}", TITLE, DESCRIPTION, PARAMS (your params, each with default/min/max/unit),
   EXAMPLE (a dict of params for the gate's demo run, e.g. the request's numbers), and the hook function(s). Use the view
   helpers (agents.is_through, agents.arrive_h, edges.stretch(...), pois.fronting(...), ...). Return numpy arrays of the
   documented shapes. Keep it short and commented like the engine code.
2. Create ${BACKEND}/${testPath}: pytest tests using hp.policies.testing (load_policy("${kind}"), view(), run(mod, view, params))
   that check the hook targets exactly the intended agents/edges/POIs, respects params (e.g. 0 -> no effect), and returns
   finite arrays of the right shape. Keep tests fast: do NOT call testing.metrics() (the gate runs the full engine).
3. Run exactly this command: ${gateCmd()}
   It runs a static scan, your test, the engine test suite, a determinism check and a sanity check. Fix your two files
   until it prints GATE_RESULT with "passed": true. Then reply with a two-sentence summary.`, 'implement');

  let gate = await runGate();
  emit('gate', { attempt: 1, ...gate });
  for (let i = 0; !gate.result.passed && i < (job.max_fix_turns ?? 2) && Date.now() < deadline - 60_000; i++) {
    await turn(session, `The host re-ran the gate and it FAILED. Fix only your two files, re-run ${gateCmd()}, and stop when it passes.

${gate.output.slice(-4000)}`, `fix ${i + 1}`);
    gate = await runGate();
    emit('gate', { attempt: i + 2, ...gate });
  }
  emit('done', { success: gate.result.passed, kind });
} catch (e) {
  emit('error', { message: abort.signal.aborted ? `aborted: time limit (${job.timeout_s}s)` : String(e?.message ?? e) });
  emit('done', { success: false, kind });
} finally {
  clearTimeout(timer);
  try { await session?.close(); } catch {}
  process.exit(0);
}
