"""Mechanical link check: every relative Markdown link must resolve on disk.

Repository-provided document gate (design: "For technical documents, use
existing mechanical checks such as link ... validation"). No third-party
dependency -- a plain regex over ``](...)`` targets is enough for this
fixture's bounded RED/GREEN proof.
"""
import re
import sys
from pathlib import Path

LINK_RE = re.compile(r"\]\(([^)]+)\)")


def main(doc_path: str) -> int:
    doc = Path(doc_path)
    ok = True
    for target in LINK_RE.findall(doc.read_text()):
        if target.startswith(("http://", "https://")):
            continue
        if not (doc.parent / target).exists():
            print(f"broken link: {target}", file=sys.stderr)
            ok = False
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
