"""Contract tests for cc-routine's skill names (#34).

The shipofclaudius plugin ships skills named `merge-pr-with-gate` and
`routine-anti-noise`. Those are Workflow-tool wrappers around a different,
narrower gate; cc-routine's procedures are prose for tool-restricted routine
sessions. Sharing a bare name listed both twice in every session with both
plugins enabled. cc-routine's copies keep their text and take routine-specific
names; nothing here depends on shipofclaudius.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / "plugins" / "cc-routine" / "skills"
SHIM_TEMPLATE_PATH = REPO_ROOT / "templates" / "shim.md.j2"
README_PATH = REPO_ROOT / "README.md"

# Names owned by shipofclaudius; cc-routine must not ship a skill under either.
SHIPOFCLAUDIUS_NAMES = {"merge-pr-with-gate", "routine-anti-noise"}

EXPECTED_SKILLS = {
    "implement-from-issue",
    "routine-event-resolve",
    "routine-noise-gate",
    "routine-merge-gate",
}


def _skill_dirs() -> set[str]:
    return {p.name for p in SKILLS_DIR.iterdir() if p.is_dir()}


def _frontmatter_name(skill_dir: str) -> str:
    text = (SKILLS_DIR / skill_dir / "SKILL.md").read_text()
    frontmatter = text.split("---")[1]
    match = re.search(r"^name:\s*(\S+)\s*$", frontmatter, re.MULTILINE)
    assert match, f"{skill_dir}/SKILL.md has no frontmatter name"
    return match.group(1)


def test_plugin_ships_exactly_the_expected_skills() -> None:
    assert _skill_dirs() == EXPECTED_SKILLS


def test_plugin_does_not_ship_shipofclaudius_names() -> None:
    """Exactly one plugin ships each name: shipofclaudius, not cc-routine."""
    assert not (_skill_dirs() & SHIPOFCLAUDIUS_NAMES)


def test_frontmatter_name_matches_directory() -> None:
    """The skill list shows the frontmatter name; it must match the directory."""
    for skill_dir in _skill_dirs():
        assert _frontmatter_name(skill_dir) == skill_dir


def test_skills_cross_reference_by_new_names() -> None:
    """Skill bodies never point a routine at a shipofclaudius-owned name."""
    for skill_dir in _skill_dirs():
        text = (SKILLS_DIR / skill_dir / "SKILL.md").read_text()
        for old in SHIPOFCLAUDIUS_NAMES:
            assert old not in text, f"{skill_dir}/SKILL.md still references {old}"


def test_generated_shims_use_new_names(tmp_path: Path) -> None:
    """Deployed shim text asks for the renamed skills, never the old bare names."""
    from string import Template

    import gen_routines

    cfg = {
        "repo_slug": "test-org/test-repo",
        "base": "main",
        "author": "test-author",
        "enable_merger": "true",
    }
    template = Template(SHIM_TEMPLATE_PATH.read_text())
    implementer = gen_routines.render_implementer(template, cfg)
    merger = gen_routines.render_merger(cfg)

    assert "routine-noise-gate" in implementer
    assert "routine-noise-gate" in merger
    assert "routine-merge-gate" in merger
    for old in SHIPOFCLAUDIUS_NAMES:
        assert old not in implementer, f"implementer shim still names {old}"
        assert old not in merger, f"merger shim still names {old}"


def test_readme_names_the_renamed_skills() -> None:
    """README Install + shim examples stay in sync with the plugin's skill names."""
    text = README_PATH.read_text()
    for name in EXPECTED_SKILLS:
        assert f"`{name}`" in text, f"README never names {name}"


def _readme_text_blocks() -> list[str]:
    """The fenced ```text blocks in README: the manual-operator shim examples."""
    return re.findall(r"```text\n(.*?)```", README_PATH.read_text(), re.DOTALL)


def test_readme_shim_examples_use_new_names() -> None:
    """The README naming note may cite shipofclaudius's names; shim examples may not."""
    blocks = _readme_text_blocks()
    assert len(blocks) >= 2, "README should carry the implementer and merger shim examples"
    for block in blocks:
        for old in SHIPOFCLAUDIUS_NAMES:
            assert old not in block, f"README shim example still names {old}"
