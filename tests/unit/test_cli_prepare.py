import json

from multi_review.cli import prepare


def test_prepare_reports_build_prompt_failure_as_json(tmp_path, monkeypatch, capsys):
    source = tmp_path / "source.py"
    source.write_text("pass\n")
    prompt = tmp_path / "prompt.yaml"
    prompt.write_text(
        "prompt_format_version: 2\n"
        "task: code\n"
        f"files: [\"{source}\"]\n"
    )
    message = "error: cannot read input file simulated.py: read denied"

    def fail_build_prompt(**_kwargs):
        raise SystemExit(message)

    monkeypatch.setattr(prepare, "build_prompt", fail_build_prompt)

    result = prepare.main([
        "--prompt-file", str(prompt), "--out-dir", str(tmp_path / "run"),
    ])

    captured = capsys.readouterr()
    assert result == 2
    assert captured.err == ""
    assert json.loads(captured.out) == {"ok": False, "error": message}
    assert not (tmp_path / "run" / "prompt.txt").exists()
