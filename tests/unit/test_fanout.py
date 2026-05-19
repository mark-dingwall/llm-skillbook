"""tests/unit/test_fanout.py — unit tests for core/fanout.py"""
import asyncio
import pytest
from multi_review.core.fanout import (
    resolve_chain, ReviewerResult, ReviewerState,
)
from multi_review.core.reviewers import CLI_SPEC


def test_resolve_chain_explicit_pin_no_fallback():
    chain = resolve_chain("gemini", explicit_model="gemini-3.1-pro",
                          fallback_disabled=False, override_chain=None)
    assert chain == ["gemini-3.1-pro"]


def test_resolve_chain_default_walks_spec_chain():
    chain = resolve_chain("gemini", explicit_model=None,
                          fallback_disabled=False, override_chain=None)
    assert chain[0] == CLI_SPEC["gemini"]["fallback_chain"][0] or chain[0] is None


def test_resolve_chain_no_fallback_flag():
    chain = resolve_chain("gemini", explicit_model=None,
                          fallback_disabled=True, override_chain=None)
    assert len(chain) == 1


def test_resolve_chain_override_chain_used():
    chain = resolve_chain("gemini", explicit_model=None,
                          fallback_disabled=False, override_chain=["a", "b"])
    assert chain == ["a", "b"]
