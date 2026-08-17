import json
import sys

from .state import invalid_json_response, process_test_fixture


def main() -> int:
    # The state processor is not an operator-facing free-form authority.  This
    # adapter exists only for the unit fixtures that characterize its pure
    # deterministic kernels; production calls state.apply from the controller.
    if sys.argv[1:] != ["--test-fixture"]:
        response = invalid_json_response("the state CLI is available only to test fixtures")
        json.dump(response, sys.stdout, separators=(",", ":"))
        sys.stdout.write("\n")
        return 2
    try:
        request = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        response = invalid_json_response(str(exc))
    else:
        response = process_test_fixture(request)
    json.dump(response, sys.stdout, separators=(",", ":"))
    sys.stdout.write("\n")
    return 0 if response["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
