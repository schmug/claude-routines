"""Public example CONFIGS for claude-routines.

Each entry describes one repo. gen_routines.py produces shim files in
shims/ and build_bodies.py converts them to RemoteTrigger create-bodies
in bodies/.

Required fields per entry:
  repo_slug      "owner/repo" — what gh --repo gets
  base           branch PRs target (e.g. "main" or "dev")
  author         GitHub login of the trusted issue author; drives the
                 event-trigger Author filter and the implementer's
                 author-trust gate

Optional fields:
  enable_merger  "true" to also emit a merger shim (pull_request.opened
                 event, merge-pr-with-gate skill). Default: off. Requires
                 Tier-2 branch protection on <base> before deploying.

Reference fields (not used by the generator; document here as a reminder
of what each target repo's CLAUDE.md must supply to the implementer skill
at runtime):
  test_cmd       e.g. "npm test"
  typecheck_cmd  e.g. "npm run typecheck"

All other per-repo invariants (lint_cmd, banned_deploys, secret_globs,
commit_prefixes, stack, lang_invariants, etc.) live in the target repo's
CLAUDE.md — the implementer skill reads them at runtime.

To use your own repos, create a local_configs.py next to this file:

    # local_configs.py (gitignored)
    CONFIGS = {
        "my-cool-app": {
            "repo_slug": "myorg/my-cool-app",
            "base": "main",
            "author": "your-github-login",
            "test_cmd": "npm test",
            "typecheck_cmd": "npm run typecheck",
        },
    }

The override completely replaces this file's CONFIGS at runtime. To extend
instead of replace, import this module and spread it:
    CONFIGS = {**configs.CONFIGS, "mine": {...}}
"""

from __future__ import annotations

CONFIGS: dict[str, dict[str, str]] = {
    # Example 1: TypeScript on Cloudflare Workers, npm-based.
    # All invariants beyond repo_slug/base/author live in target repo's CLAUDE.md.
    "example-ts-workers": {
        "repo_slug": "your-org/example-ts-workers",
        "base": "main",
        "author": "your-github-login",
        "test_cmd": "npm test",
        "typecheck_cmd": "npm run typecheck",
    },
    # Example 2: TypeScript pnpm monorepo (PRs target dev, not main).
    "example-pnpm-monorepo": {
        "repo_slug": "your-org/example-pnpm-monorepo",
        "base": "dev",
        "author": "your-github-login",
        "test_cmd": "pnpm test",
        "typecheck_cmd": "pnpm check",
    },
    # Example 3: Python 3.12 + FastAPI.
    "example-python-fastapi": {
        "repo_slug": "your-org/example-python-fastapi",
        "base": "main",
        "author": "your-github-login",
        "test_cmd": "pytest",
        "typecheck_cmd": "mypy .",
    },
}


def load() -> dict[str, dict[str, str]]:
    """Return CONFIGS, with local_configs.py taking precedence if present."""
    try:
        import local_configs  # type: ignore[import-not-found]

        local = getattr(local_configs, "CONFIGS", None)
        if isinstance(local, dict) and local:
            return local
    except ImportError:
        pass
    return CONFIGS
