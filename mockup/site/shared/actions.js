// Shared click / submit handling for the site designs, so every design behaves the same.
// Markup uses data-act="…" on buttons (and selects, on change) and data-form="…" on forms.
// Modals: core.ui.modal = { name, arg } — designs render it, data-act="modal" opens one.
export function bindActions(core, { root = document } = {}) {
  const ui = core.ui;
  const openModal = (name, arg = null) => { ui.modal = { name, arg }; core.render(); setTimeout(() => document.querySelector('[data-autofocus]')?.focus(), 30); };
  const closeModal = () => { ui.modal = null; core.render(); };
  const findPlan = (id) => { for (const w of core.view().st.workspaces) for (const p of w.plans) if (p.id === +id) return { w, p }; return {}; };

  const acts = {
    go: (d) => { ui.modal = null; core.go(d.href); },
    modal: (d) => openModal(d.modal, d.arg ?? null),
    'close-modal': closeModal,
    copy: (d) => core.act.copy(d.text, d.msg || 'Copied'),
    'copy-invite': (d) => core.act.copy(core.inviteUrl(d.code), 'Invite link copied: send it to your teammates'),
    'new-invite': (d) => core.act.createInvite(d.ws, d.role || 'editor'),
    revoke: (d) => { if (confirm('Revoke this invite link? People who already joined stay in the workspace.')) core.act.revokeInvite(d.code); },
    'remove-member': (d) => { if (confirm(`Remove ${d.name || 'this person'} from the workspace?`)) core.act.removeMember(d.ws, d.member); },
    leave: (d) => { if (confirm('Leave this workspace? You’ll need a new invite to come back.')) core.act.leave(d.ws); },
    'set-stage': (d) => core.act.setStage(+d.plan, d.stage),
    'reset-plan': (d) => { if (confirm('Reset this plan to today’s city? Everyone’s edits in it are removed.')) core.act.resetPlan(+d.plan); },
    'delete-plan': (d) => { if (confirm('Delete this plan for everyone in the workspace?')) core.act.deletePlan(+d.plan); },
    'delete-ws': (d) => { if (confirm('Delete this workspace, all its plans and its activity, for everyone? This can’t be undone.')) { closeModal(); core.act.deleteWorkspace(d.ws); } },
    recompute: (d) => core.act.recompute(+d.plan),
    'hero-edit': (d) => core.act.tryHeroEdit(+d.plan),
    duplicate: (d) => { const { w, p } = findPlan(d.plan); if (p) core.act.createPlan(w.id, `${p.name} (copy)`.slice(0, 48), p.description, p.id, true); },
    'new-account': () => { const url = core.act.newAccount(); window.open(url, '_blank'); },
    'switch-account': (d) => { location.href = core.act.switchAccount(d.slot); },
    'toggle': (d) => { ui[d.key] = !ui[d.key]; core.render(); },
    'set-ui': (d) => { ui[d.key] = d.value; core.render(); },
  };
  const changeActs = {
    role: (el) => core.act.setRole(el.dataset.ws, el.dataset.member, el.value),
    stage: (el) => core.act.setStage(+el.dataset.plan, el.value),
  };
  const forms = {
    profile: async (f) => { if (await core.act.setProfile(f.name, f.color)) closeModal(); },
    'create-ws': async (f) => { if (await core.act.createWorkspace(f.name, f.description || '')) closeModal(); },
    join: (f) => {
      const raw = String(f.code || '').trim();
      const code = (raw.match(/join\/([a-z0-9]+)/i)?.[1] || raw).toLowerCase();
      if (!code) return core.toast('Paste an invite link or code.', 'bad');
      closeModal(); core.go(`#/join/${code}`);
    },
    // ui.stayOnBoard: the design keeps you on the workspace page and the new plan shows up there.
    'new-plan': async (f) => { if (await core.act.createPlan(f.ws, f.name, f.description || '', +f.copyFrom || 0, !ui.stayOnBoard)) closeModal(); },
    'edit-plan': async (f) => { if (await core.act.updatePlan(+f.plan, f.name, f.description || '')) closeModal(); },
    'ws-settings': async (f) => { if (await core.act.updateWorkspace(f.ws, f.name, f.description || '')) closeModal(); },
    invite: (f) => core.act.createInvite(f.ws, f.role || 'editor'),
  };

  root.addEventListener('click', (e) => {
    const el = e.target.closest('[data-act]');
    if (!el || el.tagName === 'SELECT' || el.disabled) {
      // Clicking the dimmed backdrop closes a modal.
      if (e.target.matches?.('[data-backdrop]')) closeModal();
      return;
    }
    const f = acts[el.dataset.act];
    if (f) { e.preventDefault(); f(el.dataset, el); }
  });
  root.addEventListener('change', (e) => {
    const el = e.target.closest('select[data-act]');
    if (el && changeActs[el.dataset.act]) changeActs[el.dataset.act](el);
  });
  root.addEventListener('submit', (e) => {
    const form = e.target.closest('form[data-form]');
    if (!form) return;
    e.preventDefault();
    const data = Object.fromEntries(new FormData(form).entries());
    forms[form.dataset.form]?.(data, form);
  });
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && ui.modal) closeModal(); });
  return { openModal, closeModal };
}
