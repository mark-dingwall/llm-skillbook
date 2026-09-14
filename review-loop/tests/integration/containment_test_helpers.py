"""Shared test-only prerequisites for real Bubblewrap containment tests."""
from __future__ import annotations

import os
import sys
import unittest
from collections.abc import Callable
from pathlib import Path


def is_bwrap_visible_executable(path: Path) -> bool:
    """Whether ``path`` is a regular file the test process can execute."""
    return path.is_file() and os.access(path, os.X_OK)


def resolve_bwrap_visible_python(
    executable: str | Path | None = None,
    *,
    is_usable: Callable[[Path], bool] = is_bwrap_visible_executable,
) -> Path:
    """Return a usable Python executable in mappings that bind ``/usr``."""
    resolved = Path(sys.executable if executable is None else executable).resolve()
    if resolved.is_relative_to("/usr") and is_usable(resolved):
        return resolved

    for candidate in (Path("/usr/bin/python3"), Path("/usr/local/bin/python3")):
        if is_usable(candidate):
            return candidate

    raise unittest.SkipTest("Bubblewrap-visible Python executable is unavailable")
