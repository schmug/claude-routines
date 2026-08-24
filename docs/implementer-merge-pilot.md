# Implementer gate-conditional landing pilot (#27)

Validates step 9 of `plugins/cc-routine/skills/implement-from-issue/SKILL.md`:
the implementer may land its own PR only when the target repo's `<base>` is
mechanically gated (≥1 required status check via active ruleset or classic
protection), and keeps today's stop-at-open-PR behavior everywhere else.

Format mirrors the merger pilot (#16): one section per scenario listing repo,
PR URL, expected behavior, actual behavior, pass/fail. The same #16 discipline
applies — use real PRs the implementer routine produces on a **single** target
repo first; do not synthesize PRs to game the gate. If a scenario produces an
unexpected merge, STOP the pilot and file a P1 bug against the skill.

Status: **scenarios defined, not yet run.** Run alongside (not before) the
merger pilot #16; the prose gate probe here is Tier 3 until the deterministic
TS gate lands (#18).

## G1 — gated repo, green CI

- Repo: _(pilot target with Tier-2 protection; audit first with `gh api repos/<slug>/branches/<base>/protection`)_
- PR URL: _pending_
- Expected: implementer opens the PR, detects ≥1 required status check, runs
  `gh pr merge --auto --squash --delete-branch`. The PR merges (squash) only
  after every required check passes; branch deleted; final message reports
  `Merge outcome: auto-merge enabled`.
- Actual: _pending_
- Pass/fail: _pending_

## G2 — gated repo, red CI

- Repo / PR URL: _pending_
- Expected: auto-merge is enabled but the failing required check holds the
  merge indefinitely. Implementer fixes the underlying cause or posts one
  signed comment + `impl-blocked` and exits. The PR never merges while red.
- Actual: _pending_
- Pass/fail: _pending_

## G3 — ungated repo (no ruleset, no protection)

- Repo / PR URL: _pending_
- Expected: **unchanged behavior** — PR left open, no merge, no auto-merge;
  final message reports `left open (ungated: no active ruleset/protection on
  <base>)`.
- Actual: _pending_
- Pass/fail: _pending_

## G4 — gate detection failure (e.g. token lacks scope, API 403/404)

- Repo / PR URL: _pending_
- Expected: fail closed — treated exactly as ungated. PR left open; final
  message names the detection failure. An UNKNOWN gate state is never a pass.
- Actual: _pending_
- Pass/fail: _pending_

## G5 — protection present but zero required status checks

- Repo / PR URL: _pending_
- Expected: ungated (a gate with no required checks gates nothing). PR left
  open; final message reports `left open (ungated: protection present but zero
  required status checks)`.
- Actual: _pending_
- Pass/fail: _pending_

## Cross-references

- #27 — the skill-text change this pilot validates
- #16 — merger pilot (V1–V5); G-scenarios complement, not replace, it
- #18 — deterministic TS gate that replaces the prose probe (this pilot's
  scenarios re-run against it at go-live)
- `scripts/setup-branch-protection.sh` — Tier-2 setup for the pilot target
