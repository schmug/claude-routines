"""Contract tests for the doc surfaces of gate-conditional landing (#28).

#27 rewrote implement-from-issue step 9 so the implementer lands its own PR
only through a mechanical required-checks gate (fail-closed runtime detection,
squash only) and stops at the open PR otherwise. These assert README.md,
SECURITY.md §5, and the generated implementer shim state that rule instead of
the retired unconditional "never merges" / "no auto-merge" invariant.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
README_PATH = REPO_ROOT / "README.md"
SECURITY_PATH = REPO_ROOT / "SECURITY.md"
SHIM_TEMPLATE_PATH = REPO_ROOT / "templates" / "shim.md.j2"

# Matches "never merges" including emphasis variants ("**never** merges").
NEVER_MERGES = re.compile(r"never\W{0,4}merges")

# Step 9's heading phrase; the shim line and README shim example mirror it.
LANDING_PHRASE = "land or stop by merge gate"


def test_readme_drops_unconditional_merge_claims() -> None:
    text = README_PATH.read_text()
    assert not NEVER_MERGES.search(text), "README still claims the implementer never merges"
    assert "no auto-merge" not in text, "README still claims no auto-merge (unhyphenated)"


def test_security_drops_unconditional_merge_claims() -> None:
    text = SECURITY_PATH.read_text()
    assert not NEVER_MERGES.search(text), "SECURITY.md still claims the implementer never merges"
    assert "no auto-merge" not in text, "SECURITY.md still claims no auto-merge (unhyphenated)"


def test_shim_template_drops_unconditional_merge_claims() -> None:
    text = SHIM_TEMPLATE_PATH.read_text()
    assert not NEVER_MERGES.search(text)
    assert "no auto-merge" not in text


def _security_section5() -> str:
    text = SECURITY_PATH.read_text()
    start = text.index("### 5.")
    end = text.index("### 6.", start)
    return text[start:end]


def test_security_section5_states_gate_conditional_rule() -> None:
    """§5 must state the real rule: gated → squash only; detection fails closed."""
    s5 = _security_section5()
    assert "required status check" in s5.lower(), "§5 must define the gate as required status checks"
    assert "fail closed" in s5.lower() or "fail-closed" in s5.lower()
    assert "UNKNOWN" in s5, "§5 must state UNKNOWN gate state is never a pass"
    assert "squash" in s5.lower(), "§5 must state the squash-only constraint"
    assert "ungated" in s5.lower(), "§5 must state the unchanged ungated branch"


def test_shim_template_mirrors_step9_landing() -> None:
    """The generated shim's implement-from-issue line mirrors step 9's heading."""
    assert LANDING_PHRASE in SHIM_TEMPLATE_PATH.read_text()


def test_readme_shim_example_matches_template_landing() -> None:
    """The manual-operator shim example in README stays in sync with the template."""
    assert LANDING_PHRASE in README_PATH.read_text()
