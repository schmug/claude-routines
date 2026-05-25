# refactor: convert claude-routines into a Cowork plugin + thin per-repo shims (event-driven single-issue only)

## Task

Refactor this repo from "Python codegen → monolithic per-routine prompts" into "Cowork plugin with shared skills + thin per-repo shims." The plugin is installable in any repo and provides the workflow; each per-repo shim is a ~30-line routine Instructions block that pulls in plugin skills and supplies repo-specific facts.

Background that led to this decision is in two recent sessions with the maintainer:

- The current scheduled `single-issue` routine fires daily, picks one open issue, and ships a PR. We are moving to **GitHub event-driven** triggers (`issues.opened`, filtered to `author = schmug`) instead. The session now knows N from the event.
- The current `multi-sweep` pattern is being **retired entirely**. Event-driven covers fresh issues; the safety-net case is small enough that we don't need a daily cron job duplicating effort. Generation, build, and docs should drop multi-sweep.
- The prompt is too long. Per [the Opus 4.7 best-practices blog](https://claude.com/blog/best-practices-for-using-claude-opus-4-7-with-claude-code), explicit `xhigh effort`, `adaptive thinking on`, `auto mode on`, and `don't sprinkle 'think harder'` instructions are now defaults and should be **removed** from generated content. Per [the large-codebases blog](https://claude.com/blog/how-claude-code-works-in-large-codebases-best-practices-and-where-to-start), repo-specific invariants belong in each target repo's `CLAUDE.md`, not duplicated in the routine prompt.

The new shape is documented under Acceptance below.

## Pointers

Read these before planning:

- `README.md` — current architecture (CONFIGS → templates → prompts → RemoteTrigger bodies). The "Why this lives in its own repo" and "RemoteTrigger create body shape (gotchas)" sections stay relevant; the "Layout" and "Routine patterns" sections need rewriting.
- `SECURITY.md` — current security model (untrusted-content preamble, author-trust gate, build-time tool allowlist, Tier-2 repo controls). **All of this must survive the refactor.** The event-trigger filter (`Author is one of schmug`) is an *additional* layer, not a replacement for the prompt-level gate.
- `configs.py` — current CONFIGS schema (3 public template entries). The schema stays roughly the same; trim any fields that only existed to feed multi-sweep.
- `gen_routines.py` — current template engine. Refactor target: produce per-repo shim files in `shims/<repo>.md` instead of full prompts in `prompts/*.md`. Multi-sweep template deleted.
- `build_bodies.py` — current RemoteTrigger body builder. Refactor target: each generated body must carry the new GitHub trigger config (event = `issues.opened`, filter Author `is_one_of` `["schmug"]`) **and** the shim content as Instructions. No scheduled cron.
- `MANIFEST.template.md` — operator deployment tracker. Update to reflect "one routine per repo" (no more multi-sweep row) and the event-trigger fields.
- Open issues #2, #3, #4, #7 — security and auto-merge concerns. The refactor must not regress on any of them. In particular, do not introduce auto-merge as part of this PR; #7 is still open and undecided.

There is no `prompts/` or `bodies/` directory committed (both are gitignored). You will generate the new artifacts under `shims/` and `bodies/` after the refactor; both new dirs are gitignored too.

A worked example of the new per-routine prompt content (the "shim target," approximately what one shim should produce) lives in the maintainer's hand-drafted PhishSOC routine. It establishes the prose that becomes the three skills below. Treat it as the source content for skill text where you need a starting point.

## Constraints

- **Preserve all security controls.** The untrusted-content preamble, author-trust gate, build-time tool allowlist, and Tier-2 repo settings discussion in `SECURITY.md` must remain. The author-trust gate **must** appear at the start of `implement-from-issue` (defense in depth — the trigger filter is not enough on its own; `SECURITY.md` already explains why).
- **No auto-merge in this PR.** Issue #7 is undecided. The shim must not set or imply `--auto-merge`.
- **Keep the Python codegen pipeline.** Do not rewrite in TypeScript, Go, etc. Existing dependencies stay.
- **Preserve `local_configs.py` gitignore.** Never commit a real CONFIGS dict; only `configs.py` is committed.
- **`shims/` and `bodies/` are gitignored, regenerated outputs.** Source of truth is `configs.py` + `templates/` + `.claude/skills/`.
- **No multi-sweep anywhere.** Delete its template, its config fields that aren't shared, its README section, its MANIFEST row. Operators retiring existing scheduled multi-sweep routines get a one-paragraph note in the README pointing them at `RemoteTrigger action=update enabled=false`.
- **No new MCP connectors.** The plugin uses the account-default connections already documented in the README.
- **Plugin scaffolding must follow the Cowork plugin convention** as documented at https://code.claude.com/docs/en/plugins and https://claude.com/blog/how-claude-code-works-in-large-codebases-best-practices-and-where-to-start — specifically `plugin.json` at the repo root and skills under `.claude/skills/<name>/SKILL.md`. If the convention has evolved since this issue was filed, follow current docs and note the divergence in the PR body.
- **Conventional commit prefix**: `refactor:` for the main commit. Sub-PRs (see Decomposition below) use prefixes matching their content (`feat:` for new skills/plugin manifest, `refactor:` for codegen changes, `docs:` for README/SECURITY rewrites).
- **Idempotent regeneration.** Running `python3 gen_routines.py && python3 build_bodies.py` twice in a row must produce byte-identical output.

## Acceptance

The PR (or PR series, after decomposition) ships:

**1. Plugin scaffolding at the repo root.**

- `plugin.json` declaring the plugin name (`cc-routine`), version, description, and the three skills below.
- `.claude/skills/implement-from-issue/SKILL.md` — the workflow: pre-flight, read issue + pointers in parallel, plan-comment for non-trivial issues (without waiting), implement with literal scope, tiered ambiguity handling (design ambiguity → comment + `needs-decision` + exit; low-stakes → pick default + document in PR body `## Choices made` section), test/typecheck with exact counts, scratch cleanup, size-escalation auto-decompose at ≥6 files or ~1500+ lines, commit/push/open PR (no auto-merge), re-read Acceptance line by line. Must include the author-trust gate as the first concrete action.
- `.claude/skills/routine-anti-noise/SKILL.md` — skip-on-label gate (`needs-decision`, `needs-you`, `awaiting-human`, `impl-blocked`, `discussion`, `question`, `wontfix`, `duplicate`), skip-and-label rule (don't re-state known blockers), consolidation pin format.
- `.claude/skills/routine-event-resolve/SKILL.md` — resolve N from event payload, fall back to `gh issue list --repo <slug> --author <author> --state open --sort created --limit 1 --json number,createdAt` with a 15-minute freshness check, exit cleanly if neither path yields N. Includes the content-triage rules (Path A: CC prompt format; Path B: inferable spec via bug-report / feature-with-acceptance; Path C: discussion / vague → comment + `needs-format` + exit).
- Each `SKILL.md` includes a YAML frontmatter block with `name`, `description`, and an explicit `triggers:` list (per [the onboarding-Claude-Code blog](https://claude.com/blog/onboarding-claude-code-like-a-new-developer-lessons-from-17-years-of-development)'s "ALWAYS load when ..." pattern).

**2. Shim template + codegen.**

- `templates/shim.md.j2` (or equivalent) — a Jinja template producing ~30 lines per repo with: repo slug, branch base, the three skills invoked by name (`Use the implement-from-issue, routine-anti-noise, and routine-event-resolve skills against the triggering issue.`), a one-line note that all repo-specific conventions live in that repo's `CLAUDE.md` (commit prefixes, test/typecheck commands, banned deploys, post-config regen, secret globs, spec-file discipline), and the untrusted-content preamble.
- `gen_routines.py` regenerated: reads CONFIGS, writes one shim per repo to `shims/<repo>.md`. Multi-sweep code path deleted.
- `build_bodies.py` regenerated: reads each shim, produces a RemoteTrigger create body in `bodies/<repo>.json` with the new event-trigger config attached (`event: issues.opened`, `filter: { Author: is_one_of: [<author>] }`) and the shim as the Instructions field. No scheduled cron in the body. Multi-sweep code path deleted.

**3. CONFIGS schema update.**

- `configs.py` example entries trimmed: remove `cron_multi_sweep` and any multi-sweep-only fields. Keep `repo_slug`, `base`, `test_cmd`, `typecheck_cmd`, `author` (default `schmug`), and whatever other fields the new shim template references.
- Each example config gets a one-line comment pointing at the per-repo CLAUDE.md as the source for things removed from CONFIGS.

**4. Docs.**

- `README.md` rewritten: new architecture diagram (CONFIGS + plugin → shims + bodies), "Adopt for your own repos" steps updated for event-driven setup (install the plugin, add a routine pointing at the shim, set the GitHub trigger with Author filter), "Routine patterns" section reduced to one pattern (single-issue, event-driven), the "RemoteTrigger create body shape (gotchas)" section kept verbatim because it's still accurate.
- `SECURITY.md` updated: add a paragraph noting that the event-trigger Author filter is a defense-in-depth layer on top of the prompt-level author-trust gate, not a replacement. The Tier-2 repo controls section stays.
- `MANIFEST.template.md` updated: row schema becomes `repo | trigger_id | environment_id | github_app_installed | notes`. Drop the multi-sweep row.

**5. Migration note.**

- A new section in README (or a separate `MIGRATION.md`) explaining how operators retire existing scheduled routines: `RemoteTrigger action=update <trig_id> body={"enabled": false}` for each old routine, then `RemoteTrigger action=create` each new event-driven one from `bodies/<repo>.json`. List the maintainer's six active repos as examples: `dmarcheck`, `donthype-me`, `loomwiki`, `govpeer`, `clodcast`, `flawd-code`.

**6. Tests / smoke.**

- A minimal `tests/test_gen.py` (or extension of any existing test) that:
  - Parses one example CONFIGS entry, runs the generator, asserts the produced shim contains the expected skill invocations and the author from the config.
  - Runs the generator twice and asserts byte-identical output (idempotence).
- If no test framework is currently set up, add one minimally (pytest is fine; nothing fancy).

**7. CI is green.** Whatever CI exists must pass. If none exists, no requirement to add it.

## Out of scope

- **Deploying** the new shims (the RemoteTrigger create calls). The PR produces `bodies/<repo>.json` but does not call the create API. The maintainer will do that step manually after reviewing the bodies.
- **The auto-merge gate** (issue #7). Stay neutral.
- **OAuth credential blast radius** mitigations (issue #2). Document the current state if it changes; don't introduce new mitigations.
- **Per-repo CLAUDE.md updates** in the target repos (`dmarcheck`, `donthype-me`, `loomwiki`, `govpeer`, `clodcast`, `flawd-code`). Each repo gets its own follow-up PR documenting test/typecheck commands, commit prefixes, etc., that the shim now expects to find in CLAUDE.md.
- **Rewriting in another language.** Stay in Python.
- **Removing the Python codegen entirely** in favor of a static plugin. The codegen still earns its keep for generating per-repo bodies with environment IDs and filter configs.

## Decomposition hint

If diff size hits the auto-decompose threshold (≥6 files or ~1500+ lines per the workflow rules), ship in this order:

1. **`feat: scaffold cc-routine plugin with three skills`** — `plugin.json` + the three `SKILL.md` files only. No codegen changes. Smallest reviewable unit; lets the maintainer install the plugin in PhishSOC and validate the skills against a real fire before the codegen catches up.
2. **`refactor: regenerate routines from plugin shims, drop multi-sweep`** — `templates/shim.md.j2`, `gen_routines.py`, `build_bodies.py`, `configs.py` schema trim. Tests included. Multi-sweep code paths deleted.
3. **`docs: update README + SECURITY + MANIFEST for event-driven plugin architecture`** — all docs updates in one PR, including the migration note.

If you ship in three PRs, file each as a follow-up issue in CC prompt format cross-linked with `Part of #<this issue>`, then ship Part 1 from this run.

## Notes for the implementer

- The Opus 4.7 defaults are now `xhigh effort`, `adaptive thinking on`, `auto mode on`. Don't restate any of those in the new SKILL.md files. Only specify things that **differ** from defaults.
- Skill descriptions should follow the "ALWAYS load when X" pattern the Brendan MacLean blog highlights. For example, `routine-event-resolve` should trigger "ALWAYS load when the session was fired by a GitHub issues.opened event."
- The plan-comment-and-proceed pattern is intentional and answers a specific question: routines run without a user to approve a checkpoint. Don't add `AskUserQuestion` anywhere — it has no responder. Comment on the issue or fail closed.
- The shim's job is to be small. If you find yourself writing more than ~50 lines per repo, push more content into a skill.

_Filed by the maintainer based on a multi-session design discussion. The source-of-truth PhishSOC single-issue routine prompt that gave rise to the three skills is attached as a starting point._
