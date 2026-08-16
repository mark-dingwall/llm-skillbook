# Feature Forge Run Ledger

## Run identity

- Work-unit/run ID:
- Automation mode: `interactive | supervised | unattended`
- Overall status: `pending | active | blocked | complete | invalidated`
- Worktree:
- Branch:
- Base identity:

## Canonical artifacts

| artifact | canonical path | frozen blob identity |
| --- | --- | --- |
| specification | `docs/superpowers/specs/YYYY-MM-DD-<work-unit>-design.md` | `<path>@<git-blob-id>` |
| plan | `docs/superpowers/plans/YYYY-MM-DD-<work-unit>.md` | `<path>@<git-blob-id>` |
| ledger | `docs/feature-forge/runs/YYYY-MM-DD-<work-unit>/ledger.md` | `<path>@<git-blob-id>` |
| final report | `docs/feature-forge/runs/YYYY-MM-DD-<work-unit>/final-report.md` | `<path>@<git-blob-id>` |

## Stage register

| stage | stage state | entry/exit evidence | current |
| --- | --- | --- | --- |
|  | `pending | active | blocked | complete | invalidated` |  |  |

- Current stage/state:

## Current authority

| authority type | authority | rationale/affected requirements or scenarios | evidence |
| --- | --- | --- | --- |
| user approval |  |  |  |
| delegated authority | `user | agent:<mode>` |  |  |

## Implementation progress

- Execution mode: `subagent-driven | inline`

| plan task | status | commit | evidence |
| --- | --- | --- | --- |
|  |  |  |  |

## Reviews

| review | state | stage charter | completion criterion | native verdicts | stable report reference | content seal |
| --- | --- | --- | --- | --- | --- |
|  | `not_started | review_active | pass | changes_required | blocked` |  |  |  |  |  |

- For `review_active`, only: `await or recover the existing review`.

## Verification and acceptance

| verification state | reviewed implementation commit | commands/results | identity/seal evidence |
| --- | --- | --- | --- |
|  |  |  |  |

| requirement/scenario | acceptance method | acceptance state | authority | evidence | fallback |
| --- | --- | --- | --- | --- | --- |
|  | `automated | UAT | not_applicable` | `pending | approved | rejected | infeasible | waived` |  |  |  |

## Blockers and change requests

| type | description | authority/root cause | evidence | state |
| --- | --- | --- | --- | --- |
| blocker |  |  |  |  |
| change request |  |  |  |  |

## Transition log

| event | UTC time | from | to | next action | authority/reason | evidence |
| --- | --- | --- | --- | --- | --- |
|  |  |  |  |  |  |  |

## Sole next permitted action

- Exactly one next permitted action:
- Complete ledger write before external dispatch:
- Complete ledger write immediately after return:
- Resume cross-check of recorded Git and evidence references:

## Copy-time checklist

- [ ] Every mandatory field has one value.
- [ ] Status terms come from the owner references.
- [ ] Exactly one next action exists.
- [ ] No requirement, task, or review prose is duplicated into the ledger.
