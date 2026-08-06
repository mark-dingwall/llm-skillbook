import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
HARNESS = REPO_ROOT / "tests" / "manual" / "headless-driver-smoke.sh"


def test_headless_driver_smoke_harness_has_valid_bash_syntax():
    result = subprocess.run(
        ["bash", "-n", str(HARNESS)],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0, result.stderr


def test_headless_driver_smoke_harness_self_check_validates_fixtures():
    result = subprocess.run(
        ["bash", str(HARNESS), "--check"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip().endswith("headless_driver_smoke_check=PASS")
