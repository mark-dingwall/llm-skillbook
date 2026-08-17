# Claude plugin metadata contract

The manifest dots resolve from the repository root, so plugin metadata must be
interpreted from this checkout rather than from a copied subdirectory. Keep
the plugin names aligned across marketplace and plugin metadata.

Strict plugin validation checks metadata shape, but it does not prove that
Claude registered every agent. Pair validation with the plugin-agent contract
tests whenever agent layout or metadata changes. Keep installation guidance in
the root README.
