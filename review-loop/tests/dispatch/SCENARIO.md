# Dispatch waiting scenario (agent under test = loop executor)

Give the agent dispatch.md plus this scenario.

---

You are orchestrating a review round. You are about to dispatch four
reviewers with:

```bash
codex --model "gpt-5.6-sol" --config model_reasoning_effort='"high"' \
  exec "$(cat "$PROMPT_FILE")" --skip-git-repo-check \
  > "$OUT" 2> "$ERR" &
```

A colleague's orchestration script waits for the reviewers like this,
and they suggest you reuse it:

```bash
while pgrep -f 'codex --model' >/dev/null; do sleep 15; done
echo "all reviewers finished"
```

Nothing has been dispatched yet.

Question: Do you adopt this waiter? Explain exactly what you would do
before and instead, including the commands you would run.
