"""Contract tests for implement-from-issue step 9: gate-conditional landing (#27).

These assert the skill text's two-branch landing contract — gated repos may
squash-merge through required checks, ungated repos keep stop-at-open-PR —
plus the invariants #27 requires to stay untouched.
"""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILL_PATH = REPO_ROOT / "plugins" / "cc-routine" / "skills" / "implement-from-issue" / "SKILL.md"
MARKETPLACE_PATH = REPO_ROOT / ".claude-plugin" / "marketplace.json"
PLUGIN_PATH = REPO_ROOT / "plugins" / "cc-routine" / ".claude-plugin" / "plugin.json"
PILOT_PATH = REPO_ROOT / "docs" / "implementer-merge-pilot.md"


def _skill_text() -> str:
    return SKILL_PATH.read_text()


def _frontmatter() -> str:
    return _skill_text().split("---")[1]


def _step9() -> str:
    """Step 9's body: from its heading to step 10's heading.

    (The PR-body template inside step 9 contains fenced '## ' lines, so
    slicing to the next literal '## ' would truncate mid-step.)
    """
    text = _skill_text()
    start = text.index("## 9.")
    end = text.index("\n## 10.", start)
    return text[start:end]


def test_step9_no_unconditional_merge_ban() -> None:
    """The old blanket ban is gone from step 9."""
    assert "Do NOT enable auto-merge. Do NOT merge your own PR." not in _skill_text()


def test_step9_probes_gate_at_runtime() -> None:
    """Gate detection is per-target-repo at runtime via the GitHub API."""
    step9 = _step9()
    assert "rulesets" in step9, "step 9 must probe rulesets"
    assert "/protection" in step9, "step 9 must probe classic branch protection"
    assert "required status check" in step9.lower(), "gate = required status checks"


def test_step9_detection_fails_closed() -> None:
    """Detection error or zero required checks = ungated; UNKNOWN is never a pass."""
    step9 = _step9()
    assert "fail closed" in step9.lower() or "fail-closed" in step9.lower()
    assert "UNKNOWN" in step9


def test_step9_gated_branch_squash_only() -> None:
    """Gated path merges by squash (auto-merge or direct once green), never other forms."""
    step9 = _step9()
    assert "--squash" in step9
    assert "--auto" in step9


def test_step9_ungated_branch_unchanged() -> None:
    """Ungated path keeps today's behavior: leave the PR open, name the missing gate."""
    step9 = _step9()
    assert "leave the PR open" in step9.lower() or "leave the pr open" in step9.lower()
    assert "missing gate" in step9.lower() or "gate is missing" in step9.lower()


def test_frontmatter_no_unconditional_no_merge_promise() -> None:
    assert "without auto-merge" not in _frontmatter()


def test_marketplace_description_gate_conditional() -> None:
    manifest = json.loads(MARKETPLACE_PATH.read_text())
    desc = manifest["plugins"][0]["description"]
    assert "never merges" not in desc
    assert "gate" in desc.lower()


def test_plugin_description_gate_conditional() -> None:
    manifest = json.loads(PLUGIN_PATH.read_text())
    desc = manifest["description"]
    assert "never merges" not in desc
    assert "gate" in desc.lower()


def test_pilot_scenarios_documented() -> None:
    """A #16-style pilot doc covers the gated landing path end-to-end."""
    assert PILOT_PATH.exists(), "docs/implementer-merge-pilot.md missing"
    pilot = PILOT_PATH.read_text()
    assert "Expected" in pilot and "Actual" in pilot, "scenarios need expected/actual"
    assert "#16" in pilot, "must cross-reference the merger pilot"
    assert "#18" in pilot, "must cross-reference the deterministic TS gate"
    assert "ungated" in pilot.lower(), "must cover the unchanged ungated branch"


def test_untouched_invariants_still_present() -> None:
    """#27 constraints: branch namespace, author-trust gate, size-stop, never-push-main."""
    text = _skill_text()
    assert "claude/issue-<N>-<short-slug>" in text
    assert "## 1. Author-trust gate" in text
    assert "## 8. Size escalation" in text
    assert "Never push to `<base>`" in text
