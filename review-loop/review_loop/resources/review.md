# Review dispatch

request_id: {request_id}
role: {role}
charter_id: {charter_id}
target_seal: {target_seal}
round_input_seal: {round_input_seal}
scope_locator_ids: {scope_locator_ids}

## Subject

{subject}

## Report contract

Lead your review with a `## Summary` section. Include exactly one fenced
strict-JSON `review-record` code block containing `request_id`, `role`,
`charter_id`, `target_seal`, `round_input_seal`, `scope_locator_ids`, and
`source_findings`. It has no other fields. End with exactly one terminal
line, and nothing after it: `REVIEW-STATUS: COMPLETE`, or
`REVIEW-STATUS: UNABLE` if you could not review the scope.
