"""Tests for gen_routines.py shim generation."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_shim_contains_implementer_skills(tmp_path: Path) -> None:
    """Every generated shim must reference the three implementer skill names."""
    import gen_routines

    gen_routines.main(shims_dir=tmp_path)

    shim_files = [f for f in tmp_path.glob("*.md") if "-merger" not in f.name]
    assert shim_files, "no implementer shim files generated"

    for shim_file in shim_files:
        content = shim_file.read_text()
        assert "routine-event-resolve" in content, f"{shim_file.name} missing routine-event-resolve"
        assert "routine-anti-noise" in content, f"{shim_file.name} missing routine-anti-noise"
        assert "implement-from-issue" in content, f"{shim_file.name} missing implement-from-issue"


def test_shim_contains_config_author_and_repo(tmp_path: Path) -> None:
    """Generated shim includes the author and repo slug from configs."""
    import configs
    import gen_routines

    gen_routines.main(shims_dir=tmp_path)
    all_configs = configs.load()

    for name, cfg in all_configs.items():
        shim_path = tmp_path / f"{name}.md"
        assert shim_path.exists(), f"shims/{name}.md not generated"
        content = shim_path.read_text()
        assert cfg["author"] in content, f"{name}.md missing author {cfg['author']!r}"
        assert cfg["repo_slug"] in content, f"{name}.md missing repo_slug {cfg['repo_slug']!r}"


def test_generation_is_idempotent(tmp_path: Path) -> None:
    """Running main() twice with the same configs produces byte-identical output."""
    import gen_routines

    out1 = tmp_path / "run1"
    out2 = tmp_path / "run2"

    gen_routines.main(shims_dir=out1)
    gen_routines.main(shims_dir=out2)

    files1 = sorted(out1.glob("*.md"), key=lambda f: f.name)
    files2 = sorted(out2.glob("*.md"), key=lambda f: f.name)
    assert [f.name for f in files1] == [f.name for f in files2], "file sets differ between runs"
    for f1, f2 in zip(files1, files2):
        assert f1.read_text() == f2.read_text(), f"idempotence check failed for {f1.name}"


def test_merger_shim_emitted_when_flag_set(tmp_path: Path) -> None:
    """When enable_merger='true', a merger shim is also written."""
    from string import Template

    import gen_routines

    cfg = {
        "repo_slug": "test-org/test-repo",
        "base": "main",
        "author": "test-author",
        "enable_merger": "true",
    }
    template_path = REPO_ROOT / "templates" / "shim.md.j2"
    template = Template(template_path.read_text())

    out_dir = tmp_path / "shims"
    out_dir.mkdir()

    shim = gen_routines.render_implementer(template, cfg)
    (out_dir / "test.md").write_text(shim)
    merger_shim = gen_routines.render_merger(cfg)
    (out_dir / "test-merger.md").write_text(merger_shim)

    assert (out_dir / "test.md").exists()
    assert (out_dir / "test-merger.md").exists()

    merger_content = (out_dir / "test-merger.md").read_text()
    assert "merge-pr-with-gate" in merger_content
    assert "routine-anti-noise" in merger_content
    assert cfg["author"] in merger_content
    assert cfg["repo_slug"] in merger_content
