import json
import tomllib
from pathlib import Path

import pytest
from typer.testing import CliRunner

from bigtesty import __version__
from bigtesty.cli.main import app
from bigtesty.skills import (
    MARKER,
    SkillTarget,
    bundled_skills,
    install_plan,
    installed_markers,
    renamed,
    skill_dirs,
    stale,
    stale_skills_message,
    write,
)

REPO_ROOT = Path(__file__).parent.parent
SKILL = "---\nname: setup\ndescription: Set it up.\n---\n\n# Setup\n\nname: not frontmatter\n"


@pytest.mark.parametrize(
    ("target", "expected"),
    [
        # --- Case 1: Claude Code only ---
        (SkillTarget.CLAUDE, ("p/.claude/skills",)),
        # --- Case 2: the other agents only ---
        (SkillTarget.AGENTS, ("p/.agents/skills",)),
        # --- Case 3: both ---
        (SkillTarget.ALL, ("p/.claude/skills", "p/.agents/skills")),
    ],
)
def test_given_target_when_skill_dirs_then_its_skill_homes(target, expected):
    # WHEN / THEN
    assert skill_dirs(target, Path("p")) == tuple(Path(e) for e in expected)


def test_given_skill_when_renamed_then_only_the_frontmatter_name_is_prefixed():
    # WHEN
    text = renamed(SKILL, "setup")

    # THEN
    assert text.startswith("---\nname: bigtesty-setup\n") and "name: not frontmatter" in text


def test_given_skill_and_two_homes_when_install_plan_then_skill_and_marker_in_each():
    # WHEN
    plan = install_plan({"setup": SKILL}, (Path("a"), Path("b")), "1.2.0")

    # THEN
    assert [(str(w.path), w.text) for w in plan if w.path.name == MARKER] == [
        (f"a/bigtesty-setup/{MARKER}", "1.2.0\n"),
        (f"b/bigtesty-setup/{MARKER}", "1.2.0\n"),
    ]


def test_given_markers_of_two_versions_when_stale_then_only_the_other_version():
    # WHEN / THEN
    assert stale({Path("x/bigtesty-a"): "1.1.0\n", Path("x/bigtesty-b"): "1.2.0\n"}, "1.2.0") == (Path("x/bigtesty-a"),)


def test_given_stale_dirs_when_stale_skills_message_then_names_their_homes():
    # WHEN
    message = stale_skills_message((Path("p/.claude/skills/bigtesty-a"), Path("p/.claude/skills/bigtesty-b")), "1.2.0")

    # THEN
    assert message is not None and "p/.claude/skills " in message and "bigtesty skills install" in message
    assert stale_skills_message((), "1.2.0") is None


def test_given_own_skill_and_leftover_when_install_twice_then_replaced_and_own_skill_untouched(tmp_path):
    # GIVEN
    skills = bundled_skills()
    dirs = skill_dirs(SkillTarget.ALL, tmp_path)
    own = tmp_path / ".claude/skills/my-skill/SKILL.md"
    own.parent.mkdir(parents=True)
    own.write_text("mine")
    leftover = tmp_path / ".claude/skills/bigtesty-setup/old.md"
    leftover.parent.mkdir(parents=True)
    leftover.write_text("old")

    # WHEN
    write(install_plan(skills, dirs, "1.1.0"))
    write(install_plan(skills, dirs, "1.2.0"))

    # THEN
    assert own.read_text() == "mine" and not leftover.exists()
    assert set(installed_markers(tmp_path).values()) == {"1.2.0\n"}
    assert len(installed_markers(tmp_path)) == 2 * len(skills)


def test_given_package_when_bundled_skills_then_the_four_skills_with_their_folder_name():
    # WHEN
    skills = bundled_skills()

    # THEN
    assert set(skills) == {"setup", "writing-tests", "python-tests", "troubleshooting"}
    assert all(text.startswith(f"---\nname: {name}\ndescription: ") for name, text in skills.items())


def test_given_plugin_manifest_when_read_then_same_version_as_the_package():
    # GIVEN
    plugin = json.loads((REPO_ROOT / "src/bigtesty/plugin/.claude-plugin/plugin.json").read_text())
    project = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text())["project"]

    # THEN
    assert plugin["version"] == project["version"]


def test_given_project_when_skills_install_then_copies_in_both_homes(tmp_path, monkeypatch):
    # GIVEN
    monkeypatch.chdir(tmp_path)

    # WHEN
    result = CliRunner().invoke(app, ["skills", "install"])

    # THEN
    assert result.exit_code == 0
    assert (tmp_path / ".claude/skills/bigtesty-setup/SKILL.md").read_text().startswith("---\nname: bigtesty-setup\n")
    assert (tmp_path / f".agents/skills/bigtesty-troubleshooting/{MARKER}").read_text() == f"{__version__}\n"


def test_given_stale_skills_in_project_when_run_cli_then_warns(tmp_path, monkeypatch):
    # GIVEN
    marker = tmp_path / ".claude/skills/bigtesty-setup" / MARKER
    marker.parent.mkdir(parents=True)
    marker.write_text("0.9.0\n")
    monkeypatch.chdir(tmp_path)

    # WHEN
    result = CliRunner().invoke(app, ["version"])

    # THEN
    assert "bigtesty skills install" in result.output
