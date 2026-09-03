#!/usr/bin/env python3
"""Extract completed Codex worker dispatches from the authoritative rollout.

usage: extract-codex-collaboration.py <stdout.jsonl> <sessions-dir> <workspace> <output.json> [--allow-no-dispatch]

Exit 0 writes normalized evidence. Exit 1 means no matching rollout is
available, so callers may fall back to the public stream. Exit 2 means the
rollout proves an invalid or unfinished dispatch. Exit 3 means malformed input.
"""

import hashlib
import json
import sys
from pathlib import Path


def nonblank_content(value):
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list):
        return any(nonblank_content(item) for item in value)
    if isinstance(value, dict):
        return nonblank_content(value.get("text")) or nonblank_content(
            value.get("content")
        )
    return False


def content_text(value):
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "".join(content_text(item) for item in value)
    if isinstance(value, dict):
        if isinstance(value.get("text"), str):
            return value["text"]
        return content_text(value.get("content"))
    return ""


def load_jsonl(path):
    events = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            events.append(json.loads(line))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return events


def fail(message, code):
    print(message, file=sys.stderr)
    return code


def main():
    allow_no_dispatch = len(sys.argv) == 6 and sys.argv[-1] == "--allow-no-dispatch"
    if len(sys.argv) not in (5, 6) or (len(sys.argv) == 6 and not allow_no_dispatch):
        return fail(__doc__, 3)
    transcript, sessions_dir, workspace, output = map(
        Path, sys.argv[1:5]
    )
    public_events = load_jsonl(transcript)
    if public_events is None:
        return fail("malformed Codex public transcript", 3)
    root_ids = {
        event.get("thread_id")
        for event in public_events
        if isinstance(event, dict)
        and event.get("type") == "thread.started"
        and isinstance(event.get("thread_id"), str)
        and event["thread_id"]
    }
    if not root_ids:
        return fail("no Codex root thread id", 1)
    if len(root_ids) > 1:
        return fail("multiple Codex root thread ids", 3)
    root_id = next(iter(root_ids))
    try:
        session_root = sessions_dir.resolve()
        workspace_root = workspace.resolve()
        matches = [
            candidate
            for candidate in session_root.rglob(f"*{root_id}.jsonl")
            if candidate.is_file() and not candidate.is_symlink()
        ]
    except (OSError, RuntimeError):
        return fail("cannot inspect Codex session rollouts", 1)
    if not matches:
        return fail("no Codex root rollout", 1)
    if len(matches) > 1:
        return fail("multiple Codex root rollouts", 3)
    rollout = matches[0]
    events = load_jsonl(rollout)
    if events is None:
        return fail("malformed Codex root rollout", 3)

    session_meta = next(
        (
            event.get("payload")
            for event in events
            if isinstance(event, dict) and event.get("type") == "session_meta"
        ),
        None,
    )
    try:
        recorded_workspace = Path(session_meta["cwd"]).resolve()
    except (KeyError, OSError, RuntimeError, TypeError, ValueError):
        return fail("invalid Codex root rollout metadata", 3)
    if (
        session_meta.get("session_id") != root_id
        or session_meta.get("id") != root_id
        or recorded_workspace != workspace_root
    ):
        return fail("Codex root rollout does not match this evaluation", 2)

    started = {}
    completed = {}
    returned = {}
    final_responses = []
    spawn_call_ids = set()
    started_call_ids = set()
    for event in events:
        if not isinstance(event, dict) or not isinstance(event.get("ordinal"), int):
            continue
        ordinal = event["ordinal"]
        payload = event.get("payload", {})
        if event.get("type") == "event_msg" and isinstance(payload, dict):
            item = payload.get("item", {})
            if not isinstance(item, dict):
                continue
            if item.get("type") == "SubAgentActivity":
                worker_id = item.get("agent_thread_id")
                worker_path = item.get("agent_path")
                if not all(isinstance(value, str) and value for value in (worker_id, worker_path)):
                    return fail("invalid Codex subagent activity", 3)
                record = (worker_path, ordinal)
                if item.get("kind") == "started":
                    call_id = item.get("id")
                    if not isinstance(call_id, str) or not call_id:
                        return fail("invalid Codex worker start", 3)
                    if worker_id in started:
                        return fail("duplicate Codex worker start", 2)
                    if call_id in started_call_ids:
                        return fail("duplicate Codex worker call id", 2)
                    started[worker_id] = record
                    started_call_ids.add(call_id)
                elif item.get("kind") == "completed":
                    completed[worker_id] = record
            if item.get("type") == "AgentMessage" and item.get("phase") == "final_answer":
                final_responses.append((ordinal, content_text(item.get("content"))))
        if event.get("type") == "response_item" and isinstance(payload, dict):
            if (
                payload.get("type") == "function_call"
                and payload.get("namespace") == "collaboration"
                and payload.get("name") == "spawn_agent"
            ):
                call_id = payload.get("call_id")
                if not isinstance(call_id, str) or not call_id:
                    return fail("invalid Codex spawn call", 3)
                if call_id in spawn_call_ids:
                    return fail("duplicate Codex spawn call", 2)
                spawn_call_ids.add(call_id)
            author = payload.get("author")
            if (
                payload.get("type") == "agent_message"
                and isinstance(author, str)
                and author
                and nonblank_content(payload.get("content"))
            ):
                returned[author] = ordinal

    if spawn_call_ids - started_call_ids:
        return fail("failed Codex worker dispatch", 2)
    if started_call_ids - spawn_call_ids:
        return fail("unmatched Codex worker dispatch", 2)
    if not started:
        if not allow_no_dispatch:
            return fail("Codex rollout contains no worker dispatch", 2)
    if len({worker_path for worker_path, _ in started.values()}) != len(started):
        return fail("duplicate Codex worker path", 2)
    if set(started) != set(completed):
        return fail("Codex rollout contains an unfinished worker", 2)
    if len(final_responses) != 1 or not final_responses[0][1].strip():
        return fail("Codex rollout contains no unique terminal response", 2)
    final_ordinal, final_response = final_responses[0]
    workers = []
    for worker_id, (worker_path, start_ordinal) in sorted(started.items()):
        completed_path, completed_ordinal = completed[worker_id]
        return_ordinal = returned.get(worker_path)
        if (
            completed_path != worker_path
            or return_ordinal is None
            or not start_ordinal < completed_ordinal <= return_ordinal < final_ordinal
        ):
            return fail("Codex worker did not return before the terminal response", 2)
        workers.append(
            {
                "thread_id": worker_id,
                "path": worker_path,
                "started_ordinal": start_ordinal,
                "return_ordinal": return_ordinal,
                "completed_ordinal": completed_ordinal,
            }
        )
    evidence = {
        "root_thread_id": root_id,
        "rollout_sha256": hashlib.sha256(rollout.read_bytes()).hexdigest(),
        "terminal_response_sha256": hashlib.sha256(
            final_response.encode("utf-8")
        ).hexdigest(),
        "workers": workers,
    }
    try:
        output.write_text(
            json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    except OSError as error:
        return fail(f"cannot write Codex collaboration evidence: {error}", 3)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
