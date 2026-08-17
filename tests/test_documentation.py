"""Repository documentation entry-point contract."""

import os
import re
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]


def tracked_top_level_directories() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=REPO,
        check=True,
        capture_output=True,
    )
    names = {
        raw.decode().split("/", 1)[0]
        for raw in result.stdout.split(b"\0")
        if raw and b"/" in raw
    }
    return [Path(name) for name in sorted(names)]


SCOPES = [Path("."), *tracked_top_level_directories()]
LOCAL_LINK = re.compile(
    r"\[[^]]+\]\((?!https?://|mailto:|#)([^)#\s]+)(?:#[^)]*)?\)"
)


@pytest.mark.parametrize(
    "scope",
    SCOPES,
    ids=lambda scope: "root" if scope == Path(".") else str(scope),
)
def test_documentation_entrypoints(scope: Path) -> None:
    directory = REPO / scope
    assert (directory / "README.md").is_file()
    assert (directory / "CLAUDE.md").is_file()

    agents = directory / "AGENTS.md"
    assert agents.is_symlink()
    assert os.readlink(agents) == "CLAUDE.md"
    assert agents.resolve(strict=True) == (directory / "CLAUDE.md").resolve()


@pytest.mark.parametrize(
    "scope",
    SCOPES,
    ids=lambda scope: "root" if scope == Path(".") else str(scope),
)
def test_entrypoint_local_markdown_links_resolve(scope: Path) -> None:
    directory = REPO / scope
    for name in ("README.md", "CLAUDE.md"):
        document = directory / name
        if not document.exists():
            continue
        for relative in LOCAL_LINK.findall(document.read_text()):
            target = (document.parent / relative).resolve()
            assert target.exists(), f"broken link in {document}: {relative}"
