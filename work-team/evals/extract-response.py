#!/usr/bin/env python3
"""Extract a terminal response after verifying a real worker dispatch."""

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
    harness, transcript = sys.argv[1:]
    responses = []
    claude_agent_calls = set()
    claude_agents = {}
    claude_completed = {}
    codex_workers = set()
    codex_completed = {}
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
    if harness == "claude":
        workers = claude_agent_calls
        completed = claude_completed
    else:
        workers = codex_workers
        completed = codex_completed
    if (
        not workers
        or not workers.issubset(completed)
        or max(completed.values()) >= response_number
    ):
        return 2
    print(response)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
