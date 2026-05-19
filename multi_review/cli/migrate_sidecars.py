"""migrate_sidecars.py — row-driven, interactive sidecar migration (spec §11.1).

Groups legacy JSONL rows into candidate pairs, then interactively assigns
sidecar .md files to those pairs. Emits paired reports for confirmed pairs
with full v1 telemetry, rewrites the runs log with synth pair_ids, and
moves sidecars to the legacy dir.

No --auto-apply per spec §11.1.
"""
from __future__ import annotations
import argparse
import json
import shutil
import sys
from pathlib import Path

from multi_review.core.sidecar import CandidatePair, group_candidate_pairs
from multi_review.core.report import build_paired_report


def _has_full_v1_telemetry(row: dict) -> bool:
    return all(row.get(k) is not None for k in ("prompt_bytes", "output_bytes", "usage"))


def _show_pairs(pairs: list[CandidatePair]) -> None:
    for i, p in enumerate(pairs, 1):
        modes = [r["mode"] for r in p.rows]
        ts = [r["started_at"] for r in p.rows]
        print(f"  [{i}] project={p.project} modes={modes} started_at={ts} synth_pair_id={p.synth_pair_id}")


def _ask(prompt: str) -> str:
    try:
        return input(prompt).strip()
    except EOFError:
        return ""


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--notes-dir", type=Path, required=True)
    p.add_argument("--log", type=Path, required=True)
    p.add_argument("--reports-dir", type=Path, required=True)
    p.add_argument("--legacy-dir", type=Path, required=True)
    p.add_argument("--default-delay", type=int, default=1800,
                   help="Window-sizing input for candidate pair detection.")
    args = p.parse_args(argv)

    args.reports_dir.mkdir(parents=True, exist_ok=True)
    args.legacy_dir.mkdir(parents=True, exist_ok=True)

    # 1. Row-group all rows into candidate pairs.
    pairs = group_candidate_pairs(args.log, default_delay_s=args.default_delay)
    print(f"Found {len(pairs)} candidate pair(s):")
    _show_pairs(pairs)
    confirmed: list[CandidatePair] = []
    for cp in pairs:
        ans = _ask(f"  Confirm pair {cp.synth_pair_id} ({cp.project})? [y]/n ") or "y"
        if ans.startswith("y"):
            confirmed.append(cp)

    # 2. Per-sidecar interactive assignment.
    # Sort descending so project-date named sidecars (e.g. paralife-2026-05-05.md)
    # appear before generic names (e.g. exploratory.md).
    assignments: dict[str, list[CandidatePair]] = {}
    for md in sorted(args.notes_dir.glob("*.md"), reverse=True):
        if md.parent == args.legacy_dir:
            continue
        print(f"\nSidecar: {md.name}")
        _show_pairs(confirmed)
        ans = _ask("  Assign to pair number(s) (comma-separated), 'legacy', or blank to skip: ")
        if ans == "legacy":
            assignments[str(md)] = []  # explicit legacy marker
        elif ans:
            try:
                idxs = [int(x) - 1 for x in ans.split(",")]
                assignments[str(md)] = [confirmed[i] for i in idxs if 0 <= i < len(confirmed)]
            except ValueError:
                print("  (unparseable; skipping)")

    # 3. Emit reports for pairs with full v1 telemetry; flag others.
    for cp in confirmed:
        if not all(_has_full_v1_telemetry(r) for r in cp.rows):
            print(f"  {cp.synth_pair_id}: incomplete v1 telemetry; legacy/incomplete-telemetry — skipping report.")
            continue
        prose = []
        for side_path, assigned_pairs in assignments.items():
            if cp in assigned_pairs:
                prose.append(Path(side_path).read_text())
        date = cp.rows[0]["started_at"][:10]
        out_path = args.reports_dir / f"{cp.project}-{date}-{cp.synth_pair_id}.md"
        build_paired_report(
            log_path=args.log, pair_id=None,
            out_path=out_path, headline=None, mode_divergence=None,
            per_reviewer_notes="\n\n---\n\n".join(prose) if prose else None,
            legacy_run_ids=[CandidatePair.synth_run_id(r) for r in cp.rows],
            project=cp.project, date=date, synth_pair_id=cp.synth_pair_id,
        )

    # 4. Row-rewrite: pair_id back onto matched legacy rows. .bak first.
    bak = args.log.with_suffix(args.log.suffix + ".bak")
    shutil.copy2(args.log, bak)
    rows = [json.loads(l) for l in args.log.read_text().splitlines() if l.strip()]
    lookup = {}
    for cp in confirmed:
        for r in cp.rows:
            lookup[(r.get("started_at"), r.get("cwd"))] = cp.synth_pair_id
    for r in rows:
        key = (r.get("started_at"), r.get("cwd"))
        if key in lookup and r.get("pair_id") is None:
            r["pair_id"] = lookup[key]
    args.log.write_text("\n".join(json.dumps(r) for r in rows) + "\n")

    # 5. Move sidecars: assigned → deleted (prose stitched into report); legacy/unassigned → legacy dir.
    for md in args.notes_dir.glob("*.md"):
        if md.parent == args.legacy_dir:
            continue
        if str(md) in assignments and assignments[str(md)]:
            md.unlink()
        else:
            shutil.move(str(md), str(args.legacy_dir / md.name))

    print(json.dumps({"ok": True, "pairs_confirmed": len(confirmed),
                      "backup": str(bak),
                      "reports_dir": str(args.reports_dir),
                      "legacy_dir": str(args.legacy_dir)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
