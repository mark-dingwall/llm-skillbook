# Documentation guidance

## Authority

Use the record's status and role to determine authority, not its directory or
date. An approved current specification defines intended behavior; an active
plan defines work sequencing and review gates. Dated plans, evaluations,
transcripts, and other historical evidence may be retained, but must be
labelled non-authoritative from active entry points when they are superseded.
Component-owned designs and implementation details remain authoritative in
their owning component.

Plans describe intent and sequencing. They do not prove runtime behavior,
installation behavior, or test results. Confirm those claims against source,
manifests, and verification output.

## Maintaining records

Use clear specification and plan names, record a meaningful status, and keep
review gates explicit. Update active records when scope or decisions change;
preserve historical records when their dated content is evidence. Avoid
duplicating component inventories or implementation prose here.

Before publishing a local Markdown link or a placeholder for a forthcoming
record, resolve it from the document containing it. Verify that the target
exists, and run the focused documentation contract after changing entry
points. A placeholder must be unmistakably marked as such and must not be
presented as current authority.

The approved [documentation design](superpowers/specs/2026-08-18-repository-documentation-design.md)
and [implementation plan](superpowers/plans/2026-08-18-repository-documentation.md)
define the repository-wide documentation contract.
