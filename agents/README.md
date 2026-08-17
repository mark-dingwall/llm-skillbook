# `agents`

This directory is the Claude plugin's agent surface. Its agent definition
files are real-file mirrors of the canonical definitions maintained with
`multi-review`.

When an agent changes, update the canonical definition, re-copy the mirror,
and run the plugin-agent regression tests. Claude plugin discovery depends on
the agent definitions being regular files, not links.
