# Packaging test contract

These tests exercise repository packaging and plugin registration. Installer
cases use isolated temporary homes, so they do not inspect or modify a real
user installation.

Payload assertions sample important boundaries; they are not an exhaustive
inventory of every shipped file. A passing plugin metadata check does not prove
agent registration, and mirror synchronization is separately verified by the
plugin-agent tests. Interpret failures as packaging or discovery regressions,
not as evidence about component runtime behavior.
