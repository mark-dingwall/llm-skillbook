"""sidecar.py — row-grouper for legacy sidecar migration (spec §11.1).

Groups JSONL runs-log rows into candidate inline↔reference pairs.
Used by cli/migrate_sidecars.py.
"""
from __future__ import annotations
import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class CandidatePair:
    project: str
    rows: list[dict] = field(default_factory=list)  # exactly two when valid

    @property
    def synth_pair_id(self) -> str:
        h = hashlib.sha1("|".join(self.synth_run_id(r) for r in self.rows).encode()).hexdigest()[:8]
        date = self.rows[0]["started_at"][:10].replace("-", "")
        return f"pair-{date}-{h}"

    @staticmethod
    def synth_run_id(row: dict) -> str:
        seed = f"{row.get('started_at','')}|{row.get('cwd','')}"
        return f"run-{hashlib.sha1(seed.encode()).hexdigest()[:12]}"


def _read_rows(log_path: Path) -> list[dict]:
    if not log_path.exists():
        return []
    return [json.loads(l) for l in log_path.read_text().splitlines() if l.strip()]


def _ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def group_candidate_pairs(log_path: Path, *, default_delay_s: int) -> list[CandidatePair]:
    """Group JSONL rows into candidate inline↔reference pairs per spec §11.1.

    Window: max(60 min, default_delay_s + 10-min slack). Boundary cases surface
    to the user for confirmation rather than being silently dropped.
    """
    window_s = max(60 * 60, default_delay_s + 10 * 60)
    rows = _read_rows(log_path)
    candidates = [r for r in rows
                  if r.get("argv") and r.get("project")
                  and r.get("mode") in ("inline", "reference")]
    used: set[int] = set()
    pairs: list[CandidatePair] = []
    for i, a in enumerate(candidates):
        if i in used:
            continue
        for j in range(i + 1, len(candidates)):
            if j in used:
                continue
            b = candidates[j]
            if a["project"] != b["project"]:
                continue
            if {a["mode"], b["mode"]} != {"inline", "reference"}:
                continue
            if sorted(a["argv"]) != sorted(b["argv"]):
                continue
            dt = abs((_ts(a["started_at"]) - _ts(b["started_at"])).total_seconds())
            if dt > window_s:
                continue
            pairs.append(CandidatePair(project=a["project"], rows=[a, b]))
            used.update({i, j})
            break
    return pairs
