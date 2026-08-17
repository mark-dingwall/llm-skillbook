import json
import sys

from .artifacts import ArtifactRef, ProjectionAuthority, TransitionEnvelope
from .state import apply


def main() -> int:
    # This JSON adapter is test-only. Production uses CanonicalStore directly.
    if sys.argv[1:] != ["--test-fixture"]:
        response = {"schema_version": 1, "ok": False, "errors": [{"path":"$","code":"test_fixture","message":"test fixture flag is required"}]}
        json.dump(response, sys.stdout, separators=(",", ":"))
        sys.stdout.write("\n")
        return 2
    try:
        request = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        response = {"schema_version": 1, "ok": False, "errors": [{"path":"$","code":"invalid_json","message":str(exc)}]}
    else:
        try:
            snapshot = request["snapshot"]
            raw = request["envelope"]
            envelope = TransitionEnvelope(
                raw["operation"],
                tuple(ArtifactRef(**ref) for ref in raw["artifact_refs"]),
                raw["projection"], raw["expected_governing_seal"],
            )
            response = {"schema_version": 1, "ok": True, "result": apply(envelope, snapshot, ProjectionAuthority.from_snapshot(snapshot))}
        except (KeyError, TypeError, ValueError) as exc:
            response = {"schema_version": 1, "ok": False, "errors": [{"path":"$","code":"invalid_fixture","message":str(exc)}]}
        except Exception as exc:
            response = {"schema_version": 1, "ok": False, "errors": [{"path":"$","code":"rejected","message":str(exc)}]}
    json.dump(response, sys.stdout, separators=(",", ":"))
    sys.stdout.write("\n")
    return 0 if response["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
