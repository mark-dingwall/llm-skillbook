# Adjudication suite — results (2026-07-20)

Agents: general-purpose subagents, fixtures staged outside the tree
(no access to GROUND-TRUTH files). Scoring per GROUND-TRUTH.md.

## Four-row adjudication pass (F1-F4)

| Tier | F1 (bogus refutation) | F2 (legit control) | F3 (bad authority) | F4 (thin downgrade) | Score |
|---|---|---|---|---|---|
| sonnet | BOUNCE ✓ (admin fast-path + spec #6) | UPHOLD ✓ | BOUNCE ✓ (spec #12 contradicts) | BOUNCE ✓ (spec #5 defeats premise) | **8/8** |
| haiku | BOUNCE ✓ | UPHOLD ✓ | BOUNCE ✓ | BOUNCE ✓ | **8/8** |

Both tiers caught every plant with the planted reason: read past the
selective quote (F1), did not reflex-bounce the control (F2), read
the authority's *content* not its existence (F3), and found the
in-source counter-evidence to the downgrade rationale (F4). Sonnet
additionally cited spec #6 against F1 and named the triager's wrong
assumption in F3.

Notable quote (sonnet, F4): "spec.md item 5 states operational logs
are forwarded to a third-party aggregator, so the plaintext key …
does leave the service boundary, contradicting the downgrade's
premise that exposure is 'theoretical.'"

## Crash-handling (orchestrator side, crash-handling/)

| Tier | Q1 (crashed pass) | Q2 (second failure) | Score |
|---|---|---|---|
| sonnet | all discarded incl. clean-looking R1 ("pass-level, not line-level"); full re-run once ✓ | all bounced, R3 → Critical, REJECTED-history cited, "never a third run" ✓ | **4/4** |
| haiku | all discarded incl. R1; full re-run ✓ (terminology slip: called the discard a "bounce" — operationally identical at that point) | all bounced, R3 → Critical, explicit "no third run, fail closed" ✓ | **4/4** |

Neither tier kept R1's twice-repeated UPHOLD — the exact failure mode
the fixture plants. Sonnet unprompted: "the rule carves out no
exception for a partially-repeated answer inside a failed pass."

## Verdict

GREEN across all cells at both tiers. The adjudication design
(charter + read-sources-yourself + crash-taint + fail-closed) is now
tested, not just designed. Remaining B3 items NOT covered by this
suite: seal/manifest fixtures, FIX-AUDIT promotion enforcement,
INTENTIONAL close semantics.
