#!/usr/bin/env python3
"""Extract a terminal response after verifying a real worker dispatch."""

import hashlib
import json
import sys


def has_nonblank_text(value):
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list):
        return any(has_nonblank_text(item) for item in value)
    if isinstance(value, dict):
        return has_nonblank_text(value.get("text")) or has_nonblank_text(
            value.get("content")
        )
    return False


def main() -> int:
    if len(sys.argv) not in (3, 4, 5):
        return 3
    harness, transcript = sys.argv[1:3]
    extra = sys.argv[3:]
    allow_no_dispatch = False
    if extra and extra[-1] == "--allow-no-dispatch":
        allow_no_dispatch = True
        extra = extra[:-1]
    if len(extra) > 1:
        return 3
    evidence_path = extra[0] if extra else None
    if evidence_path and harness != "codex":
        return 3
    responses = []
    claude_agent_calls = set()
    claude_agents = {}
    claude_completed = {}
    codex_workers = set()
    codex_completed = {}
    codex_root_ids = set()
    codex_spawn_attempted = False
    terminal_response_sha256 = None
    with open(transcript) as lines:
        for event_number, line in enumerate(lines):
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                return 3
            if harness == "claude" and event.get("type") == "result":
                responses.append((event_number, event.get("result")))
            if harness == "claude":
                message = event.get("message", {})
                if isinstance(message, dict):
                    content = message.get("content", [])
                    if isinstance(content, list):
                        for block in content:
                            if not isinstance(block, dict):
                                continue
                            if (
                                block.get("type") == "tool_use"
                                and block.get("name") == "Agent"
                                and isinstance(block.get("id"), str)
                                and block["id"]
                            ):
                                claude_agent_calls.add(block["id"])
                            if (
                                block.get("type") == "tool_result"
                                and block.get("tool_use_id") in claude_agent_calls
                            ):
                                result = event.get("tool_use_result", {})
                                if (
                                    isinstance(result, dict)
                                    and isinstance(result.get("agentId"), str)
                                    and result["agentId"]
                                ):
                                    if (
                                        result.get("status") == "completed"
                                        and has_nonblank_text(result.get("content"))
                                    ):
                                        claude_completed[block["tool_use_id"]] = (
                                            event_number
                                        )
                                    elif result.get("status") == "async_launched":
                                        claude_agents[block["tool_use_id"]] = result[
                                            "agentId"
                                        ]
                completed_call = event.get("tool_use_id")
                if (
                    event.get("type") == "system"
                    and event.get("subtype") == "task_notification"
                    and event.get("status") == "completed"
                    and completed_call in claude_agents
                    and event.get("task_id")
                    == claude_agents.get(completed_call)
                    and has_nonblank_text(event.get("summary"))
                ):
                    claude_completed[completed_call] = event_number
            elif harness == "codex":
                if (
                    event.get("type") == "thread.started"
                    and isinstance(event.get("thread_id"), str)
                    and event["thread_id"]
                ):
                    codex_root_ids.add(event["thread_id"])
                item = event.get("item", {})
                if (
                    event.get("type") == "item.completed"
                    and item.get("type") == "agent_message"
                ):
                    responses.append((event_number, item.get("text")))
                receiver_ids = item.get("receiver_thread_ids", [])
                if (
                    event.get("type") == "item.completed"
                    and item.get("type") == "collab_tool_call"
                    and item.get("tool") == "spawn_agent"
                ):
                    codex_spawn_attempted = True
                if (
                    event.get("type") == "item.completed"
                    and item.get("type") == "collab_tool_call"
                    and item.get("tool") == "spawn_agent"
                    and item.get("status") == "completed"
                    and isinstance(receiver_ids, list)
                ):
                    codex_workers.update(
                        value
                        for value in receiver_ids
                        if isinstance(value, str) and value
                    )
                states = item.get("agents_states", {})
                if isinstance(states, dict):
                    for worker_id, state in states.items():
                        if worker_id not in codex_workers or not isinstance(state, dict):
                            continue
                        worker_return = state.get("completed")
                        if isinstance(worker_return, str) and worker_return.strip():
                            codex_completed[worker_id] = event_number
    if evidence_path:
        try:
            with open(evidence_path, encoding="utf-8") as evidence_file:
                evidence = json.load(evidence_file)
            evidence_workers = evidence["workers"]
            terminal_response_sha256 = evidence["terminal_response_sha256"]
        except (OSError, KeyError, json.JSONDecodeError, TypeError):
            return 3
        if (
            not isinstance(evidence, dict)
            or codex_root_ids != {evidence.get("root_thread_id")}
            or not isinstance(evidence_workers, list)
            or (not evidence_workers and not allow_no_dispatch)
            or not isinstance(terminal_response_sha256, str)
            or len(terminal_response_sha256) != 64
        ):
            return 3
        evidence_ids = set()
        for worker in evidence_workers:
            if not isinstance(worker, dict):
                return 3
            worker_id = worker.get("thread_id")
            ordinals = [
                worker.get("started_ordinal"),
                worker.get("return_ordinal"),
                worker.get("completed_ordinal"),
            ]
            if (
                not isinstance(worker_id, str)
                or not worker_id
                or worker_id in evidence_ids
                or not all(isinstance(value, int) for value in ordinals)
                or not ordinals[0] < ordinals[2] <= ordinals[1]
            ):
                return 3
            evidence_ids.add(worker_id)
        codex_workers.update(evidence_ids)
        codex_completed.update({worker_id: -1 for worker_id in evidence_ids})
    response_record = next(
        (
            record
            for record in reversed(responses)
            for value in [record[1]]
            if isinstance(value, str) and value.strip()
        ),
        None,
    )
    if response_record is None:
        return 1
    response_number, response = response_record
    if terminal_response_sha256 is not None and (
        hashlib.sha256(response.encode("utf-8")).hexdigest()
        != terminal_response_sha256
    ):
        return 3
    if harness == "claude":
        workers = claude_agent_calls
        completed = claude_completed
    else:
        workers = codex_workers
        completed = codex_completed
    if not workers:
        if not allow_no_dispatch or codex_spawn_attempted:
            return 2
    elif (
        not workers.issubset(completed)
        or max(completed.values()) >= response_number
    ):
        return 2
    print(response)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
