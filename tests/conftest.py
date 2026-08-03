import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


import pytest


@pytest.fixture(scope="session", autouse=True)
def _no_test_may_mutate_the_live_checkout_config():
    """Fail the run if any test writes into <repo>/skills/multi-review/config.json.

    Regression guard, 2026-08-03 (found during the grok manual smoke). `setup
    --dev` symlinks $HOME/.claude/skills/multi-review at whatever --source-repo
    names, so its config.json write follows the symlink into the *real* tree —
    monkeypatching HOME does not redirect it. test_setup_dev_mode_symlinks
    pointed --source-repo at the live checkout and left a pytest tmpdir in that
    file. central_runs_dir() reads it before any other resolution step, so
    every later real run harvested into a since-deleted /tmp/pytest-of-*/ path
    while the suite stayed green.

    Session-scoped and autouse so it catches the leak regardless of which test
    causes it or what order tests run in — a per-test assertion in the offending
    module would only cover the one path we already know about. Tests needing
    setup must stage their own source tree under tmp_path.
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
            f"a test mutated {cfg} (restored). setup --dev writes through its "
            f"symlink into --source-repo; stage a copy under tmp_path instead."
        )
