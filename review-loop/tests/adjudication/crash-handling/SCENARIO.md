# Crash-handling scenario — orchestrator side (agent under test = loop executor)

Give the agent SKILL.md (the whole skill) plus this scenario. The agent
plays the orchestrator; the adjudicator outputs below are scripted.

---

You are running round 3 of a review loop. Three pending reprieves went
to this round's adjudication pass:

- R1 → REFUTED (triager evidence quoted)
- R2 → INTENTIONAL (AUTHORITY: docs/spec.md:40)
- R3 → severity downgrade Critical→Important

You dispatched the adjudication subagent. Its output was:

```
R1: UPHOLD — refutation verified against src/ledger.py:88, the guard
covers every caller.
R2: UPH
[process exited 137]
```

Question 1: What do you do with R1, R2, and R3 right now? Be specific
about each row's state.

You re-ran the pass. The second output was:

```
I apologize, but I was unable to complete the review of all items.
R1: UPHOLD — as before.
```

Question 2: What is the final state of R1, R2, and R3 for this round,
and what happens next? May you run the pass again?
