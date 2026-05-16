# Proposal: deterministic auto-merge gate (UNDER EVALUATION — not adopted)

> **Status:** Proposal. **Not implemented in this repo. Not endorsed yet.**
> This intentionally **diverges from a deliberate security decision** of
> `claude-routines`: the existing system is **no-auto-merge** by design (see
> root `README.md` "Security" and `SECURITY.md`). This document proposes adding
> auto-merge for a narrow trusted/low-risk class, gated by a deterministic,
> unit-tested control. Adopting it **reverses that stance** and is an explicit
> owner decision, not a foregone conclusion.

## Why this exists

These two documents (`design-spec.md`, `implementation-plan.md`) were written
and executed *before* discovering that `claude-routines` already implements a
more mature, multi-repo routine system with a prompt-level author-trust gate
and a deliberate no-auto-merge posture. They are preserved here as the design
rationale for the **one piece with net-new value**: a deterministic,
exit-code-contract, unit-tested merge gate (vs. an injectable prompt-level
trust check).

## What was actually built (and where)

A working implementation was vendored into **`schmug/dmarcheck`** for a pilot,
*not* into this repo:

- PR `schmug/dmarcheck#306` (merged) — gate + scripts + prompts
- PR `schmug/dmarcheck#311` — gate self-modification denylist fix
- The gate (`scripts/routine-gate/`, ~46 unit tests) validated end-to-end
  against a real PR

The hand-written Routine prompts and the manual go-live steps in
`implementation-plan.md` are **superseded** by this repo's
`gen_routines.py` / `RemoteTrigger` model. Only the gate and the design
reasoning are candidates for adoption here.

## The open decision

`claude-routines` chose no-auto-merge as a security posture. The deterministic
gate makes auto-merge *defensible* for a tightly-bounded class (allowlisted
issue author + `spec-approved` label + small + no risk-path + CI green + no
scope drift, fail-closed). Whether that bounded auto-merge is worth reversing
the no-auto-merge stance is the decision tracked in the accompanying proposal
issue. **Do not treat these documents as describing this repo's behavior.**

## Caveat in the documents themselves

`design-spec.md` / `implementation-plan.md` reference dmarcheck-specific
branch-protection scripting. That approach was **wrong**: dmarcheck's
protection is owned by this repo's `dmarcheck-ruleset-update.json` (a GitHub
*ruleset*, stronger than the legacy branch-protection the plan applied — since
removed). Read those branch-protection sections as obsolete.
