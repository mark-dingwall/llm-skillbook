# clean_target

Fixture target copied into a fresh temporary Git repository by
`tests/integration/test_controller_clean.py`. It has:

- one safe, required baseline command a fake evidence scout proposes
  (`python3 -c "print(...)"`), exercised through the real
  `evidence.execute_gate` gate-execution path under real Bubblewrap; and
- one Minor inventory area (`greet.py`) a fake inventory owner proposes,
  below the `low`-tier specialist threshold, so it is never staffed and
  never blocks merge-readiness.
