"""Convert ./prompts/*.md into RemoteTrigger create-bodies under ./bodies/.

Each body is a complete JSON payload ready to POST as the `body` argument to
RemoteTrigger action=create inside Claude Code. Routine metadata (cron, base,
display name) is read from configs.py / local_configs.py — see configs.py.

Run after gen_routines.py. Requires $CLAUDE_ENVIRONMENT_ID to be set.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import configs

REPO_ROOT = Path(__file__).resolve().parent
PROMPTS_DIR = REPO_ROOT / "prompts"
BODIES_DIR = REPO_ROOT / "bodies"


def _env_id() -> str:
    value = os.environ.get("CLAUDE_ENVIRONMENT_ID", "").strip()
    if not value:
        sys.exit(
            "ERROR: set CLAUDE_ENVIRONMENT_ID before running. "
            "Discover yours via RemoteTrigger action=list inside Claude Code."
        )
    return value


def _build(prompt: str, *, cron: str, repo: str, prefix: str, display: str, autofix: bool, environment_id: str) -> dict:
    """Build one RemoteTrigger create-body envelope around a prompt."""
    return {
        "name": display,
        "cron_expression": cron,
        "enabled": True,
        "job_config": {
            "ccr": {
                "environment_id": environment_id,
                "events": [{
                    "data": {
                        "message": {"role": "user", "content": prompt},
                        "type": "user",
                    },
                }],
                "session_context": {
                    "allowed_tools": ["Bash", "Read", "Write", "Edit", "Glob", "Grep", "WebFetch", "WebSearch"],
                    "autofix_on_pr_create": autofix,
                    "outcomes": [{"git_repository": {"git_info": {"branches": [f"claude/{prefix}-routine"], "repo": repo}}}],
                    "sources": [{"git_repository": {"url": f"https://github.com/{repo}"}}],
                },
            },
        },
    }


def main() -> None:
    environment_id = _env_id()
    BODIES_DIR.mkdir(exist_ok=True)
    for name, cfg in configs.load().items():
        for pattern, cron_key in (("multi-sweep", "cron_multi_sweep"), ("single-issue", "cron_single_issue")):
            routine_name = f"{name}-{pattern}"
            prompt = (PROMPTS_DIR / f"{routine_name}.md").read_text()
            # autofix_on_pr_create only composes with single-issue (one PR per run).
            # multi-sweep dispatches subagents that each open their own PR.
            autofix = pattern == "single-issue"
            display = f"{name} {pattern.replace('-', ' ')}"
            body = _build(
                prompt,
                cron=cfg[cron_key],
                repo=cfg["repo_slug"],
                prefix=name,
                display=display,
                autofix=autofix,
                environment_id=environment_id,
            )
            out_path = BODIES_DIR / f"{routine_name}.json"
            out_path.write_text(json.dumps(body))
            print(f"{routine_name}: {len(out_path.read_text())} bytes ({cfg['repo_slug']}, cron={cfg[cron_key]}, autofix={autofix})")


if __name__ == "__main__":
    main()
