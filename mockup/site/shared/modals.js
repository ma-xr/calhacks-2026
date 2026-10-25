// Dialogs shared by every site design: same markup and behaviour, each design styles the classes
// (.back .dlg .dh .db .df .f .in .btn .pill .link .choice .swatches .menu .danger-zone .av).
// modals(core, v, { av, icons }) returns the HTML for the open dialog ('' when none).
import { esc, ROLES, roleLabel, PALETTE } from './core.js';

export function modals(core, v, { av, icons = {} }) {
  const m = v.needName ? { name: 'profile', forced: true } : v.ui.modal;
  if (!m) return '';
  const dlg = (title, body, sub = '') => `<div class="back" ${m.forced ? '' : 'data-backdrop'}><div class="dlg" role="dialog" aria-modal="true"><div class="dh"><div><h2>${title}</h2>${sub ? `<div class="sub">${sub}</div>` : ''}</div>${m.forced ? '' : '<button class="x" data-act="close-modal" aria-label="Close">×</button>'}</div><div class="db">${body}</div></div></div>`;
  const w = v.st.workspaces.find((x) => x.id === m.arg);
  const opt = (sel) => ROLES.map((r) => `<option value="${r.key}" ${r.key === sel ? 'selected' : ''}>${r.label}</option>`).join('');
  switch (m.name) {
    case 'profile': {
      const cur = v.account.color || PALETTE[0];
      return dlg(m.forced ? 'Welcome! What should your team call you?' : 'Your profile', `<form data-form="profile" style="display:contents">
        <label class="f">Your name<input class="in" id="pf-name" name="name" maxlength="24" placeholder="e.g. Maya Chen" value="${esc(v.account.name)}" data-autofocus required></label>
        <div class="f">Your color<div class="swatches">${PALETTE.map((c) => `<label><input type="radio" name="color" value="${c}" ${c === cur ? 'checked' : ''}><span style="background:${c}"></span></label>`).join('')}</div></div>
        <div class="df"><button class="btn primary">${m.forced ? 'Continue' : 'Save'}</button></div></form>`, m.forced ? 'Your name shows on your edits and on your cursor in shared plans.' : '');
    }
    case 'account':
      return dlg('Who’s planning?', `<div class="menu">
        <button data-act="modal" data-modal="profile">${av({ ...(v.me || {}), name: v.account.name, color: v.account.color, online: true })}<span><b>${esc(v.account.name || 'You')}</b><small>Edit name and color</small></span></button>
        ${v.accounts.filter((a) => a.slot !== v.slot).map((a) => `<button data-act="switch-account" data-slot="${esc(a.slot)}">${av({ name: a.name || 'Unnamed', color: a.color })}<span>Switch to <b>${esc(a.name || 'Unnamed')}</b><small>Another person on this browser</small></span></button>`).join('')}
        <button data-act="new-account"><span class="av" style="background:#94a3b8">+</span><span><b>Add another person</b><small>Opens a new tab as someone else: handy for demoing collaboration</small></span></button></div>`);
    case 'create-ws':
      return dlg('New workspace', `<form data-form="create-ws" style="display:contents">
        <label class="f">Name<input class="in" id="cw-name" name="name" maxlength="48" placeholder="e.g. SoMa Streets Team" data-autofocus required></label>
        <label class="f">What is it for? <i>optional</i><textarea class="in" id="cw-desc" name="description" maxlength="280" placeholder="Pedestrianizing 2nd St before the 2027 budget vote"></textarea></label>
        <div class="note">You’ll be its admin. It starts with one plan, <b>Plan A</b>, ready to edit.</div>
        <div class="df"><button type="button" class="btn ghost" data-act="close-modal">Cancel</button><button class="btn primary">Create workspace</button></div></form>`);
    case 'join':
      return dlg('Join a workspace', `<form data-form="join" style="display:contents">
        <label class="f">Invite link or code<input class="in" id="jn-code" name="code" placeholder="Paste the link a teammate sent you" data-autofocus required></label>
        <div class="df"><button type="button" class="btn ghost" data-act="close-modal">Cancel</button><button class="btn primary">Join</button></div></form>`);
    case 'invite': {
      if (!w) return '';
      const link = w.invites.find((i) => i.role === 'editor') || w.invites[0];
      return dlg(`Invite people to ${esc(w.name)}`, `${link ? `<div class="link"><span class="pill ${link.role}">${roleLabel(link.role)}</span><code>${esc(core.inviteUrl(link.code))}</code><button class="btn sm primary" data-act="copy-invite" data-code="${esc(link.code)}">${icons.copy || ''}Copy</button></div>
        <div class="note">Send this link to your colleagues. Opening it asks for their name and adds them as ${roleLabel(link.role).toLowerCase()}s.</div>` : `<div class="note">No invite link yet. Create one below.</div>`}
        <form class="row" data-form="invite"><input type="hidden" name="ws" value="${w.id}"><span class="note">Need a different role?</span><select class="inline" name="role">${opt('viewer')}</select><button class="btn sm">Create link</button></form>
        <div class="df"><button class="btn ghost" data-act="go" data-href="#/w/${w.id}/people">Manage people</button><button class="btn" data-act="close-modal">Done</button></div>`);
    }
    case 'new-plan':
      if (!w) return '';
      return dlg('New plan', `<form data-form="new-plan" style="display:contents"><input type="hidden" name="ws" value="${w.id}">
        <label class="f">Name<input class="in" id="np-name" name="name" maxlength="48" placeholder="e.g. Car-free Howard St" data-autofocus required></label>
        <label class="f">Idea <i>optional</i><textarea class="in" id="np-desc" name="description" maxlength="280" placeholder="What are you trying to change, and why?"></textarea></label>
        <div class="f">Start from<div class="choice">
          <label><input type="radio" name="copyFrom" value="0" checked>Today’s city<small>A blank plan</small></label>
          ${w.plans.slice(-3).map((p) => `<label><input type="radio" name="copyFrom" value="${p.id}">${esc(p.name)}<small>Copy its edits</small></label>`).join('')}</div></div>
        <div class="df"><button type="button" class="btn ghost" data-act="close-modal">Cancel</button><button class="btn primary">Create plan</button></div></form>`);
    case 'edit-plan': {
      const p = v.st.workspaces.flatMap((x) => x.plans).find((x) => x.id === +m.arg);
      if (!p) return '';
      return dlg('Rename plan', `<form data-form="edit-plan" style="display:contents"><input type="hidden" name="plan" value="${p.id}">
        <label class="f">Name<input class="in" id="ep-name" name="name" maxlength="48" value="${esc(p.name)}" data-autofocus required></label>
        <label class="f">Idea<textarea class="in" id="ep-desc" name="description" maxlength="280">${esc(p.description)}</textarea></label>
        <div class="df"><button type="button" class="btn ghost" data-act="close-modal">Cancel</button><button class="btn primary">Save</button></div></form>`);
    }
    case 'ws-settings':
      if (!w) return '';
      return dlg('Workspace settings', `${w.myRole === 'admin' ? `<form data-form="ws-settings" style="display:contents"><input type="hidden" name="ws" value="${w.id}">
        <label class="f">Name<input class="in" id="ws-name-${w.id}" name="name" maxlength="48" value="${esc(w.name)}" required></label>
        <label class="f">Description<textarea class="in" id="ws-desc-${w.id}" name="description" maxlength="280">${esc(w.description)}</textarea></label>
        <div class="df"><button class="btn primary">Save</button></div></form>
        <div class="danger-zone"><span><b>Delete workspace</b><small>Removes every plan and member, for everyone.</small></span><button class="btn sm danger" data-act="delete-ws" data-ws="${w.id}">Delete</button></div>` : `<div class="note">Only admins can change workspace settings.</div>`}
        <div class="danger-zone soft"><span><b>Leave workspace</b><small>You’ll need a new invite to come back.</small></span><button class="btn sm" data-act="leave" data-ws="${w.id}">Leave</button></div>`);
  }
  return '';
}
