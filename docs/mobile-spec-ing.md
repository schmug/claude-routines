# Mobile spec'ing runbook

This runbook describes the interactive half of the issue→PR pipeline for deployments that enable `require-spec-approved: true`. It is the **only path that may apply the `spec-approved` label** — routines are forbidden from touching it. An issue that carries the label has passed through a human-in-the-loop spec'ing session; one that lacks it has not.

`AskUserQuestion` cannot run inside a Routine. Routines are fully unattended. The label must be applied in an interactive session *before* the implementer fires.

## When this runbook applies

`require-spec-approved` is opt-in and off by default. The single-operator, unattended-from-phone path works without it — the author-allowlist check (condition 1 of the merge gate) is the binding gate. Enable strict mode when:

- The target repo has multiple collaborators and an allowlisted-author issue is not always a personally spec'd one.
- You want an explicit audit trail linking each auto-merged PR back to a human interactive session.
- You want CODEOWNERS or triage-role restrictions to govern which sessions can produce mergeable work.

## How to mint the label

1. Open an interactive Claude session: `claude.ai/code`, the desktop app, or a Remote Control session steered from the mobile app.

2. Describe your intent for the target repo. Ask Claude to research the repo and propose atomically-sized issues. Confirm or redirect the proposals.

3. For each proposed issue, use `AskUserQuestion` to tighten scope until each issue represents one atomic, reviewable change with:
   - A task-first body (CC format: Task / Pointers / Constraints / Acceptance / Out of scope) that a cold routine can execute without asking follow-up questions.
   - An explicit declared scope: a `Pointers:` section or a fenced ` ```scope ``` ` block listing in-scope file globs/paths.
   - Clear, checkable acceptance criteria.

4. Create each issue on the target repo using `gh issue create` or the GitHub UI.

5. Apply the `spec-approved` label **yourself in this session** — this is the trust token. The implementer routine will never apply it. A batch script, CLI flag, or any autonomous surface applying the label bypasses the intent-token model and defeats the purpose of strict mode.

6. Done. The implementer routine fires on `issues.opened`. With `require-spec-approved: true` in the shim, it checks for the label at the top of the author-trust gate (§1 of `implement-from-issue`) and exits silently if absent — so only labeled issues reach the implementation step.

## Label governance

- Restrict who can apply `spec-approved` to repo owners/admins using GitHub's triage-role settings or a CODEOWNERS rule on a `.github/` config that maps to the label. The goal is to make label-minting visible in the GitHub audit log and attributable to a specific identity.
- The merger routine re-checks the label at merge time (§6 condition 1 of `merge-pr-with-gate`). Removing the label after the implementer runs causes the merger to escalate to `needs-you` rather than auto-merge — intentional fail-closed behavior.
- Never automate the label. The value of `spec-approved` comes entirely from the guarantee that a human was interactively engaged during spec'ing. A CI step, a webhook, or any non-interactive automation that mints the label collapses that guarantee.

## Cross-references

- `plugins/cc-routine/skills/implement-from-issue/SKILL.md` §1 — where the implementer checks the label.
- `plugins/cc-routine/skills/merge-pr-with-gate/SKILL.md` §6 condition 1 — where the merger re-checks it.
- `SECURITY.md` §8 — tier classification for `require-spec-approved` (Tier 3 default → Tier 2 when enabled).
- `docs/proposals/auto-merge-gate/design-spec.md` §"The provenance trust gate" condition 2 — the original design-spec specification this implements.
