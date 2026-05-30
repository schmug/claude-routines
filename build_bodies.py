"""Convert ./shims/*.md into RemoteTrigger create-bodies under ./bodies/.

Each body is a complete JSON payload ready to pass as the `body` argument
to `RemoteTrigger action=create` inside Claude Code:

- bodies/<name>.json          — implementer routine (issues.opened event)
- bodies/<name>-merger.json   — merger routine (pull_request.opened event),
                                 only when shims/<name>-merger.md exists

Run after gen_routines.py. Requires $CLAUDE_ENVIRONMENT_ID to be set.

NOTE: The event-trigger filter JSON uses the field path
  event_trigger.github.filter.Author.is_one_of
as documented in cc-routine README §4. Confirm this key path against your
platform's `RemoteTrigger action=list` output before deploying; adjust and
note any divergence in your deployment notes.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import configs

REPO_ROOT = Path(__file__).resolve().parent
SHIMS_DIR = REPO_ROOT / "shims"
BODIES_DIR = REPO_ROOT / "bodies"


def _env_id() -> str:
    value = os.environ.get("CLAUDE_ENVIRONMENT_ID", "").strip()
    if not value:
        sys.exit(
            "ERROR: set CLAUDE_ENVIRONMENT_ID before running. "
            "Discover yours via RemoteTrigger action=list inside Claude Code."
        )
    return value


def _implementer_body(
    shim: str,
    *,
    repo: str,
    author: str,
    prefix: str,
    display: str,
    environment_id: str,
) -> dict[str, object]:
    """Build a RemoteTrigger create-body for the implementer (issues.opened)."""
    return {
        "name": display,
        "enabled": True,
        "event_trigger": {
            "github": {
                "event": "issues",
                "action": "opened",
                "filter": {"Author": {"is_one_of": [author]}},
            }
        },
        "job_config": {
            "ccr": {
                "environment_id": environment_id,
                "events": [{
                    "data": {
                        "message": {"role": "user", "content": shim},
                        "type": "user",
                    },
                }],
                "session_context": {
                    # Tier-1 (build-time enforced) least-privilege tool allowlist.
                    # WebFetch/WebSearch excluded: not needed for issue triage, and
                    # are the cleanest exfiltration channel for injected instructions.
                    # See SECURITY.md for the residual-risk discussion.
                    "allowed_tools": ["Bash", "Read", "Write", "Edit", "Glob", "Grep"],
                    "autofix_on_pr_create": True,
                    "outcomes": [{"git_repository": {"git_info": {"branches": [f"claude/{prefix}-*"], "repo": repo}}}],
                    "sources": [{"git_repository": {"url": f"https://github.com/{repo}"}}],
                },
            },
        },
    }


def _merger_body(
    shim: str,
    *,
    repo: str,
    author: str,
    prefix: str,
    display: str,
    environment_id: str,
) -> dict[str, object]:
    """Build a RemoteTrigger create-body for the merger (pull_request.opened)."""
    return {
        "name": display,
        "enabled": True,
        "event_trigger": {
            "github": {
                "event": "pull_request",
                "action": "opened",
                "filter": {"Author": {"is_one_of": [author]}},
            }
        },
        "job_config": {
            "ccr": {
                "environment_id": environment_id,
                "events": [{
                    "data": {
                        "message": {"role": "user", "content": shim},
                        "type": "user",
                    },
                }],
                "session_context": {
                    "allowed_tools": ["Bash", "Read", "Write", "Edit", "Glob", "Grep"],
                    "autofix_on_pr_create": False,
                    "outcomes": [{"git_repository": {"git_info": {"branches": [f"claude/{prefix}-*"], "repo": repo}}}],
                    "sources": [{"git_repository": {"url": f"https://github.com/{repo}"}}],
                },
            },
        },
    }


def main() -> None:
    environment_id = _env_id()
    BODIES_DIR.mkdir(exist_ok=True)
    for name, cfg in configs.load().items():
        shim_path = SHIMS_DIR / f"{name}.md"
        if not shim_path.exists():
            print(f"skip {name}: shims/{name}.md not found (run gen_routines.py first)")
            continue

        shim = shim_path.read_text()
        display = f"{name} implementer"
        body = _implementer_body(
            shim,
            repo=cfg["repo_slug"],
            author=cfg["author"],
            prefix=name,
            display=display,
            environment_id=environment_id,
        )
        out_path = BODIES_DIR / f"{name}.json"
        out_path.write_text(json.dumps(body, indent=2))
        print(f"{name}: {out_path.stat().st_size} bytes ({cfg['repo_slug']}, event=issues.opened, author={cfg['author']})")

        merger_shim_path = SHIMS_DIR / f"{name}-merger.md"
        if merger_shim_path.exists():
            merger_shim = merger_shim_path.read_text()
            merger_display = f"{name} merger"
            merger_body = _merger_body(
                merger_shim,
                repo=cfg["repo_slug"],
                author=cfg["author"],
                prefix=name,
                display=merger_display,
                environment_id=environment_id,
            )
            merger_out = BODIES_DIR / f"{name}-merger.json"
            merger_out.write_text(json.dumps(merger_body, indent=2))
            print(f"{name}-merger: {merger_out.stat().st_size} bytes ({cfg['repo_slug']}, event=pull_request.opened, author={cfg['author']})")


if __name__ == "__main__":
    main()
