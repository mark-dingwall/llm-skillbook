# Designing review-loop profiles

A profile is an optional local YAML file that overlays a few fixed knobs on
top of tier defaults. It cannot change tier, round caps, staffing
thresholds, participants, or synthesis — those stay fixed for safety.

## Selecting a profile

- A bare name (no `/`, not `.` or `..`) resolves to
  `$XDG_CONFIG_HOME/review-loop/profiles/<name>.yaml`, or
  `~/.config/review-loop/profiles/<name>.yaml` when `XDG_CONFIG_HOME` is
  unset.
- Anything containing a path separator is used as an explicit path.
- There is no auto-discovery. A missing or malformed *explicit* selection
  never falls back silently — the run asks whether to proceed with tier
  defaults instead.

## Schema (version 1)

```yaml
version: 1                 # required, must be 1
max_time_seconds: 1800     # optional, positive integer; overridden by a
                            # per-run value when the operator supplies one

holistic:
  capability: mid-tier      # mid-tier | one-above-mid | most-capable
  model: local-model-id
  fallback_capability: mid-tier   # inherits capability when omitted
  fallback_model: local-model-id  # inherits model when omitted
  multi_review:
    models:
      claude: provider-model-id   # only claude/codex are valid keys
      codex: provider-model-id    # each value must be non-empty

adversarial:
  capability: mid-tier
  model: local-model-id

specialists:
  capability: mid-tier
  model: local-model-id
```

Every field is optional except `version`. An omitted field inherits the
tier default. Unknown keys, unknown versions, wrong types, non-positive
`max_time_seconds`, and unsupported capability labels are all rejected.
Duplicate mapping keys are rejected at every nesting level (last-key-wins
parsing is not tolerated).

If `holistic.multi_review.models` is present at all, it must pin the
*complete* `claude`/`codex` pair with non-empty values — a partial pin
(only `claude`, only `codex`, or an empty `models: {}`) is rejected, as is
any key outside that pair. There is no way to configure just one side of
the multi-review slot.

An explicit model pin is never silently substituted: if it cannot be
honored, that participant fails rather than falling back to a default
model. Ordinary holistic fallback exists to cover a failed multi-review
slot, not to replace a rejected pin.

## Examples

Minimal — just cap run time:

```yaml
version: 1
max_time_seconds: 900
```

Pin local models for a self-hosted review pass:

```yaml
version: 1
holistic:
  capability: mid-tier
  model: local-7b-instruct
adversarial:
  capability: mid-tier
  model: local-7b-instruct
```

## Migration

There is no include/inherit/stacking mechanism in version 1. A future
schema version would be a new sibling file with `version: 2`; there is no
automatic upgrade path.
