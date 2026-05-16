"""Public example CONFIGS for claude-routines.

Each entry describes one repo. The generator produces two routines per repo:
- {name}-multi-sweep — daily batch triage with parallel subagent fan-out
- {name}-single-issue — daily focused one-PR-per-run pass

Required fields per entry:
- repo_slug         : "owner/repo" — what gh --repo gets
- base              : branch PRs target (e.g. "main" or "dev")
- cron_multi_sweep  : cron expression (UTC) for the multi-sweep routine
- cron_single_issue : cron expression (UTC) for the single-issue routine
- test_cmd / typecheck_cmd / lint_cmd : how the agent verifies its work
- precommit_budget  : human description of the pre-commit checks
- banned_deploys    : deploy commands the agent must never run
- post_config_regen : what to regenerate if a config file changes
- spec_files        : files code PRs must not edit (route to follow-up docs: PR)
- secret_globs      : never-commit patterns
- commit_prefixes   : conventional commit allowlist
- stack             : one-line stack summary
- lang_invariants   : toolchain-specific lint/security rules that gate merge

To use your own repos, create a `local_configs.py` next to this file:

    # local_configs.py (gitignored)
    CONFIGS = {
        "my-cool-app": {
            "repo_slug": "myorg/my-cool-app",
            "base": "main",
            "cron_multi_sweep": "0 13 * * *",
            "cron_single_issue": "0 14 * * *",
            # ... rest of required fields
        },
    }

The override completely replaces this file's CONFIGS at runtime. To extend
instead of replace, import this module and spread it: `CONFIGS = {**configs.CONFIGS, "mine": {...}}`.
"""

from __future__ import annotations

CONFIGS: dict[str, dict[str, str]] = {
    # Example 1: TypeScript on Cloudflare Workers, npm-based, Vitest.
    "example-ts-workers": {
        "repo_slug": "your-org/example-ts-workers",
        "base": "main",
        "cron_multi_sweep": "0 13 * * *",
        "cron_single_issue": "0 14 * * *",
        "test_cmd": "npm test",
        "typecheck_cmd": "npm run typecheck",
        "lint_cmd": "npm run lint",
        "precommit_budget": "~90s; runs npm test && npm run typecheck",
        "banned_deploys": "npm run deploy, wrangler deploy (CI owns deploys; running these collides with auto-deploy)",
        "post_config_regen": "if wrangler.jsonc changes touch types or bindings, regenerate via the project's typegen step and commit the regenerated artifacts in the same PR",
        "spec_files": "SECURITY.md and .github/CODEOWNERS — never weaken a documented security invariant from a code PR; route any such change to a follow-up `docs:` PR (the durable enforcement is the CODEOWNERS human-review gate, not this prompt rule)",
        "secret_globs": ".env*, .dev.vars, anything from `wrangler secret`",
        "commit_prefixes": "feat:, fix:, refactor:, test:, chore:, docs:, security:",
        "stack": "TypeScript on Cloudflare Workers (Hono), Vitest for tests",
        "lang_invariants": (
            "URL parsing in test mocks: always parse with `new URL(url).hostname === 'host.tld'`. "
            "Never use `startsWith`, `includes`, or substring on host strings — CodeQL `js/incomplete-url-substring-sanitization` gates merge. "
            "Outbound fetches to user-supplied URLs must use `redirect: 'manual'`. "
            "DNS errors (NXDOMAIN/NODATA) return `null`, never throw."
        ),
    },
    # Example 2: TypeScript on Cloudflare Workers, pnpm + monorepo with React client.
    # Note: this example uses a dev→main flow (PRs target dev, not main).
    "example-pnpm-monorepo": {
        "repo_slug": "your-org/example-pnpm-monorepo",
        "base": "dev",
        "cron_multi_sweep": "0 15 * * *",
        "cron_single_issue": "0 16 * * *",
        "test_cmd": "pnpm test",
        "typecheck_cmd": "pnpm check",
        "lint_cmd": "pnpm lint",
        "precommit_budget": "Quality gate = `pnpm lint && pnpm test && pnpm check`; all three must pass before commit",
        "banned_deploys": "pnpm deploy, wrangler deploy (CI/Workers Builds owns deploys)",
        "post_config_regen": "if `apps/web/wrangler.toml` changes bindings, regenerate worker-configuration types in the same PR",
        "spec_files": "none codified as a single SPEC file; honor existing docs/ entries and route any contradiction to a follow-up `docs:` PR",
        "secret_globs": ".env*, .dev.vars, anything from `wrangler secret`",
        "commit_prefixes": "feat:, fix:, refactor:, test:, chore:, docs:",
        "stack": (
            "TypeScript on Cloudflare Workers + React 19 client (Vite), pnpm + Turborepo monorepo, "
            "Hono backend, tRPC, TanStack Query, Drizzle ORM, Vitest, ESLint + Prettier"
        ),
        "lang_invariants": (
            "URL parsing in test mocks: parse with `new URL(url).hostname`. Never `startsWith`/`includes` substring matching on URL host strings. "
            "ESLint rule: remove unused imports and unused top-level variables entirely. The `_` prefix is allowed for function args and caught errors only (e.g. `(_req, res)`, `catch (_e)`). "
            "Feature branches target `dev`, not `main`. Never push directly to `dev` or `main`."
        ),
    },
    # Example 3: Python 3.12, FastAPI, async SQLAlchemy, pytest.
    "example-python-fastapi": {
        "repo_slug": "your-org/example-python-fastapi",
        "base": "main",
        "cron_multi_sweep": "0 19 * * *",
        "cron_single_issue": "0 20 * * *",
        "test_cmd": "pytest",
        "typecheck_cmd": "mypy .",
        "lint_cmd": "ruff check .",
        "precommit_budget": "Run `ruff check . && mypy . && pytest` before any commit",
        "banned_deploys": "(none codified at the repo level — do not run any deploy command; CI owns deploys)",
        "post_config_regen": "if SQLAlchemy models change schema, generate an Alembic migration (`alembic revision --autogenerate`) and commit it in the same PR. Never edit a committed migration.",
        "spec_files": "SPEC.md (never modify from a code PR — route any spec change to a follow-up `docs:` PR)",
        "secret_globs": ".env*",
        "commit_prefixes": "feat:, fix:, refactor:, test:, chore:, docs:",
        "stack": (
            "Python 3.12+, FastAPI (async), SQLAlchemy 2.0 async (`AsyncSession`), Pydantic v2, "
            "Celery 5.x + Redis, structlog, PostgreSQL 16, Alembic migrations, pytest + pytest-asyncio"
        ),
        "lang_invariants": (
            "Type hints everywhere; no `Any` unless absolutely necessary. mypy in strict mode. "
            "ruff with line-length=100, target=py312. `from __future__ import annotations` in every module. "
            "Logging via structlog — never `print()`. All DB operations are async (`AsyncSession`, `async_sessionmaker`). "
            "All timestamps UTC (`TIMESTAMPTZ`). `@pytest.mark.asyncio` on every async test. "
            "Stage specific files when committing — never `git add .` or `git add -A`."
        ),
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
