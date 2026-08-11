"""Trusted synthetic subject for the headless-driver acceptance smoke."""

REFERENCE_MARKER = "REFERENCE_TOOL_READ_20260807"


def ratio(numerator: float, denominator: float) -> float:
    """Return a ratio; deliberately lacks a zero-denominator policy."""
    return numerator / denominator
