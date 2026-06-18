from __future__ import annotations
import argparse
import json
import shutil
import sys
from pathlib import Path
from multi_review.core.harvest import HARVEST_SCHEMA_VERSION, TELEMETRY_QUALITY

def _upgrade_row(row: dict) -> dict:
    if row.get("schema_version") == HARVEST_SCHEMA_VERSION:
        return row
    row["schema_version"] = HARVEST_SCHEMA_VERSION
    row.setdefault("pair_id", None)
    row.setdefault("prompt_file", None)
    row.setdefault("prompt_format_version", None)
    row.setdefault("drift_status", "not_applicable")
    row.setdefault("telemetry_notes", None)
    # v1 → v2 rename: top-level `usage` becomes canonical `usage_by_reviewer`;
    # `usage` is retained as deprecated alias (harvest.py module docstring).
    # Without this rename, v1 rows pass through with `usage` only and report.py
    # silently treats them as legacy (no telemetry → eligibility defaults bite).
    if "usage_by_reviewer" not in row and "usage" in row:
        row["usage_by_reviewer"] = row["usage"]
    for cli, ub in (row.get("usage_by_reviewer") or {}).items():
        ub.setdefault("telemetry_quality", TELEMETRY_QUALITY.get(cli, "degraded"))
        ub.setdefault("final_model", None)
        ub.setdefault("comparison_eligible", True)
    # Re-point the alias to the (now-backfilled) canonical dict so both keys
    # share the same data. Mirrors harvest.build_row line 131-133.
    if "usage_by_reviewer" in row:
        row["usage"] = row["usage_by_reviewer"]
    return row

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--log", type=Path, required=True)
    p.add_argument("--backup", type=Path, required=True)
    args = p.parse_args(argv)
    shutil.copy2(args.log, args.backup)
    lines = args.log.read_text().splitlines()
    upgraded = []
    for line in lines:
        if not line.strip():
            continue
        upgraded.append(json.dumps(_upgrade_row(json.loads(line))))
    args.log.write_text("\n".join(upgraded) + ("\n" if upgraded else ""))
    print(json.dumps({"ok": True, "rows": len(upgraded), "backup": str(args.backup)}))
    return 0

if __name__ == "__main__":
    sys.exit(main())
