"""
Agent Skills shipped with BigTesty, the same files as the Claude Code plugin, copied by `bigtesty skills install`
into a project or the home directory.

Two homes: `.claude/skills` (Claude Code) and `.agents/skills` (the cross-agent convention). The copies are prefixed
`bigtesty-` so they never clash with other skills, and carry the BigTesty version so a later CLI can tell they are
stale.
"""

import re
import shutil
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from importlib import resources
from pathlib import Path

PREFIX = "bigtesty-"
MARKER = ".bigtesty-version"
_NAME_LINE = re.compile(r"^name:\s*\S+\s*$", re.MULTILINE)


class SkillTarget(StrEnum):
    CLAUDE = "claude"
    AGENTS = "agents"
    ALL = "all"


TARGET_DIRS = {
    SkillTarget.CLAUDE: Path(".claude") / "skills",
    SkillTarget.AGENTS: Path(".agents") / "skills",
}


@dataclass(frozen=True)
class FileWrite:
    path: Path
    text: str


def bundled_skills() -> dict[str, str]:
    """The SKILL.md of every skill shipped in the package, by skill name."""
    root = resources.files("bigtesty") / "plugin" / "skills"
    return {d.name: (d / "SKILL.md").read_text() for d in root.iterdir() if (d / "SKILL.md").is_file()}


def skill_dirs(target: SkillTarget, base: Path) -> tuple[Path, ...]:
    kinds = tuple(TARGET_DIRS) if target is SkillTarget.ALL else (target,)
    return tuple(base / TARGET_DIRS[kind] for kind in kinds)


def installed_name(skill: str) -> str:
    return f"{PREFIX}{skill}"


def renamed(skill_md: str, skill: str) -> str:
    """The standard wants `name` equal to the folder name: rewrites it for the prefixed folder."""
    return _NAME_LINE.sub(f"name: {installed_name(skill)}", skill_md, count=1)


def install_plan(skills: Mapping[str, str], dirs: tuple[Path, ...], version: str) -> tuple[FileWrite, ...]:
    """The files to write: the SKILL.md of each skill (renamed) and its version marker, in every directory."""
    return tuple(
        file_write
        for base in dirs
        for skill, text in sorted(skills.items())
        for file_write in (
            FileWrite(base / installed_name(skill) / "SKILL.md", renamed(text, skill)),
            FileWrite(base / installed_name(skill) / MARKER, f"{version}\n"),
        )
    )


def write(plan: tuple[FileWrite, ...]) -> None:
    """Replaces the BigTesty skill folders it writes to, dropping the files a newer version removed."""
    for folder in {file_write.path.parent for file_write in plan}:
        if folder.name.startswith(PREFIX) and folder.is_dir():
            shutil.rmtree(folder)

    for file_write in plan:
        file_write.path.parent.mkdir(parents=True, exist_ok=True)
        file_write.path.write_text(file_write.text)


def installed_markers(base: Path) -> dict[Path, str]:
    """The version markers of the BigTesty skills installed under `base` (a project or the home directory)."""
    return {
        marker.parent: marker.read_text()
        for skills_dir in TARGET_DIRS.values()
        for marker in (base / skills_dir).glob(f"{PREFIX}*/{MARKER}")
    }


def stale(markers: Mapping[Path, str], version: str) -> tuple[Path, ...]:
    """The installed skill folders whose marker is not this version."""
    return tuple(sorted(path for path, installed in markers.items() if installed.strip() != version))


def stale_skills_message(stale_dirs: tuple[Path, ...], version: str) -> str | None:
    if not stale_dirs:
        return None

    homes = sorted({str(d.parent) for d in stale_dirs})
    return (
        f"note: the BigTesty skills in {', '.join(homes)} are not from this version ({version}): "
        "refresh them with `bigtesty skills install` (--user for the home ones)"
    )
