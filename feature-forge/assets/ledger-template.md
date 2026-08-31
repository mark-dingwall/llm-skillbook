```json
{
  "schema": "feature-forge/ledger/v1",
  "run_id": "work-unit",
  "status": "active",
  "worktree": "/absolute/path/to/worktree",
  "branch": "feature/work-unit",
  "base_identity": "<git-object-id>",
  "stage": {"id": 1, "state": "active"},
  "next_action": "run preflight checks",
  "frozen": {"specification": null, "plan": null},
  "review": {
    "kind": null,
    "state": "not_started",
    "round": 0,
    "root_identity": null,
    "dispatch_id": null,
    "run_ref": null,
    "target_seal": null,
    "evidence_path": null,
    "reviewed_commit": null,
    "previous_open_finding_ids": [],
    "open_finding_ids": []
  }
}
```

## Intent and run evidence

| intent or preflight event | authority | evidence |
| --- | --- | --- |
|  |  |  |

## Current authority

| authority type | authority | rationale/affected requirements or scenarios | evidence |
| --- | --- | --- | --- |
| user approval |  |  |  |
| delegated authority | `user \| agent:<mode>` |  |  |

## Implementation progress

- Execution mode: `delegated | inline`

| plan task | status | commit | evidence |
| --- | --- | --- | --- |
|  |  |  |  |

## Verification and acceptance

| verification evidence | commands/results | identity/seal evidence |
| --- | --- | --- |
|  |  |  |

| requirement/scenario | acceptance method | acceptance state | authority | evidence | fallback |
| --- | --- | --- | --- | --- | --- |
|  | `automated \| UAT \| not_applicable` | `pending \| approved \| rejected \| infeasible \| waived` |  |  |  |

## Blockers and change requests

| type | description | authority/root cause | evidence | state |
| --- | --- | --- | --- | --- |
| blocker |  |  |  |  |
| change request |  |  |  |  |

- Blocker/change-request state: record in plain language whether the item
  remains open or has been resolved.

## Finish journal

The Finish operation journal lives inside this ledger; it is not a fifth
canonical artifact. It carries exactly these fields:

| field | value |
| --- | --- |
| `finish_id` |  |
| current phase | `ready \| claimed \| menu_pending \| choice_recorded \| executing \| terminal \| blocked` |
| prior phase (recorded only while `blocked`) |  |
| exact menu/presentation ID |  |
| selected choice | `local merge to confirmed base \| Push-and-PR \| Keep branch/worktree` |
| authority |  |
| confirmed base |  |
| base tip |  |
| feature tip |  |
| worktree |  |
| environment/reconciliation evidence |  |
| exact next side effect |  |
| completed side-effect receipts |  |
| durable receipts |  |

## Transition log

| event | parent event | UTC time | from | to | next action | session provenance | reason/authority | evidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
|  |  |  |  |  |  |  |  |  |

## Ledger copy-time checklist

These are ledger copy-time checks; they never duplicate requirement, task, or review prose.

- [ ] The JSON head validates before any workflow action.
- [ ] Human evidence remains in the tables; current checker state remains in the head.
- [ ] No requirement, task, or finding prose is copied into the JSON head.
- [ ] The ledger and final report receive no frozen blob identity.
