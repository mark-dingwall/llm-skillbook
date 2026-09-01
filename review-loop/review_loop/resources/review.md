# Review dispatch

request_id: {request_id}
role: {role}
charter_id: {charter_id}
target_seal: {target_seal}
round_input_seal: {round_input_seal}
scope_locator_ids: {scope_locator_ids}

## Subject

{subject}

Use local read-only inspection tools to examine the mounted subject when useful;
do not delegate the review judgment to another agent, subprocess, or tool.

## Report contract

Lead your review with a `## Summary` section. Include exactly one fenced
strict-JSON `review-record` code block containing `request_id`, `role`,
`charter_id`, `target_seal`, `round_input_seal`, `scope_locator_ids`, and
`source_findings`. It has no other fields. `source_findings` is an array; every
finding is exactly `{{ "id": STRING, "claim": STRING, "severity": SEVERITY,
"locator_ids": [STRING, ...] }}`, where `SEVERITY` is exactly `Minor`,
`Important`, or `Critical`; finding IDs are unique, IDs and claims are non-empty,
and locator IDs are non-empty. Put every finding mentioned in the summary in
this array; use an empty array only when the summary reports no findings. End
with exactly one terminal
line, and nothing after it: `REVIEW-STATUS: COMPLETE`, or
`REVIEW-STATUS: UNABLE` if you could not review the scope.
