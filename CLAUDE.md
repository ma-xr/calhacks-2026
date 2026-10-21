# CalHacks 2026 — Project Memory

Team: **Max** and **Aziz**. This file is the shared memory for both of our
Claude Code sessions. Read it fully before making changes, and keep it
updated as decisions get made — treat it as more important than any one
conversation's memory, since it's the only context that persists across
both our machines.

## What we're building

> TBD — fill in once the idea is locked in BRAINSTORM.md.

- One-liner:
- Sponsor track / prize we're targeting:
- Judging criteria we're optimizing for:

## Tech stack

- **Framework:** Next.js 16 (App Router, TypeScript, Tailwind v4)
- **AI:** Anthropic Claude API via `@anthropic-ai/sdk` (see `src/lib/claude.ts`)
- **Hosting:** Vercel (works out of the box with this Next.js setup)
- **Other services:** TBD (DB, auth, etc. — add here once chosen)

Don't introduce a second frontend framework, a second backend language, or
a competing state-management library without updating this section first —
the whole point is one person's Claude Code session doesn't silently diverge
from the other's.

## How to run it locally

```bash
npm install
cp .env.example .env.local   # then fill in real keys
npm run dev
```

## Project structure

```
src/
  app/              - Next.js routes (pages + API routes under app/api/*)
  components/       - Shared React components
  lib/              - Shared utilities (API clients, helpers) — e.g. lib/claude.ts
```

## Ownership split (avoid clashing here)

Update this as soon as you divide the work. Keeping each person's Claude
Code session inside its own lane is the single biggest way to avoid merge
conflicts and two agents re-solving the same problem differently.

| Area | Owner | Notes |
|------|-------|-------|
| `src/app/` (pages/UI) | TBD | |
| `src/app/api/` (backend routes) | TBD | |
| `src/lib/` (shared utils) | Both — coordinate before editing | Treat as a shared contract, not a free-for-all |
| `src/components/` | TBD | |

**Rule of thumb:** if a file lives in your lane, your Claude Code session
can move fast and autonomously. If a change touches the other person's
lane or `src/lib/` (shared code), message them first or keep the change
small and obvious, then push/pull quickly so it doesn't sit stale.

## Git workflow

1. `git pull` before starting any session.
2. Work on your own branch: `git checkout -b feature/short-name`.
3. Commit small and often.
4. `git push -u origin feature/short-name`, open a PR, merge fast — don't
   let branches live long, since long-lived branches are what cause Claude
   Code sessions on each side to diverge and conflict.
5. After merging, `git checkout main && git pull` before starting the next
   piece of work, so your next Claude Code session starts from the latest
   shared state.

## Known constraints / decisions log

Add a line here every time a non-obvious decision gets made, so neither of
our Claude Code sessions re-litigates it later.

- (none yet)

## Demo plan

See `BRAINSTORM.md` for the full plan. Freeze feature work ~30–60 minutes
before the deadline and only fix demo-breaking issues after that point.
