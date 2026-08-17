# Feature Forge Final Report

## Outcome

- Work-unit/run ID:
- Overall status: `active | blocked | complete`
- Outcome/date:
- Sole next permitted action or terminal outcome:

## Frozen authorities and reviewed snapshot

| authority | authority record/evidence | frozen artifact | `<path>@<git-blob-id>` | reviewed implementation commit | content seal |
| --- | --- | --- | --- | --- | --- |
|  |  |  |  |  |  |

## Requirement traceability

| requirement/scenario | plan task | test/evidence | outcome/date | UAT result |
| --- | --- | --- | --- | --- |
|  |  |  |  |  |

## Final verification

| verification state | commands/results | reviewed implementation commit | identity/seal evidence |
| --- | --- | --- | --- |
|  |  |  |  |

## Acceptance

### Automated acceptance

| requirement/scenario | method | state | authority | evidence | fallback |
| --- | --- | --- | --- | --- | --- |
|  | `automated \| UAT \| not_applicable` | `pending \| approved \| rejected \| infeasible \| waived` |  |  |  |

### Human UAT/sign-off

Fill in exactly one of the two mutually exclusive branches below for each
UAT-classified requirement, per its declared participant, exercise, substitute,
and evidence criterion. Never assert both, and never assert either
unconditionally when the evidence for it was not actually produced in this run.

**Human UAT branch** (authority `user`; use only when a named participant
actually performed the exercise in this run):

```text
Human UAT: [participant] performed [observable exercise]; [approved/rejected];
evidence met [criterion].
```

- Participant:
- Observable exercise performed:
- Result: `approved | rejected`
- Evidence criterion met:

**Automated-substitute branch** (authority `agent:unattended`; use only when
the declared unattended automated substitute actually ran and produced
evidence in this run):

```text
Automated substitute: [substitute] evaluated [criterion]; [pass/fail].
Automated acceptance evidence completed; human UAT/sign-off was waived.
```

- Substitute:
- Evidence criterion evaluated:
- Result: `pass | fail`
- Waiver authority/rationale: `agent:unattended`

## Open defects and authorized exceptions

| type | description | authority | evidence | disposition |
| --- | --- | --- | --- | --- |
| open defect |  |  |  |  |
| authorized exception |  |  |  |  |

## Commit checkpoints

| checkpoint | commit | evidence |
| --- | --- | --- |
|  |  |  |

## Branch-finishing readiness

Stage 13 (Report) is **active** while this report and the ledger are being
written: `finish_id` is allocated once, Finish phase is `ready`, report
outcome is `pending`, and the ledger's sole next permitted action is
`claim <finish_id>`. Only Stage 14 (Finish) replaces that `pending`/`ready`
state — with either a terminal durable receipt (Option 1 base-checkout receipt
or Option 2/3 preserved-feature-branch/worktree receipt, per the ledger Finish
journal and `workflow.md`) or a `blocked` receipt recording the prior phase and
a resolution-only next action. This report does not define a second Finish
state machine; it only reports the one the ledger's Finish journal owns.

- Worktree:
- Branch:
- Clean-tree evidence:
- Finish-authority outcome/evidence:
- Stage 13 status: `active`; Finish phase: `ready`; report outcome: `pending`; next action: `claim <finish_id>`
- Stage 14 outcome (fill in only once Finish has run): `terminal` outcome/receipt, or `blocked` receipt with prior phase and resolution-only next action

## Final-report copy-time checklist

These are final-report copy-time checks; they never duplicate requirement,
task, or review prose.

- [ ] Every mandatory field has one value.
- [ ] Status terms come from the owner references.
- [ ] Exactly one next action exists, or the terminal outcome is recorded with no next action.
- [ ] No requirement, task, or review prose is duplicated into the final report.
- [ ] Exactly one of the Human UAT or Automated-substitute branches is filled in per UAT-classified requirement, and neither is asserted unconditionally or without evidence actually produced in this run.
