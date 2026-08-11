import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


import pytest


@pytest.fixture(scope="session", autouse=True)
def _no_test_may_mutate_the_live_checkout_config():
    """Guard against recreating checkout-local setup configuration.

    Setup no longer writes config.json, but this session-scoped precaution
    keeps any future regression from mutating the live checkout through a
    `--dev` symlink. Tests invoking setup must stage their own source tree under
    tmp_path.
    """
    cfg = Path(__file__).resolve().parent.parent / "skills" / "multi-review" / "config.json"
    before = cfg.read_text() if cfg.exists() else None
    yield
    after = cfg.read_text() if cfg.exists() else None
    if after != before:
        if before is None:
            cfg.unlink(missing_ok=True)
        else:
            cfg.write_text(before)
        pytest.fail(
            f"a test mutated {cfg} (restored); stage a source copy under "
            f"tmp_path instead."
        )
