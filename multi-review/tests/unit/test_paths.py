# tests/unit/test_paths.py
from multi_review.core.paths import (
    generate_run_id,
    project_state_dir,
    run_dir,
    slugify,
)


def test_project_state_dir(tmp_path):
    assert project_state_dir(tmp_path) == tmp_path / ".multi-review"


def test_run_dir(tmp_path):
    rid = "run-20260515-1200-abcd"
    assert run_dir(tmp_path, rid) == tmp_path / ".multi-review" / "sessions" / rid


def test_generate_run_id_format():
    rid = generate_run_id()
    assert rid.startswith("run-")
    parts = rid.split("-")
    assert len(parts) == 4 and len(parts[3]) == 4


def test_slugify():
    assert slugify("Auth review v2!") == "auth-review-v2"
    assert slugify("  multiple   spaces  ") == "multiple-spaces"
