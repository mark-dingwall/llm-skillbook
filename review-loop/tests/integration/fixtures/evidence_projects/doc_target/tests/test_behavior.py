"""Behavioral fixture for guide.md, explicitly selected (not invented) because
this document's fenced example directly controls what a reader/agent does
with it (design: "RED/GREEN pressure scenarios are required when developing
review-loop's own skill or role prompts, where the document directly
controls agent behavior").
"""
from pathlib import Path

GUIDE = Path(__file__).resolve().parent.parent / "guide.md"


def _fenced_python_block(text: str) -> str:
    start = text.index("```python\n") + len("```python\n")
    end = text.index("```", start)
    return text[start:end]


def test_guide_usage_example_matches_its_documented_claim():
    text = GUIDE.read_text()
    namespace: dict[str, object] = {}
    exec(_fenced_python_block(text), namespace)
    assert namespace["result"] == 4
    assert "`result` is `4`." in text
