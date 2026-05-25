# Deployed routines (template)

Copy this file to `MANIFEST.local.md` after deploying and fill in your trigger
IDs. `MANIFEST.local.md` is gitignored so your trigger IDs and environment IDs
stay out of the public repo.

One row per target repo. Each row is a single event-driven `cc-routine`
session that fires on `issues.opened` filtered to the trusted author. See
[`README.md`](README.md) for the deployment flow and
[`SECURITY.md`](SECURITY.md) for the Tier-2 controls each target repo also
needs.

| Repo | Trusted author(s) | Environment ID | Trigger ID | Notes |
|---|---|---|---|---|
| your-org/your-repo | your-handle | env_... | trig_... | e.g. PRs target `dev`, not `main` |
