import json
import sys

from .state import invalid_json_response, process


def main() -> int:
    try:
        request = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        response = invalid_json_response(str(exc))
    else:
        response = process(request)
    json.dump(response, sys.stdout, separators=(",", ":"))
    sys.stdout.write("\n")
    return 0 if response["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
