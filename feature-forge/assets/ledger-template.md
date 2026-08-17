# Feature Forge Run Ledger

## Run identity

- Work-unit/run ID:
- Automation mode: `interactive | supervised | unattended`
- Overall status: `pending | active | blocked | complete | invalidated`
- Worktree:
- Branch:
- Base identity:

## Canonical artifacts

Frozen blob identity applies only to the independently reviewed specification
and plan. The ledger and final report are deliberately mutable run records and
never receive their own frozen blob identity.

| artifact | canonical path | frozen identity |
| --- | --- | --- |
| specification | `docs/superpowers/specs/YYYY-MM-DD-<work-unit>-design.md` | `<path>@<git-blob-id>` |
| plan | `docs/superpowers/plans/YYYY-MM-DD-<work-unit>.md` | `<path>@<git-blob-id>` |
| ledger | `docs/feature-forge/runs/YYYY-MM-DD-<work-unit>/ledger.md` | mutable — no frozen identity |
| final report | `docs/feature-forge/runs/YYYY-MM-DD-<work-unit>/final-report.md` | mutable — no frozen identity |

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
| --- | --- | --- | --- | --- | --- | --- |
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

## Finish journal

The Finish operation journal lives inside this ledger; it is not a fifth
canonical artifact. It carries exactly these fields:

| field | value |
| --- | --- |
| `finish_id` |  |
| current phase | `ready | claimed | menu_pending | choice_recorded | executing | terminal | blocked` |
| prior phase (recorded only while `blocked`) |  |
| exact menu/presentation ID |  |
| selected choice | `local merge to confirmed base | Push-and-PR | Keep branch/worktree` |
| authority |  |
| confirmed base |  |
| base tip |  |
| feature tip |  |
| worktree |  |
| environment/reconciliation evidence |  |
| exact next side effect |  |
| durable receipts |  |

## Transition log

| event | UTC time | from | to | next action | reason/authority | evidence |
| --- | --- | --- | --- | --- | --- | --- |
|  |  |  |  |  |  |  |

## Sole next permitted action

- Every nonterminal state names exactly one next permitted action.
- Terminal overall status `complete` (Finish phase `terminal`): records the terminal outcome and no next action.
- `review_active` permits only: `await or recover the existing review`.
- Exactly one next permitted action:
- Complete ledger write before external dispatch:
- Complete ledger write immediately after return:
- Resume cross-check of recorded Git and evidence references:

## Ledger copy-time checklist

These are ledger copy-time checks; they never duplicate requirement, task, or review prose.

- [ ] Every mandatory field has one value.
- [ ] Status terms come from the owner references.
- [ ] Exactly one next action exists for every nonterminal state; the terminal state has the terminal outcome and no next action.
- [ ] No requirement, task, or review prose is duplicated into the ledger.
- [ ] No blob identity is recorded for the ledger or the final report — only for the frozen specification and plan.
