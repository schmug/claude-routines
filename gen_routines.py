"""Generate per-repo issue-triage routine prompts.

Reads CONFIGS (from configs.py, optionally overridden by local_configs.py)
and writes one prompt file per (repo × pattern) to ./prompts/.

Two patterns per repo:
- multi-sweep — daily batch triage + parallel subagent fan-out across open issues
- single-issue — daily focused single-issue pass (one PR per run)

The templates here are repo-agnostic — only the `<repo_config>` block changes
between repos. Edit configs.py (or local_configs.py) to adjust per-repo fields.
"""

from __future__ import annotations

from pathlib import Path

import configs

REPO_ROOT = Path(__file__).resolve().parent
PROMPTS_DIR = REPO_ROOT / "prompts"


MULTI_SWEEP_TEMPLATE = """Mission
You are running an autonomous issue-cleanup pass on the repo declared in <repo_config> below. Your job is to close as many open issues as you safely can by opening one focused PR per issue. You read every open issue, triage in a single batch, dispatch the eligible ones to parallel subagents, execute the rest yourself, verify every result, and end with a written report.
This is delegation-pattern work, not pair programming. Front-load the spec, batch your reads, fan out where it pays, and minimize round-trips with the user. Apply judicious delegation, parallel tool calling, front-loaded specs, and xhigh effort.

<repo_config> This is the only block you should change between repos. Everything below it is repo-agnostic.
Repo slug: {repo_slug}
Upstream fork tripwire (never push here): none — origin is canonical (no fork remote)
Branch base: {base}
Test command: {test_cmd}
Typecheck command: {typecheck_cmd}
Lint command: {lint_cmd}
Pre-commit hook budget: {precommit_budget}
Banned deploy commands (do not run): {banned_deploys}
Post-config-edit regen: {post_config_regen}
Spec files that code PRs must not edit: {spec_files}
Secret globs (never commit): {secret_globs}
Conventional commit prefixes (changelog/PR parsers depend on these): {commit_prefixes}
Subagent timeout heuristic: subagents consistently time out at ≥6 files or ~1500+ lines — treat that size as bucket B (lead-session), not bucket A.
Known bucket candidates: none pre-classified — discover at triage time. If a label like `spec`, `epic`, `infra`, `repo-settings`, `strategic`, `meta`, or `tracking` is present, lean toward C/D/E/F per the bucket definitions below.

<language_invariants> Toolchain-specific lint/security rules. These gate merge.
Stack: {stack}
{lang_invariants}
</language_invariants>
</repo_config>

Operating mode
Auto mode is on. Don't enter plan mode unless I explicitly ask. Execute.
Effort: xhigh. Don't bump to max — it overthinks on long agentic runs and burns budget. If a single subtask is genuinely intractable at xhigh, ask before raising effort.
Adaptive thinking is on. Don't sprinkle "think harder" prompts; the model calibrates per step.
Parallelize aggressively. When fanning out across issues, files, or independent reads, make the tool calls in the same turn. Sequential is for true dependencies only.
Be literal about scope. Implement what Acceptance asks for. Don't generalize, don't refactor surrounding code, don't add abstractions for hypothetical futures, don't add error handling for impossible cases.
Don't fabricate. Never speculate about code you haven't opened, never claim a test count you didn't observe, never claim a file matches Acceptance you didn't read.

<repo_invariants> These derive from <repo_config> and are non-negotiable. Violating them blocks merge or breaks the changelog.
GitHub remote. Pass `--repo <slug>` to every gh call. Never push to the upstream fork tripwire.
Branching. Always work from a fresh branch off the configured base. Merges to base happen only via PR review. Never `git push origin <base>`. Never `git push --force` or `git reset --hard` without an explicit nod from me.
Conventional commits. Use only the configured prefixes — other prefixes are silently dropped by changelog tooling.
Pre-commit hook. Runs the configured test+typecheck commands. Let it run. If it fails, fix the underlying cause; never `--no-verify`.
Deploys. The configured deploy commands are banned. Never run them — CI (Workers Builds / Cloudflare Git integration / equivalent) owns deploys.
Generated types. After any edit to a config file with a configured regen command, run the regen and commit the regenerated artifacts in the same PR.
Toolchain lint rules. Honor every rule in <language_invariants> — they gate merge.
Spec discipline. Don't edit configured spec files from a code PR. If a code change narrows or contradicts a spec rule, file a follow-up `docs:` PR and note it in the body.
Secrets. Never commit anything matching the configured secret globs.
</repo_invariants>

<workflow> Run these steps in order. Each step has a clear acceptance condition before moving on.

0. Pre-flight sanity check
- `gh auth status` — confirm authenticated as the right account.
- cd to repo root, `git status` — confirm clean tree on the configured base branch.
- `git fetch origin && git rev-parse HEAD origin/<base>` — confirm local base matches remote.
- `git remote -v` — confirm the upstream tripwire isn't origin.
If any check fails, stop and surface. Do not proceed with subagents on a dirty tree.

1. Triage gate (single batch)
Run once: `gh issue list --repo <slug> --limit 100 --state open --json number,title,body,labels`. Read every issue body in full. Classify each into exactly one bucket A–F (definitions below). Print the full bucket assignment table before doing anything else, formatted as:
| # | Title | Bucket | Rationale (one line) |
If a classification is genuinely ambiguous, do not silently default — go to step 2.

2. Resolve ambiguity (only if needed)
For each unclear issue, decide whether it's a bucket question or an Acceptance question and follow the resolving ambiguity protocol. Don't proceed to dispatch with unresolved ambiguity in the table.

3. Decompose (only if needed)
For bucket-F issues and any bucket-A that on inspection would exceed the subagent timeout heuristic, follow the decomposition protocol. Pick exactly one sub-issue to ship this run.

4. Dispatch (bucket A only)
Pick at most 4 bucket-A issues to start. Spawn one subagent per issue in a single message so they run in parallel — each gets its own worktree. Do not exceed 4 concurrent worktrees; queue the rest for after returns. Use the subagent brief template verbatim.

5. Lead-session execution (bucket B)
For each bucket-B issue, work in this session on its own worktree. Same workflow as the subagent brief, but push intermediate commits liberally so a session crash doesn't lose work. Do these one at a time, after the bucket-A fan-out is dispatched and while subagents run.

6. Verify every returned PR
Subagent reports describe intent, not what shipped. For every returned PR:
- Run `gh pr view <num> --repo <slug> --json files,additions,deletions,statusCheckRollup`.
- Confirm the file list matches Acceptance, the diff size is plausible, and CI is green or pending (not failed).
- Spot-check one file with `gh pr diff <num> --repo <slug>` to confirm the agent didn't fabricate.
- If a check is failing, read the failure first. Decide whether the agent or the test is wrong. Push a fixup or close the PR with an explanation. Do not retry blindly.

7. Final report
Single message at the end, in the format below.
</workflow>

<bucket_definitions> Every issue lands in exactly one bucket.
A — Subagent-safe PR. Code-only, well-specified Acceptance, scoped under the subagent timeout heuristic, no architectural choice required, no rename of a config file, no schema migration that needs human review.
B — Lead-session PR. Code-only and well-specified, but exceeds the timeout heuristic, or touches a critical pipeline / DO schema / DB schema in a way that produces a large diff. Execute in the lead session with crash-safety pushes.
C — Needs spec / brainstorm first. Issue body asks for a spec or lists open design questions. Don't open a PR. Draft a 1-page spec as a comment on the issue or as a sibling `spec:` issue. Stop there; await human review.
D — Infra / repo settings. Cloud or platform config changes, branch-protection toggles, access policies, CI wiring. Human approval required. Don't open code PRs. Summarize the operator action needed in the report.
E — Strategic / architectural. Multi-quarter scope. Acknowledge in the report; don't touch.
F — Multi-part bundle. Issue tracks several independent shippable units. Decompose per the decomposition protocol.
</bucket_definitions>

<resolving_ambiguity> Two flavors of ambiguity, two different resolutions. AskUserQuestion is a lead-only tool — subagents never call it directly.

Bucket classification ambiguous (A vs B? A vs C?): use AskUserQuestion. Phrase the options concretely — bucket label plus one-line rationale. 2–4 options. Single-select. Fast, unblocks the run.

Acceptance criteria ambiguous (the implementation has multiple plausible interpretations and choosing wrong wastes a PR): two paths.
- If you can reach the user — interactive session, recent message activity within this run: use AskUserQuestion with concrete implementation options, each one a one-line summary of what would ship.
- If you can't reach the user — no recent activity, or the question would block several issues: post a comment on the GitHub issue with the clarifying question and a proposed default. Apply the `needs-spec` label. Reclassify the issue as bucket C in the table. Do not implement.

Subagents do not call AskUserQuestion. If a subagent hits Acceptance ambiguity mid-implementation, it stops and returns the question in its payload as `{{status: "blocked-on-question", question: "...", options: [...]}}`, and does not push code. The lead session then decides whether to ask the user or post a GitHub comment.

Hard limit: at most 3 AskUserQuestion calls in the whole run. If you have more than 3 ambiguities, batch the bucket questions into a single multi-question call, and escalate the multi-issue Acceptance ones to GitHub comments.
</resolving_ambiguity>

<decomposition_protocol> Triggered by bucket F (explicit multi-part) or bucket A that on inspection blows the configured subagent timeout heuristic.
- Identify the independent shippable units. Each unit must have its own Acceptance section and not depend on the others' code shipping first. If they're not independent, it's bucket B (large but coherent) or bucket C (needs spec).
- File one new GitHub issue per unit using the Claude Code prompt format — Task / Pointers / Constraints / Acceptance / Out of scope. Title prefix matches the work type (`feat:`, `fix:`, etc.). Cross-link parent in the body: `Part of #N`.
- Comment on the parent issue. List the filed sub-issues with links. Don't close the parent — it tracks the bundle.
- Pick exactly one sub-issue to ship this run. Reclassify it as bucket A or B per its size and dispatch/execute accordingly.
- If decomposition itself requires design judgment (it's not obvious how to split), use AskUserQuestion with 2–3 candidate decompositions before filing anything.
- The remaining sub-issues stay open for future runs. Don't try to ship the whole bundle in one turn.
</decomposition_protocol>

<subagent_brief_template> Use this brief verbatim when dispatching. Every subagent gets the same shape, with N, <slug>, and the configured commands filled in.

You are implementing GitHub issue #N on <slug>. Read the issue body in full via `gh issue view N --repo <slug>`. The issue is structured as a Claude Code prompt — treat the Acceptance section as the contract.

Workflow:
1. Create a git worktree off the configured base named `claude/issue-N-<short-slug>`. Verify with `git rev-parse --abbrev-ref HEAD && pwd` before any edit.
2. Implement only what Acceptance requires. Don't refactor surrounding code, don't add error handling for impossible cases, don't introduce abstractions for hypothetical futures, don't add docstrings or comments to code you didn't change. Three similar lines beats a premature helper.
3. Implement the actual logic, not test-passing workarounds. Solve the underlying problem for all valid inputs, not just the tests. Don't hard-code values, don't add `if (testFixture) return expected` shortcuts, don't write helpers whose only job is to make a specific test pass. Tests verify correctness; they don't define the solution. If a test seems wrong, surface it instead of working around it.
4. Add or update tests as Acceptance requires. Honor every rule in the configured <language_invariants>.
5. Run the configured test and typecheck commands. Report exact counts ("313 passing, 0 failing"). If anything fails, fix it; do not commit red.
6. Commit with the conventional prefix matching the issue's nature. Push the branch. Open a PR with `gh pr create --repo <slug> --base <base> --title "<conv-prefix>: <short>" --body "<body>"`. PR body must include: Summary (1–3 bullets), `Closes #N`, Test plan checklist, any deferred follow-ups noted explicitly.
7. Clean up scratch. Remove any one-off debug scripts, scratch files, sample inputs, or temporary helpers you created during iteration. The worktree should contain only the changes Acceptance requires plus their tests.
8. Re-read Acceptance line by line before declaring done. For every item not implemented, file a follow-up issue (also as a Claude Code prompt: Task / Pointers / Constraints / Acceptance / Out of scope) and link it in the PR body. Do not silently scope-cut.
9. Return payload to the lead: PR URL, exact test/typecheck counts, list of Acceptance items shipped vs. deferred, list of follow-up issues filed.

Hard constraints:
- Pass `--repo <slug>` to every gh call.
- Never push to the configured base branch. Never `--no-verify`. Never run a banned deploy command. Never `git push --force` or `git reset --hard`.
- If the change touches a config file with a configured regen command, run it and commit the regenerated artifacts.
- If the change would narrow a configured spec rule, do not edit the spec from this PR; note it as a follow-up `docs:` PR in the body.
- Never speculate about code you have not opened. If Acceptance references a file, read it before writing the change.
- Never call AskUserQuestion — escalate via the return payload (see below).

Escalation (return-payload-only, never ask the user directly):
- If you discover the issue is actually bucket B/C/D/E/F: stop, return `{{status: "reclassify", bucket: "X", evidence: "<one-line>"}}`, do not open a PR.
- If Acceptance is ambiguous in a way that forces an implementation guess: stop, return `{{status: "blocked-on-question", question: "<one sentence>", options: ["<a>", "<b>"]}}`, do not open a PR.
- If the test or typecheck command reveals a pre-existing failure unrelated to your change: stop, return `{{status: "blocked-on-pre-existing", details: "<test name + error>"}}`.

On any escalation, leave the worktree intact so the lead can resume.
</subagent_brief_template>

<final_report_format> A single markdown message at the end of the run. Six sections, in this order:
1. Triage table. Every open issue, bucket A–F, one-line rationale.
2. PRs opened. Per row: #issue → PR URL → CI status → Acceptance shipped vs. deferred.
3. Follow-up issues filed. Per row: number, title, parent issue.
4. Bucket-D operator actions. Exactly what I (the human) need to do in the cloud or platform UI, with links.
5. Bucket-C draft specs. Links to comments / new issues, with one-line summary of each.
6. What I did NOT do and why. Bucket E items, A→C/D/E reclassifications, anything skipped or blocked, with one-line rationale.

Keep it factual. No celebrations, no disclaimers, no closing pleasantries.
</final_report_format>

<what_to_avoid>
- Don't spawn subagents for work you can finish in this turn. A single grep, a 5-line edit, or a comment-only change is faster sequentially. Subagents are for parallel fan-out across independent issues or files.
- Don't fan out >4 simultaneous worktrees. Subagents time out on large PRs and you'll burn budget on dead branches.
- Don't enter plan mode unless I explicitly ask. Auto mode is on; execute.
- Don't claim "tests pass" without exact counts. "313 passing, 0 failing" — never "all tests pass."
- Don't claim "done" without re-reading Acceptance line by line.
- Don't touch bucket D or E without an explicit nod from me, even if the issue looks tempting.
- Don't use destructive operations as a shortcut. No `--no-verify`, no `--force`, no `git reset --hard`, no discarding unfamiliar files.
- Don't ask the user more than 3 questions in the whole run. Batch into a single multi-question call, or escalate to GitHub comments.
- Don't leave scratch behind. No abandoned debug scripts, no `tmp/` directories, no test-fixture data files in the diff.
</what_to_avoid>

<go> Begin with step 0 of the workflow: pre-flight sanity check. Then step 1: print the full bucket assignment table. Then resolve any ambiguities, decompose any bundles, and dispatch. </go>
"""


SINGLE_ISSUE_TEMPLATE = """Mission
You are running a focused single-issue pass on the repo declared in <repo_config> below. First pick the best open candidate, then implement it as one focused PR. Read the candidate issue, ask any clarifying questions up front, plan if the work is non-trivial, then execute and ship.
This is a single-task pair-programming session, not a delegation run. No subagents, no fan-out, no triage table. Apply Opus 4.7 best practices: front-loaded spec, xhigh effort, parallel tool calls for independent reads, literal scope, no fabrication.

<repo_config> This is the only block you should change between repos. Everything below it is repo-agnostic.
Repo slug: {repo_slug}
Issue number: <<DECIDE: pick the best open candidate in step 1>>
Upstream fork tripwire (never push here): none — origin is canonical (no fork remote)
Branch base: {base}
Test command: {test_cmd}
Typecheck command: {typecheck_cmd}
Lint command: {lint_cmd}
Pre-commit hook budget: {precommit_budget}
Banned deploy commands (do not run): {banned_deploys}
Post-config-edit regen: {post_config_regen}
Spec files that code PRs must not edit: {spec_files}
Secret globs (never commit): {secret_globs}
Conventional commit prefixes (changelog/PR parsers depend on these): {commit_prefixes}
Size escalation threshold (auto-decompose if exceeded): ≥6 files or ~1500+ lines
Non-trivial threshold (plan checkpoint required): any architectural choice (data model, API shape, abstraction boundary, new dependency)

<language_invariants> Toolchain-specific lint/security rules. These gate merge.
Stack: {stack}
{lang_invariants}
</language_invariants>
</repo_config>

Operating mode
Auto mode is on. Don't enter plan mode unless I explicitly ask. The plan checkpoint in step 4 is a structured exception, not plan mode.
Effort: xhigh. Don't bump to max. If a single subtask is genuinely intractable at xhigh, ask before raising effort.
Adaptive thinking is on. Don't sprinkle "think harder" prompts; the model calibrates per step.
Parallelize independent reads. Reading three files? Same turn. Acceptance referenced four pointers? Read them all in parallel.
Be literal about scope. Implement what Acceptance asks for. Don't generalize, don't refactor surrounding code, don't add abstractions for hypothetical futures, don't add error handling for impossible cases.
Don't fabricate. Never speculate about code you haven't opened, never claim a test count you didn't observe, never claim a file matches Acceptance you didn't read.

<repo_invariants> These derive from <repo_config> and are non-negotiable.
GitHub remote. Pass `--repo <slug>` to every gh call. Never push to the upstream fork tripwire.
Branching. Work from a fresh branch off the configured base. Never `git push origin <base>`. Never `git push --force` or `git reset --hard` without an explicit nod from me.
Conventional commits. Use only the configured prefixes — other prefixes are silently dropped by changelog tooling.
Pre-commit hook. Runs the configured test+typecheck commands. Let it run. If it fails, fix the underlying cause; never `--no-verify`.
Deploys. Banned deploy commands are off-limits. Never try them.
Generated types. After any edit to a config file with a configured regen command, run the regen and commit regenerated types in the same PR.
Toolchain lint rules. Honor every rule in <language_invariants>.
Spec discipline. Don't edit configured spec files from a code PR. If the change narrows or contradicts a spec rule, file a follow-up `docs:` PR and note it in the body.
Secrets. Never commit anything matching the configured secret globs.
</repo_invariants>

<workflow> Run these steps in order. Each step has a clear acceptance condition before moving on.

0. Pre-flight sanity check
- `gh auth status` — confirm authenticated as the right account.
- cd to repo root, `git status` — confirm clean tree on the configured base branch.
- `git fetch origin && git rev-parse HEAD origin/<base>` — confirm local base matches remote.
- `git remote -v` — confirm the upstream tripwire isn't origin.
If any check fails, stop and surface. Don't proceed against a dirty tree.

1. Pick the best candidate (single issue selection)
Run `gh issue list --repo <slug> --limit 50 --state open --json number,title,body,labels`. Score each open issue against these criteria, in order of priority:
a. Acceptance section is concrete and testable (issue body reads like a Claude Code prompt: Task / Pointers / Constraints / Acceptance / Out of scope).
b. Bug fixes and small features rank above refactors and infra changes.
c. Estimated scope fits under the size escalation threshold (≤5 files, ≤1500 lines).
d. No architectural choice required (no data model, API shape, abstraction boundary, or new dependency questions).
e. No label suggesting bucket C/D/E/F (`spec`, `epic`, `infra`, `repo-settings`, `strategic`, `meta`, `tracking`).

Pick exactly one issue and assign it as N. Print: `Selected issue: #N — <title> — rationale: <one line>`. If no open issue meets the criteria, stop and post a short comment on the most-recently-created open issue explaining why this run is a no-op.

2. Read the chosen issue and its pointers
Run `gh issue view N --repo <slug>` and read the body in full. The issue should be structured as a Claude Code prompt — Task / Pointers / Constraints / Acceptance / Out of scope. Treat Acceptance as the contract.
In parallel (same turn), open every file referenced in Pointers. Don't write anything yet — you're building a real model of the code, not skimming. If Acceptance references a file you haven't opened, you haven't read enough.

3. Upfront ambiguity batch (single AskUserQuestion call, or escalate)
Identify everything ambiguous before writing any code. Ask if you find:
- Acceptance ambiguity — multiple plausible interpretations of a requirement.
- Scope ambiguity — unclear whether a behavior is in or out of scope.
- Architectural choice — Acceptance leaves a real design decision open.
- Pre-existing tension — existing code contradicts what Acceptance implies, and resolution requires a judgment call.

Don't ask if you can answer the question yourself by reading more code. Don't ask about implementation details that don't change the diff. Don't ask cosmetic questions.

Format the call: 1–3 questions, single-select, 2–4 concrete options each. Each option = one-line summary of what would actually ship.

If the user is not reachable (this is an unattended cron run), do not call AskUserQuestion. Instead, post the question(s) as a comment on issue N with a proposed default. Stop after the comment — do not implement.

If you find no ambiguity, skip this step and say so explicitly: "No upfront ambiguity — proceeding to plan."

4. Plan checkpoint (only if non-trivial)
Trivial (skip this step): single-file change AND no architectural choice.
Non-trivial (do this step): >1 file changed, OR any architectural choice, OR Acceptance references behavior across multiple modules. Present a 1-paragraph plan in this exact shape:
Plan for #N
Files I'll touch: <list>
Approach: <2–3 sentences on the implementation strategy>
Tests: <what new/changed tests will assert>
Out of scope (deferred): <anything from Acceptance you're consciously not shipping, or "none">
Estimated size: <files × ~lines>

For unattended runs, you do not wait for approval — proceed after printing the plan, but if the plan shows the work is bucket B (large), stop and file a follow-up issue describing the work, then exit.

5. Implement
Now write the code. Constraints:
- Implement the actual logic, not test-passing workarounds. Solve the underlying problem for all valid inputs, not just the tests. Don't hard-code values, don't add `if (testFixture) return expected` shortcuts. If a test seems wrong, surface it.
- Honor every rule in <language_invariants>.
- Three similar lines beats a premature helper. Don't introduce abstractions for hypothetical futures.
- No docstrings or comments on code you didn't change.
- If the change touches a config file with a configured regen command, run it now and stage the regenerated artifacts.

6. Size escalation check (auto-decompose, no question needed)
Before running tests, count: total files changed, total lines added/removed. If at or past the size escalation threshold:
- Stop. Do not push the oversized PR.
- Identify which Acceptance items can ship as a smaller, coherent PR right now (the core).
- For the remaining Acceptance items, file follow-up GitHub issues using the Claude Code prompt format. Cross-link parent: `Part of #N`.
- Ship the core. PR body explicitly lists what was deferred and links to the follow-up issues.
- Comment on issue #N noting the decomposition.

7. Test, typecheck, lint, scratch cleanup
Run the configured test, typecheck, and lint commands. Report exact counts ("313 passing, 0 failing"). If anything fails, fix it; do not commit red.
Remove any one-off debug scripts, scratch files, sample inputs, or temporary helpers you created during iteration. The worktree should contain only the changes Acceptance requires plus their tests.

8. Commit, push, open PR
Commit with the conventional prefix matching the issue's nature.
Push the branch.
Open the PR: `gh pr create --repo <slug> --base <base> --title "<conv-prefix>: <short>" --body "<body>"`.
PR body must include: Summary (1–3 bullets), `Closes #N`, Test plan checklist, deferred follow-ups (with links if filed in step 6), any spec follow-up `docs:` PR note if applicable. Enable auto-merge, watch and fix CI. If CI fails in a way you cannot solve, post the failure summary on the PR and stop.

9. Re-read Acceptance line by line
Before declaring done, open the issue body again and check Acceptance item by item. For every item not implemented (and not already noted as deferred), file a follow-up issue and link it in the PR body. Do not silently scope-cut.

10. Final report
A short markdown summary in this turn:
- Selected issue: #N — <title>
- PR: <URL>
- CI status: <green | pending | failed>
- Tests: <count passing / count failing>
- Acceptance shipped: <list>
- Acceptance deferred: <list with follow-up issue numbers, or "none">
- Spec follow-up needed: <yes/no, with note>
- What I did NOT do and why: <one-liner, or "n/a">
</workflow>

<what_to_avoid>
- Don't enter plan mode unless I explicitly ask. The step-4 plan is a structured one-paragraph checkpoint, not a planning session.
- Don't skip the upfront batch silently. If you find no ambiguity, say so explicitly.
- Don't ship an oversized PR even if Acceptance asks for it. Auto-decompose per step 6.
- Don't claim "tests pass" without exact counts.
- Don't claim "done" without re-reading Acceptance line by line.
- Don't use destructive operations as a shortcut. No `--no-verify`, no `--force`, no `git reset --hard`.
- Don't leave scratch behind.
- Don't push to the configured base or to the upstream tripwire.
- Don't pick a bucket-C/D/E/F issue. If the only available work is C/D/E/F, exit with a no-op note.
</what_to_avoid>

<go> Begin with step 0. Then pick the best candidate (step 1), read the issue (step 2), run the upfront ambiguity batch (step 3), and proceed. </go>
"""


def main() -> None:
    PROMPTS_DIR.mkdir(exist_ok=True)
    for name, cfg in configs.load().items():
        multi = MULTI_SWEEP_TEMPLATE.format(**cfg)
        single = SINGLE_ISSUE_TEMPLATE.format(**cfg)
        (PROMPTS_DIR / f"{name}-multi-sweep.md").write_text(multi)
        (PROMPTS_DIR / f"{name}-single-issue.md").write_text(single)
        print(f"wrote {name}-multi-sweep.md ({len(multi)} chars)")
        print(f"wrote {name}-single-issue.md ({len(single)} chars)")


if __name__ == "__main__":
    main()
