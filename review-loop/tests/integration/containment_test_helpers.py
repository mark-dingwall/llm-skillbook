"""Shared test-only prerequisites for real Bubblewrap containment tests."""
from __future__ import annotations

import sys
import unittest
from collections.abc import Callable
from pathlib import Path


def resolve_bwrap_visible_python(
    executable: str | Path | None = None,
    *,
    is_visible: Callable[[Path], bool] = Path.is_file,
) -> Path:
    """Return a Python executable available in mappings that bind ``/usr``."""
    resolved = Path(sys.executable if executable is None else executable).resolve()
    if resolved.is_relative_to("/usr") and is_visible(resolved):
        return resolved

    for candidate in (Path("/usr/bin/python3"), Path("/usr/local/bin/python3")):
        if is_visible(candidate):
            return candidate

    raise unittest.SkipTest("Bubblewrap-visible Python is unavailable")
