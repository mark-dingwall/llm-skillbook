# Backlog

Forward-looking work, not committed to a milestone. Re-evaluate only when the
stated trigger is present.

## Batch reviewed-snapshot blob reads (deferred 2026-09-13)

`tracked_content_mismatches` currently starts one `git cat-file` process for
each tracked blob. With 2,514 tracked entries, one content comparison measured
about 8.9 seconds and the four required post-review gates therefore add roughly
36 seconds across an ordinary successful run. A one-process `git cat-file
--batch` probe measured about 2.1 seconds for the same repository, suggesting a
possible cumulative saving of approximately 27 seconds.

This is deferred from PR #7 under the Strictly MVP policy: current behavior is
correct, the latency is not a workflow blocker, and batching is an optimization
rather than a merge prerequisite. Revisit when measured gate latency materially
impairs normal completion or recovery, or a supported repository makes the
per-blob process cost substantially worse.

Keep any eventual implementation narrow:

- use one persistent `git cat-file --batch` process per snapshot comparison;
- preserve byte-exact regular-file and symlink-target comparison, existing
  allowed-path behavior, transforming-attribute rejection, hardened Git
  environment, missing-object handling, and explicit gitlink rejection;
- parse binary payloads by their reported byte lengths and fail closed on
  malformed or incomplete output; and
- add no cache, new workflow artifact, schema change, or generalized Git object
  subsystem.

Focused tests should cover binary blobs, unusual valid paths, missing or
malformed objects, unchanged security boundaries, and the replacement of
per-blob subprocesses with a single batch process.
